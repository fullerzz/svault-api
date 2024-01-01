import logging
from typing import Annotated, Any

from icecream import ic
from litestar import Litestar, MediaType, get, post
from litestar.contrib.sqlalchemy.base import UUIDBase
from litestar.contrib.sqlalchemy.plugins import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
)
from litestar.datastructures import UploadFile
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.params import Body
from rich.logging import RichHandler

from svault_api.models import (
    S3Object,
    UserFile,
    UserFileModel,
    UserFileRespository,
    UserUploadFile,
    provide_user_file_repo,
)
from svault_api.s3_client import S3Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger: logging.Logger = logging.getLogger(__name__)

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
async def get_media(user_file_repo: UserFileRespository) -> list[S3Object]:
    return await s3_client.get_all_objects()


@post(path="/media/upload", media_type=MediaType.JSON)
async def upload_file(
    user_file_repo: UserFileRespository,
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, Any]:
    logger.info(f"Received file: {data.filename}")
    file_content: bytes = await data.read()
    user_upload_file = UserUploadFile(filename=data.filename, file_content=file_content)

    s3obj = await s3_client.upload(user_upload_file)
    ic(s3obj)

    obj: UserFileModel = await user_file_repo.add(
        UserFileModel(
            filename=user_upload_file.filename,
            bucket_name=s3obj.bucket_name,
            key=s3obj.key,
            uploaded_timestamp=s3obj.uploaded_timestamp,
            created_timestamp=s3obj.uploaded_timestamp,
        )
    )
    ic(obj)

    await user_file_repo.session.commit()
    ic(UserFile.model_validate(obj))

    return {"result": "File uploaded successfully", "s3_object": s3obj.model_dump()}


app = Litestar(
    route_handlers=[index, get_media, upload_file],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
    dependencies={"user_file_repo": Provide(provide_user_file_repo)},
)
