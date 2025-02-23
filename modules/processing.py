# -----------------------------------------------------------------------------
# processing.py
# -----------------------------------------------------------------------------

import os
import time
import base64
import logging
from io import BytesIO
from typing import Generator, Tuple, List, Optional, Callable, Union

import matplotlib.pyplot as plt

from modules.duplicate_finder import DuplicateFinder
from modules.file_manager import FileManager
from modules.logger_config import logger

# Configure logger
logger = logging.getLogger(__name__)

def stopScanFlag(stopFlag: Union[bool, Callable[[], bool]]) -> bool:
	"""
	Determines if a stop has been requested.

	Parameters:
	-----------
	stopFlag : Union[bool, Callable[[], bool]]
		External flag or callable to indicate a stop request.

	Returns:
	--------
	bool
		True if a stop has been requested, False otherwise.
	"""
	if callable(stopFlag):
		return stopFlag()
	return stopFlag

def stopScan() -> str:
	"""
	Signals an early termination of the scan.

	Returns:
	--------
	str
		Confirmation message indicating that a stop has been requested.
	"""
	logger.info("Stop scan requested by user.")
	return "Stop requested."

def processAction(
	foldersInput: str,
	fileExtension: str,
	minSize: float,
	action: str,
	targetFolder: Optional[str] = "",
	saveCsv: bool = False,
	stopFlag: Union[bool, Callable[[], bool]] = False
) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
	"""
	Processes user actions from the Gradio UI.
	Generates an advanced report automatically at the end of the duplicate scan.

	Parameters:
	-----------
	foldersInput : str
		Folder path(s) to scan. Can be a single path or multiple paths provided one per line.
	fileExtension : str
		Optional file extension filter (e.g., .txt, .jpg).
	minSize : float
		Minimum file size in MB to be considered for scanning.
	action : str
		The action to perform (e.g., "Find Duplicates", "Delete Duplicates").
	targetFolder : Optional[str], optional
		Destination folder for moving duplicates. Required if action is "Move Duplicates".
	saveCsv : bool, optional
		Flag indicating whether to save duplicate information as a CSV file.
	stopFlag : Union[bool, Callable[[], bool]], optional
		Flag or callable indicating whether to stop the scan.

	Yields:
	-------
	Tuple[str, str, str, str, str, str]
		A tuple containing status message, main output HTML, progress HTML, scan statistics,
		advanced report HTML, and log output.
	"""
	if stopScanFlag(stopFlag):
		logger.info("Scan cancellation requested before start.")
		yield ("Scan cancelled", "", "<progress value='0' max='100'></progress>", "", "", getLogContent())
		return

	# Convert minimum size from MB to bytes.
	minSizeBytes: int = int(minSize * 1024 * 1024) if minSize > 0 else 0

	folders = [folder.strip() for folder in foldersInput.splitlines() if folder.strip()]
	for folder in folders:
		if not os.path.exists(folder):
			logger.error(f"Specified folder does not exist: {folder}")
			yield (
				"Error",
				f"The specified folder does not exist: {folder}",
				"<progress value='0' max='100'></progress>",
				"",
				"",
				getLogContent()
			)
			continue

		finder = DuplicateFinder(folder, fileExtension, minSizeBytes)
		finder.saveCsv = saveCsv

		if action == "Find Duplicates":
			yield from _findDuplicates(finder, stopFlag)
		elif action in ["Delete Duplicates", "Simulate Deletion", "Move Duplicates"]:
			yield from _manageDuplicates(finder, action, targetFolder)
		else:
			logger.error(f"Invalid action selected: {action}")
			yield (
				"Error",
				"Invalid action selected.",
				"<progress value='0' max='100'></progress>",
				"",
				"",
				getLogContent()
			)

def _findDuplicates(finder: DuplicateFinder, stopFlag: Union[bool, Callable[[], bool]]) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
	"""
	Handles the 'Find Duplicates' action.

	Parameters:
	-----------
	finder : DuplicateFinder
		An instance of DuplicateFinder.
	stopFlag : Union[bool, Callable[[], bool]]
		Flag or callable indicating whether to stop the scan.

	Yields:
	-------
	Tuple[str, str, str, str, str, str]
		Status updates and results based on the 'Find Duplicates' action.
	"""
	try:
		for status, html, progress, statsInfo in finder.findDuplicatesStream(lambda: stopScanFlag(stopFlag)):
			if status == "Finalisation":
				duplicates = finder.findDuplicates()
				advReport = _generateAdvancedReport(finder, duplicates)
				yield (status, html, progress, statsInfo, advReport, getLogContent())
			else:
				yield (status, html, progress, statsInfo, "", getLogContent())
	except Exception as e:
		logger.error(f"Error during duplicate search: {e}")
		yield (
			"Error",
			f"Error during duplicate search: {e}",
			"<progress value='0' max='100'></progress>",
			"",
			"",
			getLogContent()
		)

def _manageDuplicates(
	finder: DuplicateFinder,
	action: str,
	targetFolder: Optional[str]
) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
	"""
	Handles actions related to managing duplicates such as deletion, simulation, and moving.

	Parameters:
	-----------
	finder : DuplicateFinder
		An instance of DuplicateFinder.
	action : str
		The action to perform.
	targetFolder : Optional[str]
		Destination folder for moving duplicates.

	Yields:
	-------
	Tuple[str, str, str, str, str, str]
		Status updates and results based on the selected action.
	"""
	yield ("Scanning for Duplicates", "Scanning the folder for duplicates...", "<progress value='0' max='100'></progress>", "", "", getLogContent())
	try:
		duplicates = finder.findDuplicates()
	except Exception as e:
		logger.error(f"Error during duplicate search: {e}")
		yield (
			"Error",
			f"Error during duplicate search: {e}",
			"<progress value='0' max='100'></progress>",
			"",
			"",
			getLogContent()
		)
		return

	if not duplicates:
		advReport = _generateAdvancedReport(finder, duplicates)
		yield (
			"Result",
			"No duplicate files found.",
			"<progress value='100' max='100'></progress>",
			"",
			advReport,
			getLogContent()
		)
		return

	fileManager = FileManager()

	if action == "Delete Duplicates":
		yield from _deleteDuplicates(fileManager, finder, duplicates)
	elif action == "Simulate Deletion":
		yield from _simulateDeletion(fileManager, finder, duplicates)
	elif action == "Move Duplicates":
		if not targetFolder:
			yield (
				"Error",
				"Target folder must be specified for moving duplicates.",
				"<progress value='0' max='100'></progress>",
				"",
				"",
				getLogContent()
			)
			return
		yield from _moveDuplicates(fileManager, finder, duplicates, targetFolder)

def _deleteDuplicates(
	fileManager: FileManager,
	finder: DuplicateFinder,
	duplicates: List[Tuple[str, str]]
) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
	"""
	Deletes duplicate files.

	Parameters:
	-----------
	fileManager : FileManager
		An instance of FileManager.
	finder : DuplicateFinder
		An instance of DuplicateFinder.
	duplicates : List[Tuple[str, str]]
		List of duplicate file paths.

	Yields:
	-------
	Tuple[str, str, str, str, str, str]
		Status updates and results after deletion.
	"""
	yield ("Deleting Duplicates", "Deleting duplicate files...", "<progress value='50' max='100'></progress>", "", "", getLogContent())
	result = fileManager.deleteDuplicates(duplicates)
	summary = (
		f"<p><b>Deleted Files:</b> {result.get('deletedCount', 0)} files.<br>"
		f"Total space freed: {result.get('totalSpaceFreed', 0) / (1024 * 1024):.2f} MB.</p>"
	)
	stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
	advReport = _generateAdvancedReport(finder, duplicates)
	yield (
		"Deletion Completed",
		summary,
		"<progress value='100' max='100'></progress>",
		stats,
		advReport,
		getLogContent()
	)

def _simulateDeletion(
	fileManager: FileManager,
	finder: DuplicateFinder,
	duplicates: List[Tuple[str, str]]
) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
	"""
	Simulates the deletion of duplicate files.

	Parameters:
	-----------
	fileManager : FileManager
		An instance of FileManager.
	finder : DuplicateFinder
		An instance of DuplicateFinder.
	duplicates : List[Tuple[str, str]]
		List of duplicate file paths.

	Yields:
	-------
	Tuple[str, str, str, str, str, str]
		Status updates and results after simulation.
	"""
	yield ("Simulating Deletion", "Simulating deletion of duplicate files...", "<progress value='50' max='100'></progress>", "", "", getLogContent())
	result = fileManager.deleteDuplicates(duplicates, simulate=True)
	summary = (
		f"<p><b>Simulated Deletion:</b> {result.get('simulatedDeletedCount', 0)} files.<br>"
		f"Total space that would be freed: {result.get('totalSpaceFreed', 0) / (1024 * 1024):.2f} MB.</p>"
	)
	stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
	advReport = _generateAdvancedReport(finder, duplicates)
	yield (
		"Simulation Completed",
		summary,
		"<progress value='100' max='100'></progress>",
		stats,
		advReport,
		getLogContent()
	)

def _moveDuplicates(
	fileManager: FileManager,
	finder: DuplicateFinder,
	duplicates: List[Tuple[str, str]],
	targetFolder: str
) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
	"""
	Moves duplicate files to a specified target folder.

	Parameters:
	-----------
	fileManager : FileManager
		An instance of FileManager.
	finder : DuplicateFinder
		An instance of DuplicateFinder.
	duplicates : List[Tuple[str, str]]
		List of duplicate file paths.
	targetFolder : str
		Destination folder for moving duplicates.

	Yields:
	-------
	Tuple[str, str, str, str, str, str]
		Status updates and results after moving files.
	"""
	yield ("Moving Duplicates", f"Moving duplicate files to '{targetFolder}'...", "<progress value='50' max='100'></progress>", "", "", getLogContent())
	result = fileManager.moveDuplicates(duplicates, targetFolder)
	if (error := result.get("error")):
		yield (
			"Error",
			error,
			"<progress value='0' max='100'></progress>",
			"",
			"",
			getLogContent()
		)
	else:
		summary = f"<p><b>Moved Files:</b> {result.get('movedCount', 0)} files have been moved to '{targetFolder}'.</p>"
		stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
		advReport = _generateAdvancedReport(finder, duplicates)
		yield (
			"Move Completed",
			summary,
			"<progress value='100' max='100'></progress>",
			stats,
			advReport,
			getLogContent()
		)

def _generateAdvancedReport(finder: DuplicateFinder, duplicates: List[Tuple[str, str]]) -> str:
	"""
	Generates an advanced report HTML based on the duplicates found.

	Parameters:
	-----------
	finder : DuplicateFinder
		An instance of DuplicateFinder.
	duplicates : List[Tuple[str, str]]
		List of duplicate file paths.

	Returns:
	--------
	str
		HTML content of the advanced report.
	"""
	duplicateCount: int = len(duplicates)
	totalDuplicateSpace: int = 0
	sizesMb: List[float] = []

	for dup, _ in duplicates:
		try:
			size = os.path.getsize(dup)
			sizesMb.append(size / (1024 * 1024))
			totalDuplicateSpace += size
		except Exception as e:
			logger.error(f"Error obtaining size for file '{dup}': {e}")

	plt.figure(figsize=(6, 4))
	if sizesMb:
		plt.hist(sizesMb, bins=10, edgecolor='black')
		plt.xlabel("Duplicate File Size (MB)")
		plt.ylabel("Count")
		plt.title("Distribution of Duplicate File Sizes")
	else:
		plt.text(0.5, 0.5, "No duplicates found to visualise.", ha='center', va='center')

	buf = BytesIO()
	plt.tight_layout()
	plt.savefig(buf, format='png')
	plt.close()
	buf.seek(0)
	imgBase64 = base64.b64encode(buf.read()).decode("utf-8")
	imgHtml = f"<img src='data:image/png;base64,{imgBase64}'/>"

	initialStats = finder.getInitialStats()
	advancedReport = (
		f"<h3>Advanced Report</h3>"
		f"<p>Total Files Scanned: {initialStats.get('totalFiles', 0)}</p>"
		f"<p>Total Subfolders: {initialStats.get('totalSubfolders', 0)}</p>"
		f"<p>Files with Unique Size: {initialStats.get('uniqueSizeFiles', 0)}</p>"
		f"<p>Duplicates Found: {duplicateCount}</p>"
		f"<p>Total Space Occupied by Duplicates: {totalDuplicateSpace / (1024 * 1024):.2f} MB</p>"
		f"<h4>Duplicate File Size Distribution</h4>"
		f"{imgHtml}"
	)
	return advancedReport

def getLogContent() -> str:
	"""
	Retrieves the current content of the log file.

	Returns:
	--------
	str
		Content of the log file or an error message if reading fails.
	"""
	try:
		with open("duplicate_finder.log", "r", encoding="utf-8") as f:
			return f.read().replace('\n', '<br>')  # Replace newlines for HTML display
	except Exception as e:
		return f"Error reading log file: {e}"

# -----------------------------------------------------------------------------
# End of processing.py
# -----------------------------------------------------------------------------