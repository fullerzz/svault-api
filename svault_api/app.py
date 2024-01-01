from typing import Annotated, Any

from icecream import ic
from litestar import Litestar, MediaType, get, post
from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.plugins import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
)
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from svault_api.models import S3Object, UserUploadFile
from svault_api.s3_client import S3Client

s3_client = S3Client()
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config
)  # Create 'async_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)


@get("/")
async def index() -> str:
    return "Hello, world!"


@get("/media", media_type=MediaType.JSON)
async def get_media() -> list[S3Object]:
    return await s3_client.get_all_objects()


@post(path="/media/upload", media_type=MediaType.JSON)
async def upload_file(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, Any]:
    file_content: bytes = await data.read()
    user_upload_file = UserUploadFile(filename=data.filename, file_content=file_content)
    s3obj = await s3_client.upload(user_upload_file)
    ic(s3obj)
    return {"result": "File uploaded successfully", "s3_object": s3obj.model_dump()}


app = Litestar(
    route_handlers=[index, get_media, upload_file],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
)
