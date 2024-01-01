import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.plugins import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
)
from pydantic import UUID4, BaseModel, Field
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

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


## SQLAlchemy Models
class UserFile(UUIDBase):
    filename: Mapped[str]
    bucket_name: Mapped[str]
    key: Mapped[str]
    uploaded_timestamp: Mapped[datetime]
    created_timestamp: Mapped[datetime]


session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config
)  # Create 'async_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)
