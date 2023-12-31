from datetime import datetime

from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

UTC_TZ = ZoneInfo("UTC")
BUCKET_NAME: str = "fullerzz-media"
REGION: str = "us-west-1"


class S3Object(BaseModel):
    bucket_name: str
    object_name: str
    object_content: str


class UserFile(BaseModel):
    filename: str
    file_content: str
    created_timestamp: datetime | None = None
    uploaded_timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC_TZ))
