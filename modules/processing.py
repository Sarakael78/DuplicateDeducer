# -----------------------------------------------------------------------------
# processing.py
# -----------------------------------------------------------------------------

import os
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from typing import Generator, Tuple
from modules.duplicate_finder import DuplicateFinder
from modules.file_manager import FileManager
from modules.logger_config import logger

# Global flag to control the stopping of a scan
STOP_REQUESTED = False

def get_stop_requested():
    """
    Returns the current value of the global STOP_REQUESTED flag.
    """
    global STOP_REQUESTED
    return STOP_REQUESTED

def stop_scan() -> str:
    """
    Sets the global stop flag to signal an early termination of the scan.

    Returns
    -------
    str
        Confirmation message indicating that a stop has been requested.
    """
    global STOP_REQUESTED
    STOP_REQUESTED = True
    logger.info("Stop scan requested by user.")
    return "Stop requested."

def process_action(
    folders_input: str,
    file_extension: str,
    min_size: float,
    action: str,
    target_folder: str = "",
    save_csv: bool = False,
    stop_flag: bool = False
) -> Generator[Tuple[str, str, str, str, str], None, None]:
    """
    Processes user actions from the Gradio UI, such as finding, deleting, simulating deletion,
    moving duplicates, or generating advanced reports.

    Parameters
    ----------
    folders_input : str
        Folder path(s) to scan. Can be a single path or multiple paths provided one per line.
    file_extension : str
        Optional file extension filter (e.g., .txt, .jpg).
    min_size : float
        Minimum file size in MB to be considered for scanning.
    action : str
        The action to perform (e.g., "Find Duplicates", "Delete Duplicates").
    target_folder : str, optional
        Destination folder for moving duplicates. Required if action is "Move Duplicates".
    save_csv : bool, optional
        Flag indicating whether to save duplicate information as a CSV file.
    stop_flag : bool, optional
        Flag indicating whether to stop the scan.

    Yields
    ------
    tuple
        A tuple containing status message, main output HTML, progress HTML, scan statistics,
        and advanced report HTML. For non-Advanced Report actions, the advanced report will be an
        empty string. For the Advanced Report action, main output will be empty.
    """
    global STOP_REQUESTED
    STOP_REQUESTED = False  # Reset stop flag at start.

    if STOP_REQUESTED:
        STOP_REQUESTED = False
        yield ("Scan cancelled", "", "<progress value='0' max='100'></progress>", "", "")
        return

    # Convert minimum size from MB to bytes.
    min_size_bytes = int(min_size * 1024 * 1024) if min_size > 0 else 0

    # Handle the Advanced Report action separately
    if action == "Advanced Report":
        yield from _process_advanced_report(folders_input, file_extension, min_size_bytes)
    else:
        yield from _process_standard_actions(
            folders_input, file_extension, min_size_bytes, action, target_folder, save_csv
        )

def _process_advanced_report(
    folders_input: str,
    file_extension: str,
    min_size_bytes: int
) -> Generator[Tuple[str, str, str, str, str], None, None]:
    """
    Processes the Advanced Report action, allowing scanning of multiple directories.

    Parameters
    ----------
    folders_input : str
        Multiline string with one folder path per line.
    file_extension : str
        Optional file extension filter.
    min_size_bytes : int
        Minimum file size in bytes.

    Yields
    ------
    tuple
        Status updates and the final advanced report.
    """
    folder_list = [line.strip() for line in folders_input.splitlines() if line.strip()]
    if not folder_list:
        logger.error("No directories provided for advanced report.")
        yield (
            "Error",
            "No directories provided for advanced report.",
            "<progress value='0' max='100'></progress>",
            "",
            ""
        )
        return

    all_duplicates = []
    total_files_scanned = 0
    total_subfolders = 0
    total_unique_files = 0

    for folder in folder_list:
        if not os.path.exists(folder):
            msg = f"Directory '{folder}' does not exist."
            logger.error(msg)
            yield (
                "Error",
                msg,
                "<progress value='0' max='100'></progress>",
                "",
                ""
            )
            return
        try:
            finder = DuplicateFinder(folder, file_extension, min_size_bytes)
            stats = finder.get_initial_stats()
            total_files_scanned += stats.get("total_files", 0)
            total_subfolders += stats.get("total_subfolders", 0)
            total_unique_files += stats.get("unique_size_files", 0)
            duplicates = finder.find_duplicates()
            all_duplicates.extend(duplicates)
        except Exception as e:
            msg = f"Error scanning directory '{folder}': {str(e)}"
            logger.error(msg)
            yield (
                "Error",
                msg,
                "<progress value='0' max='100'></progress>",
                "",
                ""
            )
            return

    duplicate_count = len(all_duplicates)
    total_duplicate_space = 0
    sizes = []
    for dup, orig in all_duplicates:
        try:
            fsize = os.path.getsize(dup)
            total_duplicate_space += fsize
            sizes.append(fsize / (1024 * 1024))  # convert to MB
        except Exception as e:
            logger.error(f"Error obtaining size for file '{dup}': {str(e)}")

    potential_space_savings = total_duplicate_space

    plt.figure(figsize=(6, 4))
    if sizes:
        plt.hist(sizes, bins=10, edgecolor='black')
        plt.xlabel("Duplicate File Size (MB)")
        plt.ylabel("Count")
        plt.title("Distribution of Duplicate File Sizes")
    else:
        plt.text(0.5, 0.5, "No duplicates found to visualize.", ha='center', va='center')
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
        f"<p>Total Space Occupied by Duplicates: {total_duplicate_space / (1024 * 1024):.2f} MB</p>"
        f"<p>Potential Space Savings: {potential_space_savings / (1024 * 1024):.2f} MB</p>"
        f"<h4>Duplicate File Size Distribution</h4>"
        f"{img_html}"
    )
    yield (
        "Advanced Report Completed",
        "",
        "<progress value='100' max='100'></progress>",
        "",
        report_html
    )

def _process_standard_actions(
    folders_input: str,
    file_extension: str,
    min_size_bytes: int,
    action: str,
    target_folder: str,
    save_csv: bool
) -> Generator[Tuple[str, str, str, str, str], None, None]:
    """
    Processes standard actions: Find Duplicates, Delete Duplicates, Simulate Deletion, Move Duplicates.

    Parameters
    ----------
    folders_input : str
        Folder path(s) to scan.
    file_extension : str
        Optional file extension filter.
    min_size_bytes : int
        Minimum file size in bytes.
    action : str
        The action to perform.
    target_folder : str
        Destination folder for moving duplicates.
    save_csv : bool
        Flag indicating whether to save duplicate information as a CSV file.

    Yields
    ------
    tuple
        Status updates and results based on the selected action.
    """
    folder = folders_input.strip()
    if not os.path.exists(folder):
        logger.error("Specified folder does not exist.")
        yield (
            "Error",
            "The specified folder does not exist.",
            "<progress value='0' max='100'></progress>",
            "",
            ""
        )
        return

    finder = DuplicateFinder(folder, file_extension, min_size_bytes)
    finder.save_csv = save_csv  # Set CSV saving flag based on user selection

    if action == "Find Duplicates":
        # Stream duplicates as they are found.
        for status, html, progress, stats_info in finder.find_duplicates_stream(get_stop_requested):
            yield (status, html, progress, stats_info, "")
        STOP_REQUESTED = False

    elif action in ["Delete Duplicates", "Simulate Deletion", "Move Duplicates"]:
        # Yield an initial status update for scanning.
        yield ("Scanning for Duplicates", "Scanning the folder for duplicates...", "<progress value='0' max='100'></progress>", "", "")
        try:
            duplicates = finder.find_duplicates()
        except Exception as e:
            msg = f"Error during duplicate search: {str(e)}"
            logger.error(msg)
            yield (
                "Error",
                msg,
                "<progress value='0' max='100'></progress>",
                "",
                ""
            )
            return

        if not duplicates:
            yield (
                "Result",
                "No duplicate files found.",
                "<progress value='100' max='100'></progress>",
                "",
                ""
            )
            return

        if action == "Delete Duplicates":
            yield ("Deleting Duplicates", "Deleting duplicate files...", "<progress value='50' max='100'></progress>", "", "")
            result = FileManager.delete_duplicates(duplicates)
            summary = (
                f"<p><b>Deleted Files:</b> {result['deleted_count']} files.<br>"
                f"Total space freed: {result['total_space_freed'] / (1024 * 1024):.2f} MB.</p>"
            )
            stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
            yield (
                "Deletion Completed",
                summary,
                "<progress value='100' max='100'></progress>",
                stats,
                ""
            )

        elif action == "Simulate Deletion":
            yield ("Simulating Deletion", "Simulating deletion of duplicate files...", "<progress value='50' max='100'></progress>", "", "")
            result = FileManager.delete_duplicates(duplicates, simulate=True)
            summary = (
                f"<p><b>Simulated Deletion:</b> {result['simulated_deleted_count']} files.<br>"
                f"Total space that would be freed: {result['total_space_freed'] / (1024 * 1024):.2f} MB.</p>"
            )
            stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
            yield (
                "Simulation Completed",
                summary,
                "<progress value='100' max='100'></progress>",
                stats,
                ""
            )

        elif action == "Move Duplicates":
            if not target_folder.strip():
                yield (
                    "Error",
                    "Target folder must be specified for moving duplicates.",
                    "<progress value='0' max='100'></progress>",
                    "",
                    ""
                )
                return
            yield ("Moving Duplicates", f"Moving duplicate files to '{target_folder}'...", "<progress value='50' max='100'></progress>", "", "")
            result = FileManager.move_duplicates(duplicates, target_folder)
            if "error" in result:
                yield (
                    "Error",
                    result["error"],
                    "<progress value='0' max='100'></progress>",
                    "",
                    ""
                )
            else:
                summary = f"<p><b>Moved Files:</b> {result['moved_count']} files have been moved to '{target_folder}'.</p>"
                stats = f"<p>Duplicates Processed: {len(duplicates)}</p>"
                yield (
                    "Move Completed",
                    summary,
                    "<progress value='100' max='100'></progress>",
                    stats,
                    ""
                )
    else:
        logger.error("Invalid action selected.")
        yield (
            "Error",
            "Invalid action selected.",
            "<progress value='0' max='100'></progress>",
            "",
            ""
        )

# -----------------------------------------------------------------------------
# End of processing.py
# -----------------------------------------------------------------------------