from __future__ import annotations

import collections.abc

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config.settings import settings

engine = create_async_engine(settings.database.url, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> collections.abc.AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
