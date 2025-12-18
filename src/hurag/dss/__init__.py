from .rss import with_rdb
from .vss import with_vdb
from .. import logger

@with_vdb(client_name="vdb_client")
@with_rdb(
    connection_name="rdb_connection",
    cursor_name="rdb_cursor",
)
async def init_ds(rdb_connection, rdb_cursor, vdb_client):
    """Initialize the data storage of the HuRAG knowledge base.

    Args:
        rdb_connection: The RDB connection object.
        rdb_cursor: The RDB cursor object.
        vdb_client: The VDB client object.

        All 3 arguments are injected by 'with_rdb' and 'with_vdb'.
    """
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
        logger.warning(f"Error while initializing the rdb: {e}")
        raise e

    # 2. Initialize vdb
    import asyncio

    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    _create_collection(vdb_client, **p)
                ) for p in INIT_VSS_PARAMS
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


__all__ = [
    "with_rdb",
    "with_vdb",
    "init_ds",
]

