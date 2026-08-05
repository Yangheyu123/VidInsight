from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class AccountCreate(BaseModel):
    platform_open_id: str = Field(min_length=1, max_length=160)
    nickname: str = Field(min_length=1, max_length=100)
    alias: str | None = None
    priority: int = Field(default=3, ge=1, le=5)


class AccountPatch(BaseModel):
    nickname: str | None = None
    alias: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


class VideoImport(BaseModel):
    platform_item_id: str
    title: str = "未命名作品"
    published_at: datetime
    duration_ms: int | None = Field(default=None, ge=0)
    play_count: int = Field(ge=0)
    like_count: int = Field(ge=0)
    comment_count: int = Field(ge=0)
    forward_count: int = Field(ge=0)
    share_count: int = Field(default=0, ge=0)
    completion_rate: float = Field(ge=0, le=1)
    completion_sample_count: int | None = Field(default=None, ge=0)
    video_follow_conversion: float | None = Field(default=None, ge=0, le=1)
    collected_at: datetime
    source: Literal["douyin_api", "computer_use", "authorized_import", "contract_api", "controlled_crawler"] = "authorized_import"


class AccountSnapshotImport(BaseModel):
    follower_count: int = Field(ge=0)
    collected_at: datetime
    source: Literal["douyin_api", "computer_use", "authorized_import", "contract_api", "controlled_crawler"] = "authorized_import"


class ExportRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    account_ids: list[str] = []
    period: Literal["day", "week", "month", "custom"] = "custom"

