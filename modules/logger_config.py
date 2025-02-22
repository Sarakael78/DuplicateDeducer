# -----------------------------------------------------------------------------
# logger_config.py
# -----------------------------------------------------------------------------

import logging

# Define the logging format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Create a logger named 'duplicate_deducer'
logger = logging.getLogger("duplicate_deducer")
logger.setLevel(logging.INFO)

# Prevent adding multiple handlers if they already exist
if not logger.handlers:
    # File handler for logging to a file
    file_handler = logging.FileHandler("duplicate_finder.log", mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream handler for logging to the console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)