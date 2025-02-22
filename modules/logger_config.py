# -----------------------------------------------------------------------------
# logger_config.py
# -----------------------------------------------------------------------------


import logging

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("duplicate_deducer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler("duplicate_finder.log", mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)