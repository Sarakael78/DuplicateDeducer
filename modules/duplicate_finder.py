# -----------------------------------------------------------------------------
# duplicate_finder.py
# -----------------------------------------------------------------------------

import os
import pickle
import time
import xxhash
import csv
from collections import defaultdict
from typing import List, Tuple, Dict, Generator, Callable, Optional
from modules.logger_config import logger

class DuplicateFinder:
	"""
	Scans directories recursively to identify duplicate files based on their content
	using a two-step hashing approach for efficiency.

	Attributes:
	-----------
	rootFolder : str
		Absolute path of the folder to scan.
	fileExtension : Optional[str]
		Optional filter to scan only files with the specified extension.
	minSize : int
		Minimum file size in bytes to be considered for scanning.
	cacheFile : str
		Path to the hash cache file.
	hashCache : Dict[str, Tuple[float, str]]
		Dictionary storing file paths and their corresponding full hashes along with modification time.
	csvFile : str
		Path to the CSV file where duplicate information is saved.
	saveCsv : bool
		Flag indicating whether to save duplicate information to CSV.
	"""

	def __init__(self, rootFolder: str, fileExtension: Optional[str] = None, minSize: int = 0, saveCsv: bool = False) -> None:
		"""
		Initialises the DuplicateFinder with the specified parameters.

		Parameters:
		-----------
		rootFolder : str
			Folder path to scan.
		fileExtension : Optional[str], optional
			Optional file extension filter. Defaults to None.
		minSize : int, optional
			Minimum file size in bytes. Defaults to 0.
		saveCsv : bool, optional
			Flag indicating whether to save duplicate information to CSV. Defaults to False.
		"""
		self.rootFolder: str = os.path.abspath(os.path.expanduser(rootFolder))
		self.fileExtension: Optional[str] = fileExtension.strip() if fileExtension and fileExtension.strip() != "" else None
		self.minSize: int = minSize  # in bytes
		self.cacheFile: str = "hash_cache.pkl"
		self.hashCache: Dict[str, Tuple[float, str]] = self.loadHashCache()
		self.csvFile: str = "duplicates.csv"
		self.saveCsv: bool = saveCsv

	def __del__(self) -> None:
		"""
		Destructor to ensure that the hash cache is saved upon deletion of the instance.
		"""
		self.saveHashCache()
		logger.info("DuplicateFinder instance destroyed. Hash cache saved.")

	def loadHashCache(self) -> Dict[str, Tuple[float, str]]:
		"""
		Loads the hash cache from the cache file if it exists.

		Returns:
		--------
		Dict[str, Tuple[float, str]]
			Loaded hash cache or an empty dictionary if loading fails.
		"""
		if os.path.exists(self.cacheFile):
			try:
				logger.info("Loading hash cache.")
				with open(self.cacheFile, "rb") as f:
					cache = pickle.load(f)
				logger.info("Hash cache loaded successfully.")
				return cache
			except Exception as e:
				logger.error(f"Error loading hash cache: {e}")
		return {}

	def saveHashCache(self) -> None:
		"""
		Saves the current hash cache to the cache file.
		"""
		try:
			with open(self.cacheFile, "wb") as f:
				pickle.dump(self.hashCache, f)
			logger.info("Hash cache saved.")
		except Exception as e:
			logger.error(f"Error saving hash cache: {e}")

	def calculateQuickHash(self, filePath: str, sampleSize: int = 4096) -> Optional[str]:
		"""
		Calculates a quick hash of the first few kilobytes of the file.

		Parameters:
		-----------
		filePath : str
			Path to the file.
		sampleSize : int, optional
			Number of bytes to read for the quick hash. Defaults to 4096.

		Returns:
		--------
		Optional[str]
			The calculated quick hash as a hexadecimal string.
			Returns None if an error occurs.
		"""
		try:
			with open(filePath, "rb") as f:
				sample = f.read(sampleSize)
		except FileNotFoundError:
			logger.error(f"File not found: '{filePath}'. Skipping quick hash.")
			return None
		except PermissionError:
			logger.error(f"Permission denied: '{filePath}'. Skipping quick hash.")
			return None
		except Exception as e:
			logger.error(f"Unexpected error reading file '{filePath}' for quick hash: {e}")
			return None

		hasher = xxhash.xxh64()
		hasher.update(sample)
		return hasher.hexdigest()

	def calculateFullHash(self, filePath: str, chunkSize: int = 65536) -> Optional[str]:
		"""
		Calculates the full hash of the file by reading it in chunks.

		Utilises caching to avoid recalculating hashes for unchanged files.

		Parameters:
		-----------
		filePath : str
			Path to the file.
		chunkSize : int, optional
			Size of each chunk to read from the file. Defaults to 65536.

		Returns:
		--------
		Optional[str]
			The calculated full hash as a hexadecimal string.
			Returns None if an error occurs.
		"""
		try:
			modTime = os.path.getmtime(filePath)
		except Exception as e:
			logger.error(f"Error getting modification time for file '{filePath}': {e}")
			return None

		if filePath in self.hashCache:
			cachedModTime, cachedHash = self.hashCache[filePath]
			if cachedModTime == modTime:
				return cachedHash

		hasher = xxhash.xxh64()
		try:
			with open(filePath, "rb") as f:
				while (chunk := f.read(chunkSize)):
					hasher.update(chunk)
		except FileNotFoundError:
			logger.error(f"File not found: '{filePath}'. Skipping full hash.")
			return None
		except PermissionError:
			logger.error(f"Permission denied: '{filePath}'. Skipping full hash.")
			return None
		except Exception as e:
			logger.error(f"Unexpected error reading file '{filePath}' for full hash: {e}")
			return None

		fileHash = hasher.hexdigest()
		self.hashCache[filePath] = (modTime, fileHash)
		return fileHash

	def groupFilesBySize(self) -> Dict[int, List[str]]:
		"""
		Groups files in the root folder by their size.

		Returns:
		--------
		Dict[int, List[str]]
			A dictionary where keys are file sizes and values are lists of file paths.
		"""
		sizeDict: Dict[int, List[str]] = {}
		for dirpath, _, filenames in os.walk(self.rootFolder):
			for filename in filenames:
				if self.fileExtension and not filename.endswith(self.fileExtension):
					continue
				filePath = os.path.join(dirpath, filename)
				try:
					size = os.path.getsize(filePath)
					if self.minSize and size < self.minSize:
						continue
				except Exception as e:
					logger.error(f"Error getting size for file '{filePath}': {e}")
					continue
				sizeDict.setdefault(size, []).append(filePath)
		return sizeDict

	def getInitialStats(self) -> Dict[str, int]:
		"""
		Gathers initial statistics about the files and folders in the root directory.

		Returns:
		--------
		Dict[str, int]
			A dictionary containing total files, total subfolders, and files with unique sizes.
		"""
		totalFiles = 0
		totalSubfolders = 0
		for _, dirnames, filenames in os.walk(self.rootFolder):
			totalSubfolders += len(dirnames)
			totalFiles += len(filenames)
		uniqueSizeFiles = 0
		sizeDict = self.groupFilesBySize()
		for files in sizeDict.values():
			if len(files) == 1:
				uniqueSizeFiles += 1
		return {"totalFiles": totalFiles, "totalSubfolders": totalSubfolders, "uniqueSizeFiles": uniqueSizeFiles}

	def _appendDuplicateCsv(self, duplicateFile: str, originalFile: str) -> None:
		"""
		Appends information about a duplicate file to the CSV file.

		Parameters:
		-----------
		duplicateFile : str
			Path to the duplicate file.
		originalFile : str
			Path to the original file.
		"""
		header = ['timestamp', 'duplicate_file', 'original_file']
		fileExists = os.path.exists(self.csvFile)
		try:
			with open(self.csvFile, 'a', newline='', encoding='utf-8') as csvfile:
				writer = csv.writer(csvfile)
				if not fileExists:
					writer.writerow(header)
				writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), duplicateFile, originalFile])
		except Exception as e:
			logger.error(f"Error writing to CSV file '{self.csvFile}': {e}")

	def findDuplicates(self) -> List[Tuple[str, str]]:
		"""
		Identifies duplicate files by comparing their hashes.

		Returns:
		--------
		List[Tuple[str, str]]
			A list of tuples where each tuple contains the path to a duplicate file and its original.
		"""
		sizeDict = self.groupFilesBySize()
		duplicates: List[Tuple[str, str]] = []
		logger.info(f"Starting full scan in folder: {self.rootFolder}")

		for size, files in sizeDict.items():
			if len(files) < 2:
				continue
			quickGroups: Dict[str, List[str]] = {}
			for filePath in files:
				quickHash = self.calculateQuickHash(filePath)
				if not quickHash:
					continue
				quickGroups.setdefault(quickHash, []).append(filePath)

			for quick, fileList in quickGroups.items():
				if len(fileList) < 2:
					continue
				fullHashes: Dict[str, str] = {}
				for filePath in fileList:
					fullHash = self.calculateFullHash(filePath)
					if not fullHash:
						continue
					if fullHash in fullHashes:
						orig = fullHashes[fullHash]
						# Determine original vs duplicate based on folder name comparison
						if os.path.dirname(filePath).lower() < os.path.dirname(orig).lower():
							original, duplicate = filePath, orig
							fullHashes[fullHash] = original
						else:
							original, duplicate = orig, filePath
						logger.info(f"Duplicate found: {duplicate} (duplicate) -> {original} (original)")
						duplicates.append((duplicate, original))
						if self.saveCsv:
							self._appendDuplicateCsv(duplicate, original)
					else:
						fullHashes[fullHash] = filePath
		self.saveHashCache()
		return duplicates

	def findDuplicatesStream(self, stopRequestedCallback: Callable[[], bool] = lambda: False) -> Generator[Tuple[str, str, str, str], None, None]:
		"""
		Generator that yields status updates while finding duplicates, allowing for real‐time progress tracking.

		Parameters:
		-----------
		stopRequestedCallback : Callable[[], bool], optional
			A callback function that returns True if a stop has been requested. Defaults to a no‐op.

		Yields:
		-------
		Tuple[str, str, str, str]
			A tuple containing a status message, accumulated duplicate HTML, progress HTML, and statistics info.
		"""
		# Step 1: Group files by size and remove files with unique sizes.
		sizeDict = self.groupFilesBySize()
		candidateFiles: List[str] = []
		for files in sizeDict.values():
			if len(files) > 1:
				candidateFiles.extend(files)

		# Get initial statistics.
		initialStats = self.getInitialStats()
		totalCandidateFiles = len(candidateFiles)
		startTime = time.time()
		progressHtml = (
			f"<progress value='0' max='100'></progress>"
			f"<p>Processed 0 / {totalCandidateFiles} files.<br>Elapsed Time: 00:00:00, ETA: Calculating...</p>"
		)
		statsInfo = (
			f"<p>Total Files in Folder: {initialStats['totalFiles']}<br>"
			f"Total Subfolders: {initialStats['totalSubfolders']}<br>"
			f"Files with Unique Size: {initialStats['uniqueSizeFiles']}<br>"
			f"Duplicates Found: 0</p>"
		)
		initMessage = (
			f"<p>Initialisation: {initialStats['totalFiles']} total files found. "
			f"{totalCandidateFiles} candidate files for duplicate analysis (unique files excluded).</p>"
		)
		yield ("Initialisation", initMessage, progressHtml, statsInfo)

		# Step 2: Begin scanning hashes.
		yield ("Scanning Hashes", f"<p>Scanning {totalCandidateFiles} candidate files for duplicates...</p>", progressHtml, statsInfo)

		processedFiles = 0
		totalDuplicates = 0
		accumulatedHtml = ""
		quickGroupsStream: Dict[str, List[Dict[str, Optional[str]]]] = defaultdict(list)

		for filePath in candidateFiles:
			if stopRequestedCallback():
				progressHtml = self._buildProgressHtml(processedFiles, totalCandidateFiles, startTime)
				yield (
					"Stopped",
					accumulatedHtml + f"<p>Scan stopped by user after processing {processedFiles} files.</p>",
					progressHtml,
					statsInfo
				)
				self.saveHashCache()
				return

			quickHash = self.calculateQuickHash(filePath)
			if not quickHash:
				processedFiles += 1
				progressHtml = self._buildProgressHtml(processedFiles, totalCandidateFiles, startTime)
				yield ("Scanning Hashes", accumulatedHtml, progressHtml, statsInfo)
				continue

			duplicateFound = False
			for candidate in quickGroupsStream[quickHash]:
				if candidate["full"] is None:
					candidate["full"] = self.calculateFullHash(candidate["path"])
				currentFull = self.calculateFullHash(filePath)
				if currentFull == candidate["full"]:
					orig = candidate["path"]
					# Determine original vs duplicate based on folder name comparison
					if os.path.dirname(filePath).lower() < os.path.dirname(orig).lower():
						original, duplicate = filePath, orig
						candidate["path"] = original  # update candidate to new original
					else:
						original, duplicate = orig, filePath
					duplicateHtml = (
						f"<p><b>Duplicate Found:</b><br>"
						f"Duplicate: <a href='file://{duplicate}' target='_blank'>{duplicate}</a><br>"
						f"Original: <a href='file://{original}' target='_blank'>{original}</a></p>"
					)
					accumulatedHtml += duplicateHtml
					logger.info(f"Streaming duplicate: {duplicate} duplicates {original}")
					totalDuplicates += 1
					if self.saveCsv:
						self._appendDuplicateCsv(duplicate, original)
					duplicateFound = True
					break

			if not duplicateFound:
				quickGroupsStream[quickHash].append({"path": filePath, "full": None})

			processedFiles += 1
			progressHtml = self._buildProgressHtml(processedFiles, totalCandidateFiles, startTime)
			statsInfo = (
				f"<p>Total Files in Folder: {initialStats['totalFiles']}<br>"
				f"Total Subfolders: {initialStats['totalSubfolders']}<br>"
				f"Files with Unique Size: {initialStats['uniqueSizeFiles']}<br>"
				f"Duplicates Found: {totalDuplicates}</p>"
			)
			yield ("Scanning Hashes", accumulatedHtml, progressHtml, statsInfo)

			if processedFiles % 500 == 0:
				self.saveHashCache()

		# Step 3: Finalisation.
		finalSummary = f"<p><b>Finalisation:</b> Total Duplicates Found: {totalDuplicates}</p>"
		accumulatedHtml += finalSummary
		finalProgress = (
			f"<progress value='100' max='100'></progress>"
			f"<p>Processed {totalCandidateFiles} / {totalCandidateFiles} files.<br>"
			f"Elapsed Time: {time.strftime('%H:%M:%S', time.gmtime(time.time()-startTime))}, ETA: 00:00:00</p>"
		)
		statsInfo = (
			f"<p>Total Files in Folder: {initialStats['totalFiles']}<br>"
			f"Total Subfolders: {initialStats['totalSubfolders']}<br>"
			f"Files with Unique Size: {initialStats['uniqueSizeFiles']}<br>"
			f"Duplicates Found: {totalDuplicates}</p>"
		)
		yield ("Finalisation", accumulatedHtml, finalProgress, statsInfo)
		self.saveHashCache()

	def _buildProgressHtml(self, processedFiles: int, totalFiles: int, startTime: float) -> str:
		"""
		Builds the HTML string for displaying progress.

		Parameters:
		-----------
		processedFiles : int
			Number of files processed so far.
		totalFiles : int
			Total number of files to process.
		startTime : float
			Timestamp when the processing started.

		Returns:
		--------
		str
			HTML string representing the progress bar and time metrics.
		"""
		elapsedTime = time.time() - startTime
		estimatedRemaining = (elapsedTime / processedFiles) * (totalFiles - processedFiles) if processedFiles > 0 else 0
		progressPercent = int((processedFiles / totalFiles) * 100) if totalFiles > 0 else 100
		elapsedFormatted = time.strftime("%H:%M:%S", time.gmtime(elapsedTime))
		etaFormatted = time.strftime("%H:%M:%S", time.gmtime(estimatedRemaining)) if processedFiles > 0 else "Calculating..."
		return (
			f"<progress value='{progressPercent}' max='100'></progress>"
			f"<p>Processed {processedFiles} / {totalFiles} files.<br>"
			f"Elapsed Time: {elapsedFormatted}, ETA: {etaFormatted}</p>"
		)