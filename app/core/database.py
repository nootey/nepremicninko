import threading
from asyncio import current_task
from datetime import datetime
from logging import Logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.core.models import ConfigState, Listing, meta


class DatabaseClient:
    def __init__(self, url: str, logger: Logger):
        self.db_connections = threading.local()
        self.url = url
        self.logger = logger.getChild("database")

    def async_engine(self) -> AsyncEngine:
        if not hasattr(self.db_connections, "engine"):
            self.logger.debug("Starting engine.")
            self.db_connections.engine = create_async_engine(self.url)
            self.logger.debug("Creating database engine finished.")
        return self.db_connections.engine

    def async_session_factory(self) -> async_sessionmaker:
        self.logger.debug("Starting session factory.")
        if not hasattr(self.db_connections, "session_factory"):
            engine = self.async_engine()
            self.db_connections.session_factory = async_sessionmaker(bind=engine)
        return self.db_connections.session_factory

    def async_scoped_session(self) -> async_scoped_session[AsyncSession]:
        self.logger.debug("Getting scoped session.")
        if not hasattr(self.db_connections, "scoped_session"):
            session_factory = self.async_session_factory()
            self.db_connections.scoped_session = async_scoped_session(session_factory, scopefunc=current_task)
        return self.db_connections.scoped_session

    async def cleanup(self):
        self.logger.debug("Cleaning database engine.")

        await self.db_connections.engine.dispose()
        self.logger.debug("Cleaning database finished.")

    async def create_models(self):
        self.logger.debug("Creating ORM modules.")
        async with self.async_engine().begin() as conn:
            await conn.run_sync(meta.create_all)
        self.logger.debug("Finished creating ORM modules.")

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
        result = await session.execute(select(Listing).where(Listing.item_id == item_id))
        listing = result.scalar_one_or_none()

        return listing

    async def flush_listings(self):
        self.logger.info("Flushing all listings from database ...")

        session_factory = self.async_session_factory()
        async with session_factory() as session:
            # Count existing records
            from sqlalchemy import delete, func

            count_result = await session.execute(func.count(Listing.item_id))
            count = count_result.scalar()

            if count == 0:
                self.logger.info("No listings to flush.")
                return 0

            # Delete all listings
            result = await session.execute(delete(Listing))
            await session.commit()

            deleted_count = result.rowcount
            self.logger.info(f"Successfully flushed {deleted_count} listings from database.")
            return deleted_count

    async def get_url_hash(self):
        """Get the stored URL configuration hash."""
        session_factory = self.async_session_factory()
        async with session_factory() as session:
            result = await session.execute(select(ConfigState))
            config_state = result.scalar_one_or_none()

            return config_state.url_hash if config_state else None

    async def set_url_hash(self, url_hash: str):
        """Store the URL configuration hash."""
        session_factory = self.async_session_factory()
        async with session_factory() as session:
            result = await session.execute(select(ConfigState))
            config_state = result.scalar_one_or_none()

            if config_state:
                config_state.url_hash = url_hash
                config_state.updated_at = datetime.now()
            else:
                config_state = ConfigState(url_hash=url_hash, updated_at=datetime.now())
                session.add(config_state)

            await session.commit()
            self.logger.info(f"Stored URL hash: {url_hash}")

    async def get_schema_hash(self):
        """Get the stored schema hash."""
        session_factory = self.async_session_factory()
        async with session_factory() as session:
            result = await session.execute(select(ConfigState))
            config_state = result.scalar_one_or_none()
            return config_state.schema_hash if config_state and hasattr(config_state, "schema_hash") else None

    async def set_schema_hash(self, schema_hash: str):
        """Store the schema hash."""
        session_factory = self.async_session_factory()
        async with session_factory() as session:
            result = await session.execute(select(ConfigState))
            config_state = result.scalar_one_or_none()

            if config_state:
                config_state.schema_hash = schema_hash
                config_state.updated_at = datetime.now()
            else:
                config_state = ConfigState(url_hash="", schema_hash=schema_hash, updated_at=datetime.now())
                session.add(config_state)

            await session.commit()
            self.logger.info(f"Stored schema hash: {schema_hash}")
