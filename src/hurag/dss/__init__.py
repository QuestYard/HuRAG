from .. import logger
from .rss import with_rdb
from .vss import with_vdb
from .fss import FileContent, MM_FOLDER, AT_FOLDER


@with_vdb(client_arg_name="vdb_client")
@with_rdb(connection_arg_name="rdb_connection", cursor_arg_name="rdb_cursor")
async def init_ds(rdb_connection, rdb_cursor, vdb_client):
    """Initialize the data storage of the HuRAG knowledge base."""
    import warnings
    from aiomysql import Warning as mysql_warning

    warnings.filterwarnings("ignore", category=mysql_warning)
    from ..constants import INIT_RSS_STATEMENTS, INIT_VSS_PARAMS

    # 1. Initialize rdb
    rdb_stmts = [s.strip() for s in INIT_RSS_STATEMENTS.split(";")]
    try:
        for stmt in rdb_stmts:
            if not stmt:
                continue
            await rdb_cursor.execute(stmt)
        await rdb_connection.commit()
        logger.info("The rdb is initialized.")
    except Exception as e:
        await rdb_connection.rollback()
        logger.error(f"Error while initializing the rdb: {e}")
        raise

    # 2. Initialize vdb
    import asyncio

    try:
        async with asyncio.TaskGroup() as tg:
            _ = [
                tg.create_task(_create_collection(vdb_client, **p))
                for p in INIT_VSS_PARAMS
            ]
        logger.info("The vdb is initialized.")
    except ExceptionGroup as eg:
        logger.error(f"Error while initializing the vdb: {eg}")
        for i, error in enumerate(eg.exceptions):
            logger.error(f"{i}: {error}")
        raise eg


async def _create_collection(cli, name, fields, indice):
    if await cli.has_collection(name):
        await cli.drop_collection(name)

    schema = cli.create_schema(enable_dynamic_field=False)
    for field in fields:
        schema.add_field(**field)
    index_params = cli.prepare_index_params()
    for index in indice:
        index_params.add_index(**index)
    await cli.create_collection(name, schema=schema, index_params=index_params)


@with_vdb(client_arg_name="vdb_client")
@with_rdb(connection_arg_name="rdb_connection", cursor_arg_name="rdb_cursor")
async def clear_graph(rdb_connection, rdb_cursor, vdb_client):
    """Clean the knowledge graph data from both RDB and VDB.

    Args:
        rdb_connection: The RDB connection object.
        rdb_cursor: The RDB cursor object.
        vdb_client: The VDB client object.

        All 3 arguments are injected by 'with_rdb' and 'with_vdb'.
    """
    try:
        await rdb_cursor.execute("DELETE FROM community_entity;")
        await rdb_cursor.execute("DELETE FROM communities;")
        await rdb_cursor.execute("DELETE FROM entity_cite;")
        await rdb_cursor.execute("DELETE FROM relation_cite;")
        await rdb_cursor.execute("DELETE FROM relations;")
        await rdb_cursor.execute("DELETE FROM entities;")
        await rdb_cursor.execute("UPDATE documents SET kg_built = FALSE;")
        await rdb_connection.commit()
    except Exception as e:
        await rdb_connection.rollback()
        logger.error(f"Error while cleaning the rdb graph data: {e}")
        raise

    try:
        await vdb_client.delete(collection_name="nodes", filter='id != ""')
        await vdb_client.delete(collection_name="edges", filter='id != ""')
        await vdb_client.delete(collection_name="communities", filter='id != ""')
        logger.info("The knowledge graph data is cleaned from both RDB and VDB.")
    except Exception as e:
        logger.error(f"Error while cleaning the vdb graph data: {e}")
        raise


__all__ = [
    "with_rdb",
    "with_vdb",
    "FileContent",
    "MM_FOLDER",
    "AT_FOLDER",
]
