# -----------------------------------------------------------------------------
# file_manager.py
# -----------------------------------------------------------------------------

import os
import shutil
from modules.logger_config import logger


class FileManager:
    """
    Provides methods for managing duplicate files, including deletion, simulated deletion,
    and moving duplicates to a specified target folder.

    Methods
    -------
    delete_duplicates(duplicates: list, simulate: bool = False) -> dict
        Deletes or simulates deletion of duplicate files.
    
    move_duplicates(duplicates: list, target_folder: str) -> dict
        Moves duplicate files to the specified target folder.
    """

    @staticmethod
    def delete_duplicates(duplicates: list, simulate: bool = False) -> dict:
        """
        Deletes duplicate files or simulates their deletion based on the `simulate` flag.

        Parameters
        ----------
        duplicates : list
            A list of tuples where each tuple contains the path to a duplicate file and its original.
        simulate : bool, optional
            If True, simulates deletion without actually removing files. Default is False.

        Returns
        -------
        dict
            A dictionary containing counts of deleted or simulated deletions, total space freed,
            and a list of deleted files.
        """
        total_deleted = 0
        total_freed = 0
        deleted_files = []
        for dup, _ in duplicates:
            try:
                size = os.path.getsize(dup)
                total_freed += size
                if not simulate:
                    os.remove(dup)
                    total_deleted += 1
                    deleted_files.append(dup)
                    logger.info(f"Deleted file: {dup}")
                else:
                    logger.info(f"Simulated deletion for file: {dup}")
            except Exception as e:
                logger.error(f"Error deleting file '{dup}': {e}")
        return {
            "deleted_count": total_deleted if not simulate else 0,
            "simulated_deleted_count": len(duplicates) if simulate else 0,
            "total_space_freed": total_freed,
            "deleted_files": deleted_files,
        }

    @staticmethod
    def move_duplicates(duplicates: list, target_folder: str) -> dict:
        """
        Moves duplicate files to the specified target folder.

        Parameters
        ----------
        duplicates : list
            A list of tuples where each tuple contains the path to a duplicate file and its original.
        target_folder : str
            The destination folder where duplicates will be moved.

        Returns
        -------
        dict
            A dictionary containing the count of moved files and a list of their new paths.
            If an error occurs while creating the target folder, an error message is returned.
        """
        moved_files = []
        if not os.path.exists(target_folder):
            try:
                os.makedirs(target_folder)
                logger.info(f"Created target folder: {target_folder}")
            except Exception as e:
                logger.error(f"Error creating target folder '{target_folder}': {e}")
                return {"error": f"Error creating target folder '{target_folder}': {e}"}
        for dup, _ in duplicates:
            try:
                filename = os.path.basename(dup)
                dest_path = os.path.join(target_folder, filename)
                shutil.move(dup, dest_path)
                moved_files.append(dest_path)
                logger.info(f"Moved file '{dup}' to '{dest_path}'")
            except Exception as e:
                logger.error(f"Error moving file '{dup}': {e}")
        return {"moved_count": len(moved_files), "moved_files": moved_files}