from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DownloadStatus(enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class TorrentDownload(Base):
    __tablename__ = "torrent_downloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    magnet_uri: Mapped[str] = mapped_column(String, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)  # "movie" or "tv"
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), default=DownloadStatus.PENDING
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    eta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    save_path: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    files: Mapped[list[DownloadedFile]] = relationship(
        "DownloadedFile", back_populates="torrent", cascade="all, delete-orphan"
    )


class DownloadedFile(Base):
    __tablename__ = "downloaded_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    torrent_id: Mapped[int] = mapped_column(ForeignKey("torrent_downloads.id"))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    final_path: Mapped[str] = mapped_column(String, nullable=False)
    moved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    torrent: Mapped[TorrentDownload] = relationship(
        "TorrentDownload", back_populates="files"
    )
