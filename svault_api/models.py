import logging
import uuid
from datetime import datetime

from advanced_alchemy import SQLAlchemyAsyncRepository
from litestar.contrib.sqlalchemy.base import UUIDBase
from pydantic import UUID4, BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from zoneinfo import ZoneInfo

UTC_TZ = ZoneInfo("UTC")
logger: logging.Logger = logging.getLogger(__name__)


class S3Object(BaseModel):
    bucket_name: str
    key: str
    uploaded_timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC_TZ))


class UserUploadFile(BaseModel):
    filename: str
    file_content: bytes
    file_uuid: UUID4 = Field(default_factory=lambda: uuid.uuid4())
    created_timestamp: datetime | None = None


## SQLAlchemy Models
class UserFileModel(UUIDBase):
    filename: Mapped[str]
    bucket_name: Mapped[str]
    key: Mapped[str]
    uploaded_timestamp: Mapped[datetime]
    created_timestamp: Mapped[datetime]


class UserFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None  # noqa: A003
    filename: str
    bucket_name: str
    key: str
    uploaded_timestamp: datetime
    created_timestamp: datetime


class UserFileRespository(SQLAlchemyAsyncRepository[UserFileModel]):
    model_type = UserFileModel


async def provide_user_file_repo(db_session: AsyncSession) -> UserFileRespository:
    return UserFileRespository(session=db_session)
