import asyncio
from pathlib import Path

from app.core.config import config
from app.core.database import DatabaseManager
from app.core.logger import AppLogger

logger = AppLogger(name="scraper").get_logger()

async def main():
    logger.info("Starting scraper application")
    db_manager = None
    try:
        # Ensure database directory exists
        db_path = Path(config.DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database directory ready: {db_path.parent}")

        # Initialize database manager
        db_manager = DatabaseManager(url=f"sqlite+aiosqlite:///{config.DB_PATH}")

        # Create tables if they don't exist
        await db_manager.create_models()
        logger.info("Database initialized successfully")

        # TODO: Add scraper logic here

        logger.info("Scraper finished successfully")

    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        raise
    finally:
        # Clean up database connections
        if 'db_manager' in locals():
            await db_manager.cleanup()
            logger.info("Database cleanup completed")

if __name__ == "__main__":
    asyncio.run(main())