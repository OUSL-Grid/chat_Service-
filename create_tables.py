import asyncio

from app.database import engine, Base
from app import models  # noqa: F401  (importing registers the tables with Base)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Tables created!")


asyncio.run(main())