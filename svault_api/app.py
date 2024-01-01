from typing import Annotated, Any

from icecream import ic
from litestar import Litestar, MediaType, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

from svault_api.models import S3Object, UserUploadFile
from svault_api.s3_client import S3Client

s3_client = S3Client()


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


app = Litestar([index, get_media, upload_file])
