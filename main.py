import asyncio
from pathlib import Path

from app.core.config import config
from app.core.database import DatabaseClient
from app.core.logger import AppLogger
from app.services.crawler import crawl

logger = AppLogger(name="scraper").get_logger()

async def main():
    logger.info("Starting scraper application")
    db_client = None
    try:
        # Ensure database directory exists
        db_path = Path(config.DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database directory ready: {db_path.parent}")

        # Initialize database client
        db_client = DatabaseClient(url=f"sqlite+aiosqlite:///{config.DB_PATH}")

        # Create tables if they don't exist
        await db_client.create_models()
        logger.info("Database initialized successfully")


        await crawl(db_client)

        logger.info("Scraper finished successfully")

    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        raise
    finally:
        # Clean up database connections
        if 'db_client' in locals():
            await db_client.cleanup()
            logger.info("Database cleanup completed")

if __name__ == "__main__":
    asyncio.run(main())