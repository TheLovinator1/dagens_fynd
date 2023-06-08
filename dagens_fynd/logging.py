import sys

from loguru import logger


def add_logger() -> None:
    """Add our own logger."""
    log_format: str = (
        "<green>{time:YYYY-MM-DD at HH:mm:ss}</green> <level>{message}</level> <yellow>{extra[name]}</yellow>"
        " <cyan>{extra[price]}</cyan>"
    )

    # Log to file
    logger.add(
        "logs/dagens_fynd.json",
        level="INFO",
        rotation="1GB",
        compression="zip",
        serialize=True,
    )

    # Log to stderr
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
