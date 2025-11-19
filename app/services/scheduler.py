import asyncio
import time

import pytz
from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import config
from app.core.logger import AppLogger
from app.services.crawler import crawl

logger = AppLogger(name="scheduler").get_logger()

async def run_scrape_job(db_client):

    start = time.time()
    logger.info("Scheduled scrape triggered")

    try:
        await crawl(db_client)
        elapsed = time.time() - start
        logger.info(f"Scrape completed in {elapsed:.2f} seconds")
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}", exc_info=True)


def handle_job_error(event: JobExecutionEvent):
    logger.error(f"Scheduled job failed: {event.exception}", exc_info=True)


async def start_scheduler(db_client) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_listener(handle_job_error, EVENT_JOB_ERROR)

    timezone = pytz.timezone(config.SCHEDULER_TIMEZONE)

    scheduler.add_job(
        run_scrape_job,
        'cron',
        minute=f"*/{config.SCHEDULER_INTERVAL_MINUTES}",
        timezone=timezone,
        args=[db_client]
    )

    scheduler.start()

    next_run = scheduler.get_jobs()[0].next_run_time
    logger.info(f"Scheduler started — next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutting down gracefully")
        scheduler.shutdown()