from __future__ import annotations
from pathlib import Path
from . import get_oa_client
from .. import logger
from typing import cast

from typing import TYPE_CHECKING, AsyncGenerator

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from openai import BadRequestError, RateLimitError, APITimeoutError
from openai.types import FileObject, FilePurpose

if TYPE_CHECKING:
    from openai import AsyncOpenAI


# Moonshot file purpose
FILE_EXTRACT = cast(FilePurpose, "file-extract")
IMAGE = cast(FilePurpose, "image")
VIDEO = cast(FilePurpose, "video")

def is_retryable_error(exception: BaseException) -> bool:
    if isinstance(exception, (RateLimitError, APITimeoutError, BadRequestError)):
        return True
    return False


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception(is_retryable_error),
)
async def _upload_file_with_retry(
    client: AsyncOpenAI, file: Path, purpose: FilePurpose
) -> FileObject:
    return await client.files.create(file=file, purpose=purpose)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception(is_retryable_error),
)
async def _get_content_with_retry(client: AsyncOpenAI, file_id: str) -> str:
    response = await client.files.content(file_id=file_id)
    return response.text


async def upload_file(
    file: Path,
    client: AsyncOpenAI,
    *,
    purpose: FilePurpose = FILE_EXTRACT,
) -> FileObject | None:
    try:
        return await _upload_file_with_retry(client, file, purpose)
    except Exception as e:
        logger.error(f"{file.name} uploading failed: {e!r}")
        return None


async def upload_files(
    files: list[Path] | Path,
    *,
    purpose: FilePurpose = FILE_EXTRACT,
    client: AsyncOpenAI | None = None,
) -> AsyncGenerator[FileObject | None, None]:
    if not isinstance(files, list):
        files = [files]

    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    import asyncio

    sem = asyncio.Semaphore(20)

    async def _upload(file: Path) -> FileObject | None:
        async with sem:
            return await upload_file(file=file, purpose=purpose, client=client)

    tasks = [asyncio.create_task(_upload(f)) for f in files]

    for task in asyncio.as_completed(tasks):
        yield await task

async def extract_file_content(
    file: Path,
    client: AsyncOpenAI,
    *,
    keep_uploaded: bool = False,
) -> dict | None:
    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    try:
        file_object = await _upload_file_with_retry(client, file, FILE_EXTRACT)
        file_content = await _get_content_with_retry(client, file_object.id)

        if not keep_uploaded:
            await client.files.delete(file_id=file_object.id)

        return {"path": file, "content": file_content}
    except Exception as e:
        logger.error(f"{file.name} extracting content failed: {e!r}")
        return None


async def extract_files(
    files: list[Path] | Path,
    *,
    keep_uploaded: bool = False,
    client: AsyncOpenAI | None = None,
) -> AsyncGenerator[dict | None, None]:
    if not isinstance(files, list):
        files = [files]

    client = client or await get_oa_client(client_name="multimodal", multimodal=True)

    import asyncio

    sem = asyncio.Semaphore(20)

    async def _extract(file: Path) -> dict | None:
        async with sem:
            return await extract_file_content(
                file=file, keep_uploaded=keep_uploaded, client=client
            )

    tasks = [asyncio.create_task(_extract(f)) for f in files]

    for task in asyncio.as_completed(tasks):
        yield await task


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
