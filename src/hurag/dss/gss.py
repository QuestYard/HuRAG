from __future__ import annotations
from typing import Any, TYPE_CHECKING
from ..types import EmbeddingType

if TYPE_CHECKING:
    from ..schemas import Graph
    import igraph as ig
    from igraph.clustering import VertexClustering


async def upsert_graph(
    g: Graph,
    embeddings: list[dict[EmbeddingType, Any]],
    doc_ids: list[str],
) -> None:
    """
    Upsert the knowledge graph into rdb and vdb.

    Arguments:
        g: the knowledge graph object
        embeddings: the list of embeddings for all nodes and edges in the graph
        doc_ids: the list of document ids whose segments contributed to the graph

    Return:
        None
    """
    _SQL_UPSERT_GRAPH = [
        """
        INSERT entities (id, name, type, description) VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            type = VALUES(type),
            description = VALUES(description)
        """,
        "INSERT IGNORE entity_cite (entity_id, segment_id) VALUES (%s, %s)",
        """
        INSERT relations (id, source_id, target_id, type, description, strength)
        VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE
            type = VALUES(type),
            description = VALUES(description),
            strength = VALUES(strength)
        """,
        "INSERT IGNORE relation_cite (relation_id, segment_id) VALUES (%s, %s)",
        f"""
        UPDATE documents SET kg_built = TRUE
        WHERE id IN ({",".join(["%s"] * len(doc_ids))})
        """,
    ]
    from .. import logger
    from ..constants import GRAPH_FIELD_SEP
    from . import rss, vss

    # save into vdb
    from itertools import batched, starmap

    _embeddings = (
        {"dense_vec": d, "sparse_vec": s}
        for embedding in embeddings
        for d, s in zip(embedding["dense_vecs"], embedding["sparse_vecs"])
    )
    try:
        data = (
            {"id": node.id, "dense_vec": None, "sparse_vec": None} for node in g.nodes
        )
        for _raw_batch in batched(zip(data, _embeddings), 5000):
            _batch = list(starmap(lambda x, y: x.update(y) or x, _raw_batch))
            await vss.upsert("nodes", _batch)
        data = (
            {"id": edge.id, "dense_vec": None, "sparse_vec": None} for edge in g.edges
        )
        for _raw_batch in batched(zip(data, _embeddings), 5000):
            _batch = list(starmap(lambda x, y: x.update(y) or x, _raw_batch))
            await vss.upsert("edges", _batch)
    except Exception as e:
        logger.error(f"Failed save graph element vectors into vdb: {e}")
        raise

    # save into rdb
    node_name_id_maps = {node.name: node.id for node in g.nodes}
    data = [
        [
            (
                n.id,
                n.name[:100] if n.name else n.name,
                n.type,
                n.description[:500] if n.description else n.description,
            )
            for n in g.nodes
        ],
        [
            (n.id, s)
            for n in g.nodes
            if n.seg_ids
            for s in set(n.seg_ids.split(GRAPH_FIELD_SEP))
        ],
        [
            (
                e.id,
                node_name_id_maps[e.source],
                node_name_id_maps[e.target],
                e.type,
                e.description[:500] if e.description else e.description,
                e.strength,
            )
            for e in g.edges
        ],
        [
            (e.id, s)
            for e in g.edges
            if e.seg_ids
            for s in set(e.seg_ids.split(GRAPH_FIELD_SEP))
        ],
        tuple(doc_ids),
    ]
    try:
        await rss.transact(_SQL_UPSERT_GRAPH, data)
        logger.info(
            f"Knowledge graph created for {len(doc_ids)} documents, "
            f"including {len(g.nodes)} entities and {len(g.edges)} relations."
        )
    except Exception as e:
        logger.error(f"Failed save knowledge graph into rdb: {e}")
        raise


async def save_communities(
    graph: ig.Graph,
    partitions: VertexClustering,
    communities: list[dict[str, Any]],
) -> tuple[int, int]:
    """
    Existing communities will be cleaned out before saving new communities.

    Arguments:
        graph: the igraph.Graph object.
        partitions: the partitions resulted from Leiden algorithm.
        communities: the embedding table of communities.

    Return:
        A tuple containing:
            - The number of communities saved.
            - The number of community-entity associations saved.
    """
    from . import vss, rss

    sql = [
        "DELETE FROM community_entity;",
        "DELETE FROM communities;",
        "INSERT INTO communities (id, summary) VALUES (%s, %s)",
        "INSERT INTO community_entity (community_id, entity_id) VALUES (%s, %s)",
    ]

    _communities = [(s["c_no"], s["summary"]) for s in communities]
    _community_entity = [
        (s["c_no"], graph.vs["name"][vid])
        for s in communities
        for vid in partitions[s["c_no"]]
    ]
    _embeddings = [
        {
            "id": s["c_no"],
            "dense_vec": s["dense_vec"],
            "sparse_vec": s["sparse_vec"],
        }
        for s in communities
    ]
    await rss.transact(sql, [(), (), _communities, _community_entity])
    cli = await vss.get_client()
    await cli.delete("communities", filter='id != ""')
    await cli.insert("communities", _embeddings)

    return len(_communities), len(_community_entity)


async def search(
    keywords: dict[str, list[str]],
    vecs: dict[str, Any],
    docs: dict[str, Any],
    top_k: int = 20,
    max_nodes: int = 1000,
    hops: int = 1,
    rrf_k: float = 60,
) -> dict[str, float]:
    """
    Arguments:
        keywords: {"low_level_keywords": [], "high_level_keywords": []}
        vecs: {"dense": semantic vectors, "sparse": lexical weights}, among
            which the first vector-pair refers to the query, then the high-
            level keywords and the low-level keywords.
    Return:
        {id1: score1, id2: score2, ..., id_top_k: score_top_k}
    """
    from . import vss, rss

    n_lk = len(keywords["low_level_keywords"])
    n_hk = len(keywords["high_level_keywords"])

    # one-hop search for nodes, for all keywords, ll and hl
    zero_hop_nodes = {}
    # zero_hop_nodes := {node_id: score, ...}
    for i in range(1, n_hk + n_lk + 1):
        vectors = {
            "dense": [vecs["dense_vecs"][i]],
            "sparse": vecs["sparse_vecs"][i],
        }
        zero_hop_nodes.update(
            await vss.search("nodes", vecs=vectors, top_k=3, rrf_k=rrf_k)
        )
    nodes = await _n_hop_search(zero_hop_nodes, top_n=max_nodes, hops=hops)

    # search edges, for the query itself and hl keywords
    hit_edges = {}
    for i in range(n_hk + 1):
        vectors = {
            "dense": [vecs["dense_vecs"][i]],
            "sparse": vecs["sparse_vecs"][i],
        }
        hit_edges.update(await vss.search("edges", vecs=vectors, top_k=3, rrf_k=rrf_k))
    edges = set(hit_edges)

    # found cited segments and merge
    node_cites = (
        []
        if not nodes
        else await rss.query(
            f"""
        SELECT sc.segment_id, s.document_id
        FROM entity_cite sc
        JOIN segments s ON s.id = sc.segment_id
        WHERE sc.entity_id IN ({",".join(["%s"] * len(nodes))})
        """,
            tuple(nodes),
        )
    )
    edge_cites = (
        []
        if not edges
        else await rss.query(
            f"""
        SELECT rc.segment_id, s.document_id
        FROM relation_cite rc
        JOIN segments s ON s.id = rc.segment_id
        WHERE rc.relation_id IN ({",".join(["%s"] * len(edges))})
        """,
            tuple(edges),
        )
    )
    segments = set(x for x in edge_cites + node_cites if x[1] in docs)
    # semantic search in chunks of these segments
    chunks = [
        x[0]
        for x in await rss.query(
            f"""
            WITH segs(id) AS (VALUES {",".join(["(%s)"] * len(segments))})
            SELECT c.id FROM chunks c JOIN segs s ON c.segment_id = s.id
            """,
            tuple(s[0] for s in segments),
        )
    ]
    graph_search_results = await vss.search(
        collection_name="chunks",
        scope=chunks,
        vecs={
            "dense": [vecs["dense_vecs"][0]],
            "sparse": vecs["sparse_vecs"][0],
        },
        top_k=top_k,
        rrf_k=rrf_k,
    )

    return graph_search_results


async def _n_hop_search(ori_nodes, top_n, hops):
    from . import rss

    if not ori_nodes:
        return set()
    nodes = set(ori_nodes)
    starts = nodes.copy()
    for _ in range(hops):
        connected = set(
            x[0]
            for x in await rss.query(
                f"""
                WITH nodes(id) AS (VALUES {",".join(["(%s)"] * len(starts))})
                SELECT r.source_id FROM relations r JOIN nodes n ON r.target_id = n.id
                UNION
                SELECT r.target_id FROM relations r JOIN nodes n ON r.source_id = n.id
                """,
                tuple(starts),
            )
        )
        starts = connected.copy() - nodes
        nodes |= connected
        if len(nodes) >= top_n:
            break
    return nodes


# --- Communities ---


async def associations(
    keywords: dict[str, list[str]],
    vecs: dict[str, Any],
    docs: dict[str, Any],
    top_k: int = 50,
    hops: int = 1,
    max_communities: int = 5,
    max_nodes: int = 1000,
    rrf_k: float = 60,
):
    """
    Returns:
        [(segment_id, document_id), ...] in order of distance
    """
    from . import vss, rss

    scope = None
    if max_communities > 0:
        community_scores = await vss.search(
            collection_name="communities",
            vecs={
                "dense": [vecs["dense_vecs"][0]],
                "sparse": vecs["sparse_vecs"][0],
            },
            top_k=max_communities,
            rrf_k=rrf_k,
        )
        scope = [
            x[0]
            for x in await rss.query(
                f"""
                SELECT entity_id FROM community_entity
                WHERE community_id IN ({",".join(["%s"] * len(community_scores))})
                """,
                tuple(community_scores),
            )
        ]

    # cites whose distance is zero: top 3 edges and nodes
    n_lk = len(keywords["low_level_keywords"])
    n_hk = len(keywords["high_level_keywords"])

    zero_dist_edges = {}
    for i in range(n_hk + 1):
        vectors = {
            "dense": [vecs["dense_vecs"][i]],
            "sparse": vecs["sparse_vecs"][i],
        }
        zero_dist_edges.update(
            await vss.search("edges", vecs=vectors, top_k=3, rrf_k=rrf_k)
        )
    zero_dist_edge_cites = (
        set()
        if not zero_dist_edges
        else set(
            await rss.query(
                f"""
            SELECT rc.segment_id, s.document_id FROM relation_cite rc
            JOIN segments s ON s.id = rc.segment_id
            WHERE rc.relation_id IN ({",".join(["%s"] * len(zero_dist_edges))})
            """,
                tuple(zero_dist_edges),
            )
        )
    )

    zero_dist_nodes = {}
    for i in range(1, n_hk + n_lk + 1):
        vectors = {
            "dense": [vecs["dense_vecs"][i]],
            "sparse": vecs["sparse_vecs"][i],
        }
        zero_dist_nodes.update(
            await vss.search("nodes", vecs=vectors, scope=scope, top_k=3, rrf_k=rrf_k)
        )
    zero_dist_node_cites = (
        set()
        if not zero_dist_nodes
        else set(
            await rss.query(
                f"""
            SELECT ec.segment_id, s.document_id FROM entity_cite ec
            JOIN segments s ON s.id = ec.segment_id
            WHERE ec.entity_id IN ({",".join(["%s"] * len(zero_dist_nodes))})
            """,
                tuple(zero_dist_nodes),
            )
        )
        - zero_dist_edge_cites
    )

    associated_nodes = await _n_hop_search(zero_dist_nodes, top_n=max_nodes, hops=hops)
    associated_nodes_cites = (
        set()
        if not associated_nodes
        else set(
            await rss.query(
                f"""
            SELECT ec.segment_id, s.document_id
            FROM entity_cite ec
            JOIN segments s ON s.id = ec.segment_id
            WHERE ec.entity_id IN ({",".join(["%s"] * len(associated_nodes))})
            """,
                tuple(associated_nodes),
            )
        )
        - (zero_dist_edge_cites | zero_dist_node_cites)
    )
    # merge in order of distance
    segments = [x for x in zero_dist_edge_cites if x[1] in docs]
    segments += [x for x in zero_dist_node_cites if x[1] in docs]
    segments += [x for x in associated_nodes_cites if x[1] in docs]

    return segments[:top_k]
