# -----------------------------------------------------------------------------
# file_manager.py
# -----------------------------------------------------------------------------


import os
import shutil
from modules.logger_config import logger

class FileManager:
    """
    Methods for managing duplicate files – deletion, simulated deletion, or moving them.
    """
    @staticmethod
    def delete_duplicates(duplicates: list, simulate: bool = False) -> dict:
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