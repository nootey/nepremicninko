import asyncio
import time
from logging import Logger

import pytz
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import config
from app.core.database import DatabaseClient
from app.services.crawler import crawl


async def run_scrape_job(logger: Logger):
    start = time.time()
    logger.info("Scheduled scrape triggered")
    db_client = None

    try:
        # Fresh connection for each scrape
        db_client = DatabaseClient(url=f"sqlite+aiosqlite:///{config.database.path}", logger=logger)

        await crawl(db_client, logger)

        elapsed = time.time() - start
        logger.info(f"Scrape completed in {elapsed:.2f} seconds")

    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}", exc_info=True)
    finally:
        if db_client:
            await db_client.cleanup()


async def start_scheduler(logger: Logger) -> None:

    s_logger = logger.getChild("scheduler")
    scheduler = AsyncIOScheduler()

    def handle_job_executed(event: JobExecutionEvent):
        job = scheduler.get_job(event.job_id)
        if job and job.next_run_time:
            s_logger.info(f"Next run scheduled at: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    def handle_job_error(event: JobExecutionEvent):
        s_logger.error(f"Scheduled job failed: {event.exception}", exc_info=True)

    scheduler.add_listener(handle_job_error, EVENT_JOB_ERROR)
    scheduler.add_listener(handle_job_executed, EVENT_JOB_EXECUTED)

    timezone = pytz.timezone(config.scheduler.timezone)

    scheduler.add_job(
        run_scrape_job,
        "interval",
        args=[s_logger],
        minutes=config.scheduler.interval_minutes,
        timezone=timezone,
        max_instances=1,
    )

    scheduler.start()

    next_run = scheduler.get_jobs()[0].next_run_time
    s_logger.info(f"Scheduler started - next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        s_logger.info("Scheduler shutting down gracefully")
        scheduler.shutdown()
