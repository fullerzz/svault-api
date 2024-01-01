import uuid
from datetime import datetime

from litestar.datastructures import UploadFile
from pydantic import UUID4, BaseModel, ConfigDict, Field
from zoneinfo import ZoneInfo

UTC_TZ = ZoneInfo("UTC")


class S3Object(BaseModel):
    bucket_name: str
    key: str
    uploaded_timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC_TZ))


class UserUploadFile(BaseModel):
    filename: str
    file_content: bytes
    file_uuid: UUID4 = Field(default_factory=lambda: uuid.uuid4())
    created_timestamp: datetime | None = None
