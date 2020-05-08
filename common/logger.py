import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


def logger(name):
    return logging.getLogger(name)
