import logging
import sys
from src.core.config import settings


logging.getLogger("rq.worker").setLevel(logging.ERROR)
logging.getLogger("rq").setLevel(logging.ERROR)
logging.getLogger("google.api_core").setLevel(logging.ERROR)
logging.getLogger("grpc").setLevel(logging.ERROR)
logging.getLogger("google.generativeai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    # avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(
        logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    )

    # format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger