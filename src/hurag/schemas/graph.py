from __future__ import annotations
from typing import Self, Any
from copy import deepcopy
from dataclasses import dataclass, field

from ..utilities import (
    split_string_by_markers,
    is_float,
    clean_str,
    normalize_extracted_info,
)
from ..constants import GRAPH_FIELD_SEP

@dataclass
class Entity:
    id: str | None = field(default=None)
    name: str | None = field(default=None, compare=False)
    type: str | None = field(default=None, compare=False)
    description: str | None = field(default=None, compare=False, repr=False)
    seg_ids: str | None = field(default=None, compare=False, repr=False)

    def __add__(self, other: Self) -> Self:
        try:
            _new_entity = deepcopy(self)
            if self.name == other.name:
                _new_entity += other
            return _new_entity
        except TypeError:
            return NotImplemented

    def __radd__(self, other: Self) -> Self:
        return self + other

    def __iadd__(self, other: Self) -> Self:
        """
        Absorb another entity into self by concatenating names, types and
        descriptions. Id and embeddings will be set to None.

        Absorbing results in an intermediate form of Entity. They cannot be
        directly stored into the knowledge graph before being recreated to
        single name, single type and single description.
        """
        if not isinstance(other, type(self)):
            return NotImplemented

        self.id = None
        self.name = self.name or ""
        self.type = self.type or ""
        self.description = self.description or ""
        self.seg_ids = self.seg_ids or ""
        self.name += (GRAPH_FIELD_SEP + (other.name or ""))
        self.type += (GRAPH_FIELD_SEP + (other.type or ""))
        self.description += (GRAPH_FIELD_SEP + (other.description or ""))
        self.seg_ids += (GRAPH_FIELD_SEP + (other.seg_ids or ""))

        return self

    def __eq__(self, other) -> bool:
        if self.id is not None and other.id is not None:
            return self.id == other.id
        return self.name == other.name and self.seg_ids == other.seg_ids

    @property
    def brief(self) -> str:
        return f"## {self.name}: \n\n- {self.description}"

    def create(
        self,
        fields: list[str],
        segment_id: str | None = None,
        alias: dict[str, str] | None = None,
    ) -> Self:
        """
        Parse a single entity from an extracted string record.

        If fields are invalid or name is empty, return a None-valued Entity.
        """
        if len(fields) < 4 or '"entity"' not in fields[0]:
            return self
        _name = clean_str(fields[1]).strip()
        if not _name:
            return self
        _name = normalize_extracted_info(_name, is_entity=True)
        if alias and _name in alias:
            _name = alias[_name]

        _type = clean_str(fields[2]).strip('"')
        if not _type.strip() or _type.startswith('("'):
            return self

        _description = clean_str(fields[3])
        _description = normalize_extracted_info(_description)
        if not _description.strip():
            return self

        self.id = None
        self.name = _name
        self.type = _type
        self.description = _description
        self.seg_ids = segment_id or ""

        return self

@dataclass
class Relation:
    id: str | None = field(default=None)
    source: str | None = field(default=None, compare=False)
    target: str | None = field(default=None, compare=False)
    type: str | None = field(default=None, compare=False)
    description: str | None = field(default=None, compare=False, repr=False)
    strength: float = field(default=0, compare=False, repr=False)
    seg_ids: str | None = field(default=None, compare=False, repr=False)

    def __add__(self, other: Self) -> Self:
        try:
            _new_relation = deepcopy(self)
            if self.source == other.source and self.target == other.target:
                _new_relation += other
            return _new_relation
        except TypeError:
            return NotImplemented

    def __radd__(self, other: Self) -> Self:
        return self + other

    def __iadd__(self, other: Self) -> Self:
        """
        Absorb another relation into self by concatenating names, types and
        descriptions. Id and embeddings will be set to None.

        Absorbing results in an intermediate form of Relation. They cannot be
        directly stored into the knowledge graph before being recreated to
        single source, single target, single type and single description.
        """
        if not isinstance(other, type(self)):
            return NotImplemented

        self.id = None
        self.source = self.source or ""
        self.target = self.target or ""
        self.type = self.type or ""
        self.description = self.description or ""
        self.seg_ids = self.seg_ids or ""
        self.source += (GRAPH_FIELD_SEP + (other.source or ""))
        self.target += (GRAPH_FIELD_SEP + (other.target or ""))
        self.type += (GRAPH_FIELD_SEP + (other.type or ""))
        self.description += (GRAPH_FIELD_SEP + (other.description or ""))
        self.seg_ids += (GRAPH_FIELD_SEP + (other.seg_ids or ""))
        self.strength += other.strength

        return self


    def __eq__(self, other) -> bool:
        if self.id is not None and other.id is not None:
            return self.id == other.id
        return (
            self.source == other.source
            and self.target == other.target
            and self.seg_ids == other.seg_ids
        )

    @property
    def brief(self) -> str:
        return f"## {self.source} - {self.target}:\n\n- {self.description}"

    def create(
        self,
        fields: list[str],
        segment_id: str | None = None,
        alias: dict[str, str] | None = None,
    ) -> Self:
        """
        Parse a single relation from an extracted string record.
        """
        if len(fields) < 5 or '"relation"' not in fields[0]:
            return self

        _source = clean_str(fields[1])
        _target = clean_str(fields[2])
        if not _source or not _target:
            return self
        _source = normalize_extracted_info(_source, is_entity=True)
        _target = normalize_extracted_info(_target, is_entity=True)
        if _source == _target:
            return self
        if alias:
            if _source in alias:
                _source = alias[_source]
            if _target in alias:
                _target = alias[_target]
        
        _description = clean_str(fields[3])
        _description = normalize_extracted_info(_description)
        if not _description.strip():
            return self

        _type = clean_str(fields[4])
        if not _type.strip():
            return self
        _type = normalize_extracted_info(_type, is_entity=True)
        _type = _type.replace("，", ",").replace("、", ",")

        _strength_str = clean_str(fields[-1]).strip().strip("'").strip('"')
        _strength = float(_strength_str) if is_float(_strength_str) else 1.0

        self.id = None
        self.source = _source
        self.target = _target
        self.type = _type
        self.description = _description
        self.strength = _strength
        self.seg_ids = segment_id or ""

        return self

def _process_local_graph(
    nodes: list[Entity],
    edges: list[Relation],
    blacklist: list[str] | None,
) -> tuple[Any, Any]:
    import re
    import pandas as pd

    if not blacklist:
        BLACKLIST_REGEX = re.compile(r"(?!)")  # match nothing
    else:
        pattern = "|".join([f"(?:{v})" for v in blacklist])
        BLACKLIST_REGEX = re.compile(f"^(?:{pattern})$")

    entities = pd.DataFrame(
        [
            {
                "id": None,
                "name": node.name,
                "type": node.type,
                "description": node.description,
                "seg_ids": node.seg_ids,
            }
            for node in nodes
        ]
    )
    relations = pd.DataFrame(
        [
            {
                "id": None,
                "source": edge.source,
                "target": edge.target,
                "type": edge.type,
                "description": edge.description,
                "strength": edge.strength,
                "seg_ids": edge.seg_ids,
            }
            for edge in edges
        ]
    )
    to_drop_entities_mask = entities["name"].str.contains(
        BLACKLIST_REGEX,
        regex=True,
        na=False
    )
    entities = entities[~to_drop_entities_mask].reset_index(drop=True)
    ent_set = set(zip(entities["name"], entities["seg_ids"]))
    remain_relations_mask = (
        pd.Series(zip(relations["source"], relations["seg_ids"])).isin(ent_set)
        &
        pd.Series(zip(relations["target"], relations["seg_ids"])).isin(ent_set)
    )
    relations = relations[remain_relations_mask].reset_index(drop=True)
    # group and aggregate
    entities = (
        entities
        .groupby("name", as_index=False)
        .agg(
            {
                "id": lambda _: None,
                "type": GRAPH_FIELD_SEP.join,
                "description": GRAPH_FIELD_SEP.join,
                "seg_ids": GRAPH_FIELD_SEP.join,
            }
        )
    )
    relations = (
        relations
        .groupby(["source", "target"], as_index=False)
        .agg(
            {
                "id": lambda _: None,
                "type": GRAPH_FIELD_SEP.join,
                "description": GRAPH_FIELD_SEP.join,
                "strength": "sum",
                "seg_ids": GRAPH_FIELD_SEP.join,
            }
        )
    )
    return entities, relations

async def _fetch_db_graph(nodes: list[Entity], edges: list[Relation]):
    from ..dss import rss
    pool = await rss.get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute("SET note_verbosity = ''")
        await cur.execute("DROP TEMPORARY TABLE IF EXISTS temp_nodes")
        await cur.execute("SET note_verbosity = 'basic,explain'")
        await cur.execute(
            """
            CREATE TEMPORARY TABLE temp_nodes (
                name VARCHAR(100) COLLATE utf8mb4_unicode_ci
            );
            """
        )
        await cur.executemany(
            "INSERT INTO temp_nodes VALUES (%s)",
            [(x.name,) for x in nodes],
        )
        await cur.execute(
            """
            SELECT id, name, type, description FROM entities
            WHERE name IN (SELECT name FROM temp_nodes)
            """
        )
        exists_nodes = {
            node[1]: {
                "id": node[0],
                "name": node[1],
                "type": node[2],
                "description": node[3],
            }
            for node in await cur.fetchall()
        }
        await cur.execute("SET note_verbosity = ''")
        await cur.execute("DROP TEMPORARY TABLE IF EXISTS temp_edges")
        await cur.execute("SET note_verbosity = 'basic,explain'")
        await cur.execute(
            """
            CREATE TEMPORARY TABLE temp_edges (
                source VARCHAR(100) COLLATE utf8mb4_unicode_ci,
                target VARCHAR(100) COLLATE utf8mb4_unicode_ci
            );
            """
        )
        await cur.executemany(
            "INSERT INTO temp_edges (source, target) VALUES (%s, %s)",
            [(x.source, x.target) for x in edges]
        )
        await cur.execute(
            """
            SELECT
                r.id,
                s.name AS source,
                t.name AS target,
                r.type,
                r.description,
                r.strength
            FROM relations AS r
            JOIN entities AS s ON r.source_id = s.id
            JOIN entities AS t ON r.target_id = t.id
            JOIN temp_edges e ON e.source = s.name AND e.target = t.name
            """
        )
        exists_edges = {
            (edge[1], edge[2]): {
                "id": edge[0],
                "source": edge[1],
                "target": edge[2],
                "type": edge[3],
                "description": edge[4],
                "strength": edge[5],
            }
            for edge in await cur.fetchall()
        }
    return exists_nodes, exists_edges

@dataclass
class Graph:
    nodes: list[Entity] = field(default_factory=list, compare=False)
    edges: list[Relation] = field(default_factory=list, compare=False)
    _fps: set[tuple] = field(default_factory=set, compare=False, repr=False)

    def append_node(self, node: Entity) -> Entity | None:
        if (node.name, node.seg_ids) not in self._fps:
            self.nodes.append(node)
            self._fps.add((node.name, node.seg_ids))
            return node
        return None

    def append_edge(self, edge: Relation) -> Relation | None:
        if (edge.source, edge.target, edge.seg_ids) not in self._fps:
            self.edges.append(edge)
            self._fps.add((edge.source, edge.target, edge.seg_ids))
            return edge
        return None

    def parse_and_dedupe(
        self,
        response: str,
        segment_id: str,
        alias: dict[str, str] | None = None,
    ) -> Self:
        """
        Parse and dedupe the extraction response of LLM to nodes and edges.

        Nodes with same name and segment, edges with same source, target and
        segment will be dropped.

        Args:
            response: The raw string response from LLM extraction.
            segment_id: The segment id where the response is extracted from.
            alias: An optional mapping from extracted names to normalized names.

        Returns:
            The Graph itself after parsing and deduplication.
        """
        import re
        from ..llm import PROMPTS
        RECORD_SEPS = [PROMPTS["TUPLE_DELIMITER"]]

        lines = split_string_by_markers(response, ["\n"])
        for line in lines:
            if record := re.search(r"\((.*)\)", line):
                record = record.group(1)
                fields = split_string_by_markers(record, RECORD_SEPS)
                if '"entity"' in fields[0]:
                    self.append_node(Entity().create(fields, segment_id, alias))
                if '"relation"' in fields[0]:
                    self.append_edge(Relation().create(fields, segment_id, alias))

        return self

    def clear(self) -> Self:
        """
        Clear all nodes, edges, and fingerprints from the graph.

        Returns:
            The Graph itself after clearing.
        """
        self._fps.clear()
        self.nodes.clear()
        self.edges.clear()

        return self

    def remove_orphans(self)-> Graph:
        """
        1. Remove edges without source or target nodes.
        2. Remove nodes without edges connected to.

        Returns:
            The removed nodes and edges in a new Graph.
        """
        removed = Graph()
        node_names = set((n.name for n in self.nodes))
        index_to_remove = []
        for i, edge in enumerate(self.edges):
            if edge.source not in node_names or edge.target not in node_names:
                index_to_remove.append(i)
        for i in index_to_remove[::-1]:
            removed.edges.append(self.edges.pop(i))

        node_names = set((e.source for e in self.edges))
        node_names = node_names.union(set((e.target for e in self.edges)))
        index_to_remove = []
        for i, node in enumerate(self.nodes):
            if node.name not in node_names:
                index_to_remove.append(i)
        for i in index_to_remove[::-1]:
            removed.nodes.append(self.nodes.pop(i))

        return removed

    async def resolve(
        self,
        blacklist: list[str] | None = None,
    ) -> Self:
        """
        Resolve parsed entities and relations in 5 steps:
        1. Remove nonsensical entities by matching entity-name blacklist.
        2. Remove relations without existing source or target entities.
        3. Group entities with same name and merge into one single entity.
        4. Merge with existing entities and relations in the database.

        This method is designed to invoke after a new graph is created by
        extracting and parsing elements.

        After resolving the nodes and edges will be cleaned and be ready for
        normalization, embedding and storing.

        Args:
            blacklist: An optional list of regex patterns for blacklisting
                entity names.

        Returns:
            The resolved Graph itself.
        """
        import asyncio

        (entities, relations), (exists_nodes, exists_edges) = await asyncio.gather(
            asyncio.to_thread(_process_local_graph, self.nodes, self.edges, blacklist),
            _fetch_db_graph(self.nodes, self.edges),
        )
        
        # merge, appending 'seg_ids' is not needed.
        for name, props in exists_nodes.items():
            indices = entities.index[entities["name"] == name]
            if len(indices) > 0:
                idx = indices[0]
                entities.at[idx, "id"] = props["id"]
                entities.at[idx, "type"] += (GRAPH_FIELD_SEP + props["type"])
                entities.at[idx, "description"] += (
                    GRAPH_FIELD_SEP + props["description"]
                )
        for names, props in exists_edges.items():
            indices = relations.index[
                (relations["source"] == names[0]) & (relations["target"] == names[1])
            ]
            if len(indices) > 0:
                idx = indices[0]
                relations.at[idx, "id"] = props["id"]
                relations.at[idx, "type"] += (GRAPH_FIELD_SEP + props["type"])
                relations.at[idx, "description"] += (
                    GRAPH_FIELD_SEP + props["description"]
                )
                relations.at[idx, "strength"] += props["strength"]

        self.clear()
        self.nodes = [Entity(**row) for row in entities.to_dict(orient="records")]
        self.edges = [Relation(**row) for row in relations.to_dict(orient="records")]

        return self

    @classmethod
    def from_responses(
        cls,
        responses: list[dict[str, str]],
        alias: dict[str, str] | None = None,
    ) -> Self:
        """Create a Graph from the responses of LLM extraction."""
        graph = cls()
        for seg in responses:
            graph.parse_and_dedupe(seg["extracting"], seg["segment_id"], alias)
            graph.parse_and_dedupe(seg["gleaning"], seg["segment_id"], alias)

        return graph

    @classmethod
    async def from_db(
        cls,
        ids: str | list[str] | None = None,
        titles: str | list[str] | None = None,
    ) -> Self:
        """
        Load the entire graph from database by document IDs and titles.

        Both IDs and titles are used to load graph from database together.
        If only one of them is given, load graph by that only.

        Args:
            ids: IDs of the documents used for constructing the graph.
            titles: titles of the documents used for constructing the graph.

        Return:
            A Graph containing elments constructed from the documents.
        """
        ids = ids or []
        if isinstance(ids, str):
            ids = [ids]
        titles = titles or []
        if isinstance(titles, str):
            titles = [titles]

        if not ids and not titles:
            return cls()

        from ..dss import rss
        pool = await rss.get_pool()
        async with pool.acquire() as conn, conn.cursor() as cur:
            # locate document IDs
            select = "SELECT id FROM documents WHERE "
            cond_id = f"id IN ({','.join(['%s'] * len(ids))})" if ids else ""
            cond_tt = f"title IN ({','.join(['%s'] * len(titles))})" if titles else ""
            sql = f"{select}{' OR '.join(filter(None, [cond_id, cond_tt]))}"
            await cur.execute(sql, ids + titles)
            rows = await cur.fetchall()
            doc_ids = tuple(row[0] for row in rows)
            # load entities
            await cur.execute(
                f"""
                SELECT e.id, e.name, e.type, e.description, ec.segment_id
                FROM entities e
                JOIN entity_cite ec ON e.id = ec.entity_id
                JOIN segments s ON ec.segment_id = s.id
                WHERE s.document_id IN ({','.join(['%s'] * len(doc_ids))})
                """,
                doc_ids,
            )
            nodes = {}
            node_rows = await cur.fetchall()
            for row in node_rows:
                if row[0] not in nodes:
                    nodes[row[0]] = Entity(
                        id=row[0],
                        name=row[1],
                        type=row[2],
                        description=row[3],
                        seg_ids=row[4],
                    )
                else:
                    nodes[row[0]].seg_ids += (GRAPH_FIELD_SEP + row[4])
            # load relations
            await cur.execute(
                f"""
                SELECT r.id, se.name AS source, te.name AS target,
                       r.type, r.description, r.strength, rc.segment_id
                FROM relations r
                JOIN relation_cite rc ON r.id = rc.relation_id
                JOIN entities se ON r.source_id = se.id
                JOIN entities te ON r.target_id = te.id
                JOIN segments s ON rc.segment_id = s.id
                WHERE s.document_id IN ({','.join(['%s'] * len(doc_ids))})
                """,
                doc_ids,
            )
            edges = {}
            edge_rows = await cur.fetchall()
            for row in edge_rows:
                if row[0] not in edges:
                    edges[row[0]] = Relation(
                        id=row[0],
                        source=row[1],
                        target=row[2],
                        type=row[3],
                        description=row[4],
                        strength=row[5],
                        seg_ids=row[6],
                    )
                else:
                    edges[row[0]].seg_ids += (GRAPH_FIELD_SEP + row[6])
        return cls(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )
