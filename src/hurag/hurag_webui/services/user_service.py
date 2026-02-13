from .. import db_pool_name, logger, conf
from ...utilities import generate_id
from ...dss import rss
from ..models import User


async def get_user(account: str) -> User | None:
    resp = await rss.query(
        "SELECT id, account, username, user_path FROM users WHERE account = %s",
        (account,),
        as_dict=True,
        pool_name=db_pool_name,
    )
    return User(**resp[0]) if resp else None


async def get_user_by_id(id: str) -> User | None:
    resp = await rss.query(
        "SELECT id, account, username, user_path FROM users WHERE id = %s",
        (id,),
        as_dict=True,
        pool_name=db_pool_name,
    )
    return User(**resp[0]) if resp else None


async def is_account_exist(account: str) -> bool:
    resp = await rss.query(
        "SELECT 1 FROM users WHERE account = %s",
        (account,),
        pool_name=db_pool_name,
    )
    return bool(resp)


async def is_user_id_exist(user_id: str) -> bool:
    resp = await rss.query(
        "SELECT 1 FROM users WHERE id = %s",
        (user_id,),
        pool_name=db_pool_name,
    )
    return bool(resp)


async def is_user_valid(user_id: str, account: str) -> bool:
    resp = await rss.query(
        "SELECT 1 FROM users WHERE id = %s AND account = %s",
        (user_id, account),
        pool_name=db_pool_name,
    )
    return bool(resp)


async def upsert_user(account, username, user_path) -> User | None:
    _ = await rss.dml(
        """
        INSERT INTO users (id, account, username, user_path)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            user_path = VALUES(user_path)
        """,
        (generate_id(), account, username, user_path),
        pool_name=db_pool_name,
    )
    return await get_user(account)


async def login(account: str):
    sso_info = None
    if conf.webui_app.sso is not None:
        # should change to real sso service later
        logger.error("SSO is unavailable, login failed.")
    else:
        import csv
        from pathlib import Path

        with open(Path.cwd() / "native_sso.csv", "r", encoding="utf-8") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                if row["account"] == account:
                    sso_info = row.copy()
                    sso_info.pop("password")
                    break

    if sso_info is not None:
        user = await upsert_user(**sso_info)
        return user

    return None
