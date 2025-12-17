import aiomysql
import asyncio
from functools import wraps
from typing import Callable

from .. import conf, logger

_pool: aiomysql.Pool | None = None
_pool_lock: asyncio.Lock | None = None

async def _get_lock()-> asyncio.Lock:
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock

async def get_pool()-> aiomysql.Pool:
    """Get or create the database connection pool."""
    global _pool

    if _pool is not None:
        return _pool

    lock = await _get_lock()
    async with lock:
        _pool = await aiomysql.create_pool(
            host=conf.mariadb.host,
            port=conf.mariadb.port,
            user=conf.mariadb.user,
            password=conf.mariadb.password,
            db=conf.mariadb.database,
            autocommit=False,
        )

    return _pool

async def close_pool():
    """Close the database connection pool. Only used with API lifespan."""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

def with_rdb(
    func: Callable | None = None,
    *,
    connection_name: str = "connection",
    cursor_name: str = "cursor",
    dict_cursor: bool = False,
    ss_cursor: bool = False,
)-> Callable:
    """
    Decorator for injection of rss connection and cursor.

    Args:
        func:
            The function to be decorated.
        connection_name: optional, default "connection"
            The name of the connection argument to be injected.
        cursor_name: optional, default "cursor"
            The name of the cursor argument to be injected.
        dict_cursor: optional, default False
            Whether to use a dictionary cursor.
        ss_cursor: optional, default False
            Whether to use a server-side cursor.

    **Usage**:

    The most common usage is to inject connection and ordinary cursor with
    default names, ordinary cursor.

    There should be two arguments named "connection" and "cursor" in
    the decorated function.

    ```python
    @with_rdb
    async def my_function(connection, cursor, other_arg):
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Connection and cursor can also be injected into the decorated function
    as keyword arguments. 

    ```python
    @with_rdb
    async def my_function(other_arg, **kwargs):
        connection = kwargs['connection']
        cursor = kwargs['cursor']
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Or you can customize the names of the injected arguments.

    ```python
    @with_rdb(connection_name="conn", cursor_name="cur", dict_cursor=True)
    async def my_function(other_arg, **kwargs):
        connection = kwargs['conn']
        cursor = kwargs['cur']
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Type of cursor can also be specified. There are four types of cursor:

    - Ordinary cursor (default): `dict_cursor=False`, `ss_cursor=False`
    - Dictionary cursor: `dict_cursor=True`, `ss_cursor=False`
    - Server-side ordinary cursor: `dict_cursor=False`, `ss_cursor=True`
    - Server-side dictionary cursor: `dict_cursor=True`, `ss_cursor=True`

    **Caution**:

    - The decorated function *MUST* be asynchronous.
    - *DO NOT* close the connection or cursor in the decorated function.

    Returns:
        The decorated function.
    """
    if func is None:
        return lambda f: with_rdb(
            f,
            connection_name = connection_name,
            cursor_name = cursor_name,
            dict_cursor = dict_cursor,
            ss_cursor = ss_cursor,
        )

    @wraps(func)
    async def wrapper(*args, **kwargs):
        pool = await get_pool()
        connection = await pool.acquire()
        if dict_cursor:
            if ss_cursor:
                cursor = await connection.cursor(aiomysql.SSDictCursor)
            else:
                cursor = await connection.cursor(aiomysql.DictCursor)
        else:
            if ss_cursor:
                cursor = await connection.cursor(aiomysql.SSCursor)
            else:
                cursor = await connection.cursor()
        kwargs[connection_name] = connection
        kwargs[cursor_name] = cursor
        ret = await func(*args, **kwargs)
        await cursor.close()
        pool.release(connection)

        return ret

    return wrapper

async def query(statement: str, data: tuple=())-> list[tuple]:
    """
    Execute a SQL query statement (SELECT) and return all results.

    Args:
        statement:
            The SQL query statement to be executed.
        data:
            The data to be used in the query statement.

    Returns:
        A list of tuples representing the query results.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute(statement, data)
        ret = await cur.fetchall()
        return list(ret)

async def dml(statement: str, data: tuple | list[tuple] | None=())-> int:
    """
    Execute a DML statement (INSERT, UPDATE, DELETE).
    
    Args:
        statement:
            The DML statement to be executed.
        data:
            The data to be used in the DML statement. If a list of tuples is
            provided, executemany() will be used.

    Returns:
        The number of affected rows.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        try:
            if data is not None and isinstance(data, list):
                await cur.executemany(statement, data)
            else:
                await cur.execute(statement, data or ())
            await conn.commit()

            return cur.rowcount
        except Exception as e:
            await conn.rollback()
            raise e

async def transact(
    statements: list[str],
    data: list[tuple | list[tuple] | None] | None = None,
)-> int:
    """
    Execute multiple DML statements in a transaction.
    Args:
        statements:
            A list of DML statements to be executed.
        data:
            A list of data tuples or list of tuples corresponding to each
            statement. If None, empty tuples will be used. If the length of
            data is less than statements, the remaining statements will use
            empty tuples.

    Returns:
        The total number of affected rows.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        if data is None:
            data = [()] * len(statements)
        ns = len(statements)
        nd = len(data)
        if ns > nd:
            data = data.extend([()] * (ns - nd))
        try:
            rowcount = 0
            for st, dt in zip(statements[:ns], data[:ns]):
                if dt is not None and isinstance(dt, list):
                    await cur.executemany(st, dt)
                else:
                    await cur.execute(st, dt or ())
                rowcount += cur.rowcount
            await conn.commit()

            return rowcount
        except Exception as e:
            await conn.rollback()
            raise e

# TODO: init

# _INIT_RSS_SCRIPTS = [
#     "DROP TABLE IF EXISTS entity_name_blacklist",
#     "DROP TABLE IF EXISTS entity_alias_map",
#     "DROP TABLE IF EXISTS entity_cite",
#     "DROP TABLE IF EXISTS relation_cite",
#     "DROP TABLE IF EXISTS relations",
#     "DROP TABLE IF EXISTS entities",
#     "DROP TABLE IF EXISTS chunks",
#     "DROP TABLE IF EXISTS segments",
#     "DROP TABLE IF EXISTS doc_domain",
#     "DROP TABLE IF EXISTS documents",
#     """\
# CREATE TABLE documents (
#     id UUID PRIMARY KEY,
#     title VARCHAR(100) UNIQUE NOT NULL,
#     sn VARCHAR(50),
#     date DATE NOT NULL,
#     valid_from DATE NOT NULL,
#     valid_to DATE,
#     replaces VARCHAR(100),
#     pub_path VARCHAR(100) NOT NULL,
#     localizes VARCHAR(100),
#     authors VARCHAR(100),
#     kg_built BOOLEAN NOT NULL,
#     INDEX idx_valid_from (valid_from),
#     INDEX idx_valid_to (valid_to),
#     INDEX idx_pub_path (pub_path)
# );""",
#     """\
# CREATE TABLE segments (
#     id UUID PRIMARY KEY,
#     document_id UUID NOT NULL,
#     seq_no INT NOT NULL,
#     FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE chunks (
#     id UUID PRIMARY KEY,
#     segment_id UUID NOT NULL,
#     seq_no INT NOT NULL,
#     text VARCHAR(1000) NOT NULL,
#     FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE doc_domain (
#     document_id UUID NOT NULL,
#     domain VARCHAR(50) NOT NULL,
#     PRIMARY KEY (document_id, domain),
#     KEY idx_domain (domain),
#     FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE entities (
#     id UUID PRIMARY KEY,
#     name VARCHAR(100) NOT NULL,
#     type VARCHAR(50) NOT NULL,
#     description VARCHAR(500)
# );""",
#     """\
# CREATE TABLE entity_cite (
#     entity_id UUID NOT NULL,
#     segment_id UUID NOT NULL,
#     PRIMARY KEY (entity_id, segment_id),
#     FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
#     FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE relations (
#     id UUID PRIMARY KEY,
#     source_id UUID NOT NULL,
#     target_id UUID NOT NULL,
#     type VARCHAR(50) NOT NULL,
#     description VARCHAR(500),
#     strength FLOAT NOT NULL CHECK (strength >= 0),
#     UNIQUE KEY uniq_relation (source_id, target_id, type),
#     FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
#     FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE relation_cite (
#     relation_id UUID NOT NULL,
#     segment_id UUID NOT NULL,
#     PRIMARY KEY (relation_id, segment_id),
#     FOREIGN KEY (relation_id) REFERENCES relations(id) ON DELETE CASCADE,
#     FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE entity_alias_map (
#     alias VARCHAR(100) PRIMARY KEY,
#     normal_name VARCHAR(100) NOT NULL,
#     KEY idx_normal_name (normal_name)
# );""",
#     "CREATE TABLE entity_name_blacklist (stop_name VARCHAR(100) PRIMARY KEY);"
# ]
# 
# def init_rss():
#     data = [()] * len(_INIT_RSS_SCRIPTS)
#     transact(_INIT_RSS_SCRIPTS, data)


# import numpy as np
# 
# from ..dss import rss, vss
# 
# async def add_nonsense_patterns(patterns: list[str])-> dict:
#     from ..kernel import ef
#     nonsense_vectors = await ef(patterns)
#     with vss.connect() as cli:
#         if not cli.has_collection("nonsenses"):
#             from pymilvus import MilvusClient, DataType
#             schema = MilvusClient.create_schema(
#                 enable_dynamic_field=False,
#                 description="vectors of nonsense text patterns",
#             )
#             schema.add_field(
#                 field_name="id",
#                 datatype=DataType.INT64,
#                 is_primary=True,
#                 auto_id=True,
#             )
#             schema.add_field(
#                 field_name="vector",
#                 datatype=DataType.FLOAT_VECTOR,
#                 dim=1024,
#             )
#             schema.add_field(
#                 field_name="pattern",
#                 datatype=DataType.VARCHAR,
#                 max_length=1000,
#             )
#             index_params = cli.prepare_index_params()
#             index_params.add_index(
#                 field_name="vector",
#                 index_name="vec_idx",
#                 index_type="AUTOINDEX",
#                 metric_type="COSINE",
#             )
#             cli.create_collection(
#                 collection_name="nonsenses",
#                 schema=schema,
#                 index_params=index_params,
#             )
#         data = [{"vector": vec, "pattern": pat}
#                 for vec, pat in zip(nonsense_vectors["dense"], patterns)]
#         res = cli.insert(collection_name="nonsenses", data=data)
# 
#     return res
# 
# def _get_nonsense_vectors():
#     results = vss.query(collection_name="nonsenses", output_fields=["vector"])
#     return np.array([x["vector"] for x in results])
# 
# def _get_chunk_vectors_by_doc_ids(doc_ids: list[str]):
#     ret = vss.query(
#         collection_name="chunks",
#         filter=f"doc_id IN {doc_ids}",
#         output_fields=["dense_vec"]
#     )
#     return np.array([x["dense_vec"] for x in ret]), [x["id"] for x in ret]
# 
# def detect_nonsense_chunks(doc_ids: list[str])-> dict[str, float]:
#     nss_vecs = _get_nonsense_vectors()
#     chk_vecs, chk_ids = _get_chunk_vectors_by_doc_ids(doc_ids)
#     scores = nss_vecs @ chk_vecs.T
#     max_scores = np.max(scores, axis=0)
#     return {i: float(s) for i, s in zip(chk_ids, max_scores)}
# 

# from hurag.dss import rss, vss
# from pymilvus import DataType
# 
# sql = [
#     """\
# CREATE TABLE IF NOT EXISTS entity_alias_map (
#     alias VARCHAR(100) PRIMARY KEY,
#     entity_id UUID NOT NULL,
#     FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
# );""",
#     """\
# CREATE TABLE IF NOT EXISTS entity_name_blacklist (
#     stop_name VARCHAR(100) PRIMARY KEY
# );""",
# ]
# 
# def patch():
#     rss.transact(sql, [(),()])
#     with vss.connect() as cli:
#         if cli.has_collection("node_subvecs"):
#             cli.drop_collection("node_subvecs")
#         if cli.has_collection("nodes"):
#             cli.drop_collection("nodes")
#         schema = cli.create_schema(
#             enable_dynamic_field = False,
#             description = "dense and sparse vectors of entities"
#         )
#         schema.add_field(
#             field_name="id",
#             datatype=DataType.VARCHAR,
#             max_length=36,
#             is_primary=True,
#         )
#         schema.add_field(
#             field_name="dense_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         schema.add_field(
#             field_name="sparse_vec",
#             datatype=DataType.SPARSE_FLOAT_VECTOR,
#         )
#         schema.add_field(
#             field_name="name_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         schema.add_field(
#             field_name="desc_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         index_params = cli.prepare_index_params()
#         index_params.add_index(
#             field_name="dense_vec",
#             index_name="dense_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         index_params.add_index(
#             field_name="sparse_vec",
#             index_name="sparse_idx",
#             index_type="AUTOINDEX",
#             metric_type="IP"
#         )
#         index_params.add_index(
#             field_name="name_vec",
#             index_name="name_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         index_params.add_index(
#             field_name="desc_vec",
#             index_name="desc_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         cli.create_collection(
#             collection_name="nodes",
#             schema=schema,
#             index_params=index_params
#         )
#     print("patched okay")
# 
# if __name__ == "__main__":
#     patch()
# 
# from hurag.dss import rss
# 
# REGEX_GROUP = [
#     r"本(?:文|法|规定|条例|细则|办法|制度|要求|规范|标准)",
#     (
#         r"(?:相关|有关)"
#         r"(?:部门|机构|组织|单位|企业|规定|制度|法律|法规|规范|标准|要求)"
#     ),
#     (
#         r"各?(?:上级|下级|直属|所属|下属|本级)?"
#         r"各?(?:单位|部门|机构|单位|企业|公司)"
#     ),
#     (
#         r"第\s*(?:[一二三四五六七八九十百千万亿零〇两\d]+)"
#         r"\s*(?:分?[编册卷章]|部分|节|条|款|项)"
#     ),
#     r"(?:附件|附表|表|图)\s*(?:[一二三四五六七八九十百千万亿〇零两\d]+)",
#     r"个人|人员|法人|自然人|中华人民共和国",
#     r"(?:总|国家|省|区|市|县|分)(?:公司|局)",
#     r"全?(?:省|市)?(?:行业|系统)",
#     r"[一二三四]级目录编码",
# ]
# 
# ALIAS_TUPLES = [
#     ("中华人民共和国招标投标法", "中华人民共和国招标投标法"),
#     ("招标投标法", "中华人民共和国招标投标法"),
#     ("招投标法", "中华人民共和国招标投标法"),
#     ("标法", "中华人民共和国招标投标法"),
#     ("中华人民共和国招标投标法实施条例", "中华人民共和国招标投标法实施条例"),
#     ("招标投标法实施条例", "中华人民共和国招标投标法实施条例"),
#     ("招投标法实施条例", "中华人民共和国招标投标法实施条例"),
#     ("标法实施条例", "中华人民共和国招标投标法实施条例"),
#     ("工程、物资、服务管理委员会", "工程、物资、服务管理委员会"),
#     ("三项工作管理委员会", "工程、物资、服务管理委员会"),
#     ("三项工作管委会", "工程、物资、服务管理委员会"),
#     ("管委会", "工程、物资、服务管理委员会"),
#     ("采购工作领导小组", "采购工作领导小组"),
#     ("采购领导小组", "采购工作领导小组"),
#     ("采购办", "采购办"),
#     ("采购管理办公室", "采购办"),
#     ("采购工作领导小组办公室", "采购办"),
#     ("投资管理委员会", "投资管理委员会"),
#     ("投委会", "投资管理委员会"),
#     ("投资管理委员会办公室", "投资管理委员会办公室"),
#     ("投资办", "投资管理委员会办公室"),
#     ("采购价格咨询服务研究室", "采购价格咨询服务研究室"),
#     ("价格研究室", "采购价格咨询服务研究室"),
#     ("价研室", "采购价格咨询服务研究室"),
#     ("公开招标", "公开招标"),
#     ("公招", "公开招标"),
#     ("邀请招标", "邀请招标"),
#     ("邀标", "邀请招标"),
#     ("竞争性谈判", "竞争性谈判"),
#     ("竞争谈判", "竞争性谈判"),
#     ("竞谈", "竞争性谈判"),
#     ("竞争性磋商", "竞争性磋商"),
#     ("磋商", "竞争性磋商"),
#     ("竞磋", "竞争性磋商"),
#     ("直接采购", "直接采购"),
#     ("直采", "直接采购"),
#     ("质量管理小组", "质量管理小组"),
#     ("QC小组", "质量管理小组"),
#     ("质量管理小组活动", "质量管理小组活动"),
#     ("QC小组活动", "质量管理小组活动"),
#     ("QC活动", "质量管理小组活动"),
# ]
# 
# SQLS = [
#     "DELETE FROM entity_name_blacklist",
#     "INSERT INTO entity_name_blacklist VALUES (?)",
#     "DROP TABLE IF EXISTS entity_alias_map",
#     (
#         "CREATE TABLE entity_alias_map ("
#         "    alias VARCHAR(100) PRIMARY KEY,"
#         "    normal_name VARCHAR(100) NOT NULL,"
#         "    KEY idx_normal_name (normal_name)"
#         ");"
#     ),
#     "INSERT INTO entity_alias_map VALUES (?, ?)"
# ]
# def patch():
#     data = [(), [(x, ) for x in REGEX_GROUP], (), (), ALIAS_TUPLES]
#     rss.transact(SQLS, data)
#     print("patched okay.")
# 
# if __name__ == "__main__":
#     patch()
# 
# from hurag.dss import vss
# from pymilvus import MilvusClient, DataType
# 
# def patch():
#     with vss.connect() as cli:
#         if cli.has_collection("nodes"):
#             cli.drop_collection("nodes")
#         schema =  MilvusClient.create_schema(
#             enable_dynamic_field = False,
#             description = "dense and sparse vectors of entities"
#         )
#         schema.add_field(
#             field_name="id",
#             datatype=DataType.VARCHAR,
#             max_length=36,
#             is_primary=True,
#         )
#         schema.add_field(
#             field_name="dense_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         schema.add_field(
#             field_name="sparse_vec",
#             datatype=DataType.SPARSE_FLOAT_VECTOR,
#         )
#         index_params = cli.prepare_index_params()
#         index_params.add_index(
#             field_name="dense_vec",
#             index_name="dense_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         index_params.add_index(
#             field_name="sparse_vec",
#             index_name="sparse_idx",
#             index_type="AUTOINDEX",
#             metric_type="IP"
#         )
#         cli.create_collection(
#             collection_name="nodes",
#             schema=schema,
#             index_params=index_params
#         )
#     print("patched okay.")
# 
# if __name__ == "__main__":
#     patch()
# 
#         await add_nonsense_patterns(
#             [
#                 "附则 本规定中的“以上”含本数，“以下”不含本数",
#                 "附则 本规定由制定机构负责解释",
#                 "附则 各下属机构应按照本单位实际参照本规定制定相应的实施细则",
#                 "附则 本规定自印发之日起执行",
#             ]
#         )
#         print("无意义文本模板初始化完成")



