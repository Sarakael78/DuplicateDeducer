# -----------------------------------------------------------------------------
# Duplicate_finder.py
# -----------------------------------------------------------------------------

import os
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from modules.duplicate_finder import DuplicateFinder
from modules.file_manager import FileManager
from modules.logger_config import logger

STOP_REQUESTED = False

def stop_scan():
    """
    Sets the global stop flag to signal an early termination of the scan.
    """
    global STOP_REQUESTED
    STOP_REQUESTED = True
    return "Stop requested."

def process_action(folders_input: str, file_extension: str, min_size: float, action: str, target_folder: str = "", save_csv: bool = False):
    """
    Process the user actions from the Gradio UI.
    
    Args:
        folders_input (str): Folder path(s) to scan. This can be a single folder path or multiple 
                             folder paths provided one per line.
        file_extension (str): Optional file extension filter.
        min_size (float): Minimum file size in MB.
        action (str): Selected action.
        target_folder (str): Destination folder for moving duplicates.
        save_csv (bool): Flag indicating whether to save duplicate info as CSV.
        
    Yields:
        tuple: (status, main_output, progress_html, stat_details, advanced_report)
               For non‐Advanced Report actions, advanced_report will be an empty string.
               For the Advanced Report action, main_output will be empty.
    """
    global STOP_REQUESTED
    STOP_REQUESTED = False  # Reset stop flag at start.
    
    # Convert minimum size from MB to bytes.
    min_size_bytes = int(min_size * 1024 * 1024) if min_size > 0 else 0
    
    # If the action is Advanced Report, allow scanning of multiple directories.
    if action == "Advanced Report":
        # Parse the multiline folder input (one folder per line).
        folder_list = [line.strip() for line in folders_input.splitlines() if line.strip()]
        if not folder_list:
            logger.error("No directories provided for advanced report.")
            yield ("Error", "No directories provided for advanced report.", "<progress value='0' max='100'></progress>", "", "")
            return
        
        all_duplicates = []
        total_files_scanned = 0
        total_subfolders = 0
        total_unique_files = 0
        
        for folder in folder_list:
            if not os.path.exists(folder):
                msg = f"Directory '{folder}' does not exist."
                logger.error(msg)
                yield ("Error", msg, "<progress value='0' max='100'></progress>", "", "")
                return
            try:
                finder = DuplicateFinder(folder, file_extension, min_size_bytes)
                # Use get_initial_stats (if implemented) to collect counts.
                if hasattr(finder, 'get_initial_stats'):
                    stats = finder.get_initial_stats()
                    total_files_scanned += stats.get("total_files", 0)
                    total_subfolders += stats.get("total_subfolders", 0)
                    total_unique_files += stats.get("unique_size_files", 0)
                duplicates = finder.find_duplicates()
                all_duplicates.extend(duplicates)
            except Exception as e:
                msg = f"Error scanning directory '{folder}': {str(e)}"
                logger.error(msg)
                yield ("Error", msg, "<progress value='0' max='100'></progress>", "", "")
                return
        
        duplicate_count = len(all_duplicates)
        total_duplicate_space = 0
        sizes = []
        for dup, orig in all_duplicates:
            try:
                fsize = os.path.getsize(dup)
                total_duplicate_space += fsize
                sizes.append(fsize / (1024*1024))  # convert to MB
            except Exception as e:
                logger.error(f"Error obtaining size for file '{dup}': {str(e)}")
        
        potential_space_savings = total_duplicate_space  # Assuming removal of duplicates saves this space.
        
        # Generate a histogram visualization of duplicate file sizes.
        plt.figure(figsize=(6,4))
        if sizes:
            plt.hist(sizes, bins=10, edgecolor='black')
            plt.xlabel("Duplicate File Size (MB)")
            plt.ylabel("Count")
            plt.title("Distribution of Duplicate File Sizes")
        else:
            plt.text(0.5, 0.5, "No duplicates found to visualize.", horizontalalignment='center', verticalalignment='center')
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        img_html = f"<img src='data:image/png;base64,{img_base64}'/>"
        
        report_html = (
            f"<h3>Advanced Report</h3>"
            f"<p>Total Directories Scanned: {len(folder_list)}</p>"
            f"<p>Total Files Scanned: {total_files_scanned}</p>"
            f"<p>Total Subfolders: {total_subfolders}</p>"
            f"<p>Files with Unique Size: {total_unique_files}</p>"
            f"<p>Duplicates Found: {duplicate_count}</p>"
            f"<p>Total Space Occupied by Duplicates: {total_duplicate_space/(1024*1024):.2f} MB</p>"
            f"<p>Potential Space Savings: {potential_space_savings/(1024*1024):.2f} MB</p>"
            f"<h4>Duplicate File Size Distribution</h4>"
            f"{img_html}"
        )
        yield ("Advanced Report Completed", "", "<progress value='100' max='100'></progress>", "", report_html)
    
    else:
        # For other actions, treat the folder input as a single directory.
        folder = folders_input.strip()
        if not os.path.exists(folder):
            logger.error("Specified folder does not exist.")
            yield ("Error", "The specified folder does not exist.", "<progress value='0' max='100'></progress>", "", "")
            return
        
        finder = DuplicateFinder(folder, file_extension, min_size_bytes)
        finder.save_csv = save_csv  # Set CSV saving flag based on user selection.
        
        if action == "Find Duplicates":
            for status, html, progress, stats_info in finder.find_duplicates_stream(lambda: STOP_REQUESTED):
                yield (status, html, progress, stats_info, "")
            STOP_REQUESTED = False
        elif action in ["Delete Duplicates", "Simulate Deletion", "Move Duplicates"]:
            try:
                duplicates = finder.find_duplicates()
            except Exception as e:
                msg = f"Error during duplicate search: {str(e)}"
                logger.error(msg)
                yield ("Error", msg, "<progress value='0' max='100'></progress>", "", "")
                return
            
            if not duplicates:
                yield ("Result", "No duplicate files found.", "<progress value='100' max='100'></progress>", "", "")
                return
    
            if action == "Delete Duplicates":
                result = FileManager.delete_duplicates(duplicates)
                summary = (
                    f"<p><b>Deleted Files:</b> {result['deleted_count']} files.<br>"
                    f"Total space freed: {result['total_space_freed']/(1024*1024):.2f} MB.</p>"
                )
                stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
                yield ("Deletion Completed", summary, "<progress value='100' max='100'></progress>", stats, "")
            elif action == "Simulate Deletion":
                result = FileManager.delete_duplicates(duplicates, simulate=True)
                summary = (
                    f"<p><b>Simulated Deletion:</b> {result['simulated_deleted_count']} files.<br>"
                    f"Total space that would be freed: {result['total_space_freed']/(1024*1024):.2f} MB.</p>"
                )
                stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
                yield ("Simulation Completed", summary, "<progress value='100' max='100'></progress>", stats, "")
            elif action == "Move Duplicates":
                if not target_folder.strip():
                    yield ("Error", "Target folder must be specified for moving duplicates.", "<progress value='0' max='100'></progress>", "", "")
                    return
                result = FileManager.move_duplicates(duplicates, target_folder)
                if "error" in result:
                    yield ("Error", result["error"], "<progress value='0' max='100'></progress>", "", "")
                else:
                    summary = f"<p><b>Moved Files:</b> {result['moved_count']} files have been moved to '{target_folder}'.</p>"
                    stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
                    yield ("Move Completed", summary, "<progress value='100' max='100'></progress>", stats, "")
        else:
            logger.error("Invalid action selected.")
            yield ("Error", "Invalid action selected.", "<progress value='0' max='100'></progress>", "", "")