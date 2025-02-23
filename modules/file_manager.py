# -----------------------------------------------------------------------------
# file_manager.py
# -----------------------------------------------------------------------------

import os
import shutil
from typing import List, Tuple, Dict
from modules.logger_config import logger

class FileManager:
	"""
	Provides methods for managing duplicate files, including deletion, simulated deletion,
	and moving duplicates to a specified target folder.

	Methods:
	---------
	deleteDuplicates(duplicates: List[Tuple[str, str]], simulate: bool = False) -> Dict[str, object]
		Deletes or simulates deletion of duplicate files.
	
	moveDuplicates(duplicates: List[Tuple[str, str]], targetFolder: str) -> Dict[str, object]
		Moves duplicate files to the specified target folder.
	"""

	@staticmethod
	def deleteDuplicates(duplicates: List[Tuple[str, str]], simulate: bool = False) -> Dict[str, object]:
		"""
		Deletes duplicate files or simulates their deletion based on the `simulate` flag.

		Parameters:
		-----------
		duplicates : List[Tuple[str, str]]
			A list of tuples where each tuple contains the path to a duplicate file and its original.
		simulate : bool, optional
			If True, simulates deletion without actually removing files. Default is False.

		Returns:
		--------
		Dict[str, object]
			A dictionary containing counts of deleted or simulated deletions, total space freed,
			and a list of deleted files.
		"""
		totalDeleted: int = 0
		totalFreed: int = 0
		deletedFiles: List[str] = []
		for dup, _ in duplicates:
			try:
				size: int = os.path.getsize(dup)
				totalFreed += size
				if not simulate:
					os.remove(dup)
					totalDeleted += 1
					deletedFiles.append(dup)
					logger.info(f"Deleted file: {dup}")
				else:
					logger.info(f"Simulated deletion for file: {dup}")
			except Exception as e:
				logger.error(f"Error deleting file '{dup}': {e}")
		return {
			"deletedCount": totalDeleted if not simulate else 0,
			"simulatedDeletedCount": len(duplicates) if simulate else 0,
			"totalSpaceFreed": totalFreed,
			"deletedFiles": deletedFiles,
		}

	@staticmethod
	def moveDuplicates(duplicates: List[Tuple[str, str]], targetFolder: str) -> Dict[str, object]:
		"""
		Moves duplicate files to the specified target folder.

		Parameters:
		-----------
		duplicates : List[Tuple[str, str]]
			A list of tuples where each tuple contains the path to a duplicate file and its original.
		targetFolder : str
			The destination folder where duplicates will be moved.

		Returns:
		--------
		Dict[str, object]
			A dictionary containing the count of moved files and a list of their new paths.
			If an error occurs while creating the target folder, an error message is returned.
		"""
		movedFiles: List[str] = []
		if not os.path.exists(targetFolder):
			try:
				os.makedirs(targetFolder)
				logger.info(f"Created target folder: {targetFolder}")
			except Exception as e:
				logger.error(f"Error creating target folder '{targetFolder}': {e}")
				return {"error": f"Error creating target folder '{targetFolder}': {e}"}
		for dup, _ in duplicates:
			try:
				filename: str = os.path.basename(dup)
				destPath: str = os.path.join(targetFolder, filename)
				shutil.move(dup, destPath)
				movedFiles.append(destPath)
				logger.info(f"Moved file '{dup}' to '{destPath}'")
			except Exception as e:
				logger.error(f"Error moving file '{dup}': {e}")
		return {"movedCount": len(movedFiles), "movedFiles": movedFiles}
# -----------------------------------------------------------------------------
# End fileManager.py
# -----------------------------------------------------------------------------