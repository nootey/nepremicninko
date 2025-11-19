import logging
from datetime import datetime
from pathlib import Path

from pythonjsonlogger import jsonlogger


class AppLogger:
    def __init__(
        self,
        name: str = __name__,
        log_dir: str = "logs",
        level: int = logging.INFO,
    ):

        # Ensure log directory exists
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Generate log filename with today's date
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = Path(log_dir) / f"app-{date_str}.log"

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False  # avoid duplicate logs

        # Prevent duplicate handlers
        if not self.logger.handlers:
            # --- File handler (JSON format)
            file_handler = logging.FileHandler(filename=log_file)
            file_formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # --- Console handler (simple format)
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "[%(levelname)s] %(asctime)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger