from .rss import with_rdb
from .vss import with_vdb

__all__ = [
    "with_rdb",
    "with_vdb",
]

@with_vdb(client_name="vdb_client")
@with_rdb(
    connection_name="rdb_conn",
    cursor_name="rdb_cursor",
)
async def init_ds(rdb_conn, rdb_cursor, vdb_client):
    """Initialize the data storage of the HuRAG knowledge base.

    Args:
        rdb_conn: The RDB connection object.
        rdb_cursor: The RDB cursor object.
        vdb_client: The VDB client object.
    """
    # Perform any necessary initialization here
    print(f"VDB Client: {vdb_client}")
    print(f"RDB Connection: {rdb_conn}")
    # resp = await vdb_client.query(collection_name="nodes", filter="id != '0'")
    # return resp
