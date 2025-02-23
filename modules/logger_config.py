# -----------------------------------------------------------------------------
# logger_config.py
# -----------------------------------------------------------------------------

import logging

# Define the logging format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Create a logger named 'duplicateDeducer'
logger = logging.getLogger("duplicateDeducer")
logger.setLevel(logging.INFO)

# Prevent adding multiple handlers if they already exist
if not logger.handlers:
	# File handler for logging to a file
	fileHandler = logging.FileHandler("duplicate_finder.log", mode="w")
	fileHandler.setFormatter(formatter)
	logger.addHandler(fileHandler)

	# Stream handler for logging to the console
	streamHandler = logging.StreamHandler()
	streamHandler.setFormatter(formatter)
	logger.addHandler(streamHandler)
	
# -----------------------------------------------------------------------------
# End of logger_config.py
# -----------------------------------------------------------------------------