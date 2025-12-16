import asyncio
from pathlib import Path

from app.core.config import config
from app.core.database import DatabaseClient
from app.core.logger import AppLogger
from app.services.crawler import crawl
from app.services.scheduler import start_scheduler


async def main():

    logger = AppLogger(name="app").get_logger()
    logger.info("Starting application")
    db_client = None

    try:
        # Ensure database directory exists
        db_path = Path(config.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database directory ready: {db_path.parent}")

        # Initialize database client
        db_client = DatabaseClient(url=f"sqlite+aiosqlite:///{config.database.path}", logger=logger)

        # Create tables if they don't exist
        await db_client.create_models()
        logger.info("Database initialized successfully")

        # Run initial scrape
        logger.info("Starting initial scrape ...")
        await crawl(db_client, logger)
        logger.info("Initial scrape completed")

        # Close the connection
        await db_client.cleanup()

        # Start scheduler if enabled
        if config.scheduler.enabled:
            logger.info("Starting scheduler ...")
            await start_scheduler(logger)
        else:
            logger.info("Scheduler disabled, exiting after initial scrape")

    except Exception as e:
        logger.error(f"Application failure: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
