import threading
from asyncio import current_task
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import select

from app.core.logger import AppLogger
from app.core.models import meta, Listing

logger = AppLogger(name="database").get_logger()

class DatabaseClient:

    def __init__(self, url: str):
        self.db_connections = threading.local()
        self.url = url

    def async_engine(self) -> AsyncEngine:
        if not hasattr(self.db_connections, "engine"):
            logger.debug("Starting engine.")
            self.db_connections.engine = create_async_engine(self.url)
            logger.debug("Creating database engine finished.")
        return self.db_connections.engine

    def async_session_factory(self) -> async_sessionmaker:
        logger.debug("Starting session factory.")
        if not hasattr(self.db_connections, "session_factory"):
            engine = self.async_engine()
            self.db_connections.session_factory = async_sessionmaker(bind=engine)
        return self.db_connections.session_factory

    def async_scoped_session(self) -> async_scoped_session[AsyncSession]:
        logger.debug("Getting scoped session.")
        if not hasattr(self.db_connections, "scoped_session"):
            session_factory = self.async_session_factory()
            self.db_connections.scoped_session = async_scoped_session(
                session_factory, scopefunc=current_task
            )
        return self.db_connections.scoped_session

    async def cleanup(self):
        logger.debug("Cleaning database engine.")

        await self.db_connections.engine.dispose()
        logger.debug("Cleaning database finished.")

    async def create_models(self):
        logger.debug("Creating ORM modules.")
        async with self.async_engine().begin() as conn:
            await conn.run_sync(meta.create_all)
        logger.debug("Finished creating ORM modules.")

    async def insert_listing(self, session: AsyncSession, listing: Listing):
        session.add(listing)

    async def get_listings(self, limit: int = None):
        session_factory = self.async_session_factory()
        async with session_factory() as session:

            query = select(Listing)
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            listings = result.scalars().all()

            return listings

    async def get_listing_by_id(self, session: AsyncSession, item_id: str):

        result = await session.execute(
            select(Listing).where(Listing.item_id == item_id)
        )
        listing = result.scalar_one_or_none()

        return listing

    async def flush_listings(self):

        logger.info("Flushing all listings from database ...")

        session_factory = self.async_session_factory()
        async with session_factory() as session:
            # Count existing records
            from sqlalchemy import func, delete
            count_result = await session.execute(
                func.count(Listing.item_id)
            )
            count = count_result.scalar()

            if count == 0:
                logger.info("No listings to flush.")
                return 0

            # Delete all listings
            result = await session.execute(
                delete(Listing)
            )
            await session.commit()

            deleted_count = result.rowcount
            logger.info(f"Successfully flushed {deleted_count} listings from database.")
            return deleted_count