from __future__ import annotations
from pathlib import Path
from . import get_oa_client
from ..types import FILE_EXTRACT

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from openai.types import FileObject, FilePurpose


async def upload_file(
    file: Path,
    *,
    purpose: FilePurpose = FILE_EXTRACT,
    client: AsyncOpenAI | None = None,
) -> FileObject | None:
    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    try:
        return await client.files.create(file=file, purpose=purpose)
    except Exception:
        return None


async def upload_files(
    files: list[Path] | Path,
    *,
    purpose: FilePurpose = FILE_EXTRACT,
    client: AsyncOpenAI | None = None,
) -> list[FileObject | None]:
    if not isinstance(files, list):
        files = [files]

    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    import asyncio

    sem = asyncio.Semaphore(20)

    async def _upload(file: Path) -> FileObject | None:
        async with sem:
            return await upload_file(file=file, purpose=purpose, client=client)

    results = await asyncio.gather(*(_upload(f) for f in files))

    return list(results)

async def extract_file_content(
    file: Path,
    *,
    client: AsyncOpenAI | None = None,
    keep_uploaded: bool = False,
) -> str | None:
    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    try:
        file_object = await client.files.create(file=file, purpose=FILE_EXTRACT)
        file_content = await client.files.content(file_id=file_object.id)

        if not keep_uploaded:
            await client.files.delete(file_id=file_object.id)

        return file_content.text
    except Exception:
        return None


async def extract_files(
    files: list[Path] | Path,
    *,
    keep_uploaded: bool = False,
    client: AsyncOpenAI | None = None,
) -> list[str | None]:
    if not isinstance(files, list):
        files = [files]

    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    import asyncio

    sem = asyncio.Semaphore(20)

    async def _extract(file: Path) -> str | None:
        async with sem:
            return await extract_file_content(
                file=file, keep_uploaded=keep_uploaded, client=client
            )

    results = await asyncio.gather(*(_extract(f) for f in files))

    return list(results)


async def delete_file(file_id: str, *, client: AsyncOpenAI | None = None) -> int:
    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    try:
        await client.files.delete(file_id=file_id)
        ret = 1
    except Exception:
        ret = 0

    return ret


async def list_files(client: AsyncOpenAI | None = None) -> list[FileObject]:
    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    file_list = await client.files.list()
    return file_list.data


async def clean_files(client: AsyncOpenAI | None = None) -> int:
    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    import asyncio

    sem = asyncio.Semaphore(20)
    count = 0

    async def _delete(file_id: str) -> None:
        nonlocal count
        async with sem:
            result = await delete_file(file_id=file_id, client=client)
            count += result

    file_list = await client.files.list()
    await asyncio.gather(*(_delete(f.id) for f in file_list.data))

    return count
