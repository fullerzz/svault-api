import logging
from typing import Annotated, Any

from litestar import Litestar, MediaType, Request, Response, get, post
from litestar.contrib.sqlalchemy.base import UUIDBase
from litestar.contrib.sqlalchemy.plugins import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
)
from litestar.datastructures import UploadFile
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.params import Body

from svault_api.models import (
    S3Object,
    UserFile,
    UserFileModel,
    UserFileRespository,
    UserUploadFile,
    provide_user_file_repo,
)
from svault_api.s3_client import S3Client

logging_config = LoggingConfig(
    root={"level": logging.getLevelName(logging.INFO), "handlers": ["console"]},
    formatters={"standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
)
logger = logging_config.configure()()

s3_client = S3Client()
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config
)  # Create 'async_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


def app_exception_handler(request: Request, exc: HTTPException) -> Response:  # type: ignore
    return Response(
        content={
            "error": "server error",
            "path": request.url.path,
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
        status_code=500,
    )


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)


@get("/")
async def index() -> str:
    return "Hello, world!"


@get("/media/s3", media_type=MediaType.JSON)
async def get_media_s3(user_file_repo: UserFileRespository) -> list[S3Object]:
    return await s3_client.get_all_objects()


@get("/media")
async def get_media(user_file_repo: UserFileRespository) -> list[UserFile]:
    logger.info("Getting files from database")
    try:
        rows: list[UserFileModel] = await user_file_repo.list()
        files: list[UserFile] = [UserFile.model_validate(row) for row in rows]
    except Exception as ex:
        logger.exception("Error getting files from database")
        raise HTTPException(detail=repr(ex)) from ex
    return files


@get("/media/{file_id: str}")
async def get_media_by_id(user_file_repo: UserFileRespository, file_id: str) -> UserFile:
    logger.info(f"Querying database for file_id: {file_id}")
    file_model: UserFileModel = await user_file_repo.get(file_id)
    file: UserFile = UserFile.model_validate(file_model)
    return file  # TODO: Return 404 if not found


@post(path="/media/upload", media_type=MediaType.JSON)
async def upload_file(
    user_file_repo: UserFileRespository,
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, Any]:
    logger.info(f"Received file: {data.filename}")
    file_content: bytes = await data.read()
    user_upload_file = UserUploadFile(filename=data.filename, file_content=file_content)

    s3_obj = await s3_client.upload(user_upload_file)

    user_file: UserFileModel = await user_file_repo.add(
        UserFileModel(
            filename=user_upload_file.filename,
            bucket_name=s3_obj.bucket_name,
            key=s3_obj.key,
            uploaded_timestamp=s3_obj.uploaded_timestamp,
            created_timestamp=s3_obj.uploaded_timestamp,
        )
    )

    await user_file_repo.session.commit()
    logger.info(f"{UserFile.model_validate(user_file)!s}")

    return {"result": "File uploaded successfully", "user_file": UserFile.model_validate(user_file)}


app = Litestar(
    route_handlers=[index, get_media, get_media_by_id, upload_file],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
    dependencies={"user_file_repo": Provide(provide_user_file_repo)},
    logging_config=logging_config,
    exception_handlers={HTTPException: app_exception_handler},
)
