# -----------------------------------------------------------------------------
# duplicate_finder.py
# -----------------------------------------------------------------------------

import os
import pickle
import time
import xxhash
import csv
from collections import defaultdict
from modules.logger_config import logger


class DuplicateFinder:
    """
    Scans directories recursively to identify duplicate files based on their content
    using a two-step hashing approach for efficiency.

    Attributes
    ----------
    root_folder : str
        Absolute path of the folder to scan.
    file_extension : str or None
        Optional filter to scan only files with the specified extension.
    min_size : int
        Minimum file size in bytes to be considered for scanning.
    cache_file : str
        Path to the hash cache file.
    hash_cache : dict
        Dictionary storing file paths and their corresponding full hashes.
    csv_file : str
        Path to the CSV file where duplicate information is saved.
    save_csv : bool
        Flag indicating whether to save duplicate information to CSV.
    """

    def __init__(self, root_folder: str, file_extension: str = None, min_size: int = 0) -> None:
        """
        Initializes the DuplicateFinder with the specified parameters.

        Parameters
        ----------
        root_folder : str
            Folder path to scan.
        file_extension : str, optional
            Optional file extension filter. Defaults to None.
        min_size : int, optional
            Minimum file size in bytes. Defaults to 0.
        """
        self.root_folder = os.path.abspath(os.path.expanduser(root_folder))
        self.file_extension = file_extension.strip() if file_extension and file_extension.strip() != "" else None
        self.min_size = min_size  # in bytes
        self.cache_file = "hash_cache.pkl"
        self.hash_cache = self.load_hash_cache()
        self.csv_file = "duplicates.csv"
        self.save_csv = False

    def load_hash_cache(self) -> dict:
        """
        Loads the hash cache from the cache file if it exists.

        Returns
        -------
        dict
            Loaded hash cache or an empty dictionary if loading fails.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    cache = pickle.load(f)
                    logger.info("Hash cache loaded successfully.")
                    return cache
            except Exception as e:
                logger.error(f"Error loading hash cache: {e}")
        return {}

    def save_hash_cache(self) -> None:
        """
        Saves the current hash cache to the cache file.
        """
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.hash_cache, f)
            logger.info("Hash cache saved.")
        except Exception as e:
            logger.error(f"Error saving hash cache: {e}")

    def calculate_quick_hash(self, file_path: str, sample_size: int = 4096) -> str:
        """
        Calculates a quick hash of the first few kilobytes of the file.

        Parameters
        ----------
        file_path : str
            Path to the file.
        sample_size : int, optional
            Number of bytes to read for the quick hash. Defaults to 4096.

        Returns
        -------
        str
            The calculated quick hash as a hexadecimal string.
            Returns None if an error occurs.
        """
        try:
            with open(file_path, "rb") as f:
                sample = f.read(sample_size)
        except Exception as e:
            logger.error(f"Error reading file '{file_path}' for quick hash: {e}")
            return None

        h = xxhash.xxh64()
        h.update(sample)
        return h.hexdigest()

    def calculate_full_hash(self, file_path: str, chunk_size: int = 1024) -> str:
        """
        Calculates the full hash of the file by reading it in chunks.

        Utilizes caching to avoid recalculating hashes for unchanged files.

        Parameters
        ----------
        file_path : str
            Path to the file.
        chunk_size : int, optional
            Size of each chunk to read from the file. Defaults to 1024.

        Returns
        -------
        str
            The calculated full hash as a hexadecimal string.
            Returns None if an error occurs.
        """
        try:
            mod_time = os.path.getmtime(file_path)
        except Exception as e:
            logger.error(f"Error getting modification time for file '{file_path}': {e}")
            return None

        if file_path in self.hash_cache:
            cached_mod_time, cached_hash = self.hash_cache[file_path]
            if cached_mod_time == mod_time:
                return cached_hash

        h = xxhash.xxh64()
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
        except Exception as e:
            logger.error(f"Error reading file '{file_path}' for full hash: {e}")
            return None

        file_hash = h.hexdigest()
        self.hash_cache[file_path] = (mod_time, file_hash)
        return file_hash

    def group_files_by_size(self) -> dict:
        """
        Groups files in the root folder by their size.

        Returns
        -------
        dict
            A dictionary where keys are file sizes and values are lists of file paths.
        """
        size_dict = {}
        for dirpath, _, filenames in os.walk(self.root_folder):
            for filename in filenames:
                if self.file_extension and not filename.endswith(self.file_extension):
                    continue
                file_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(file_path)
                    if self.min_size and size < self.min_size:
                        continue
                except Exception as e:
                    logger.error(f"Error getting size for file '{file_path}': {e}")
                    continue
                size_dict.setdefault(size, []).append(file_path)
        return size_dict

    def get_initial_stats(self) -> dict:
        """
        Gathers initial statistics about the files and folders in the root directory.

        Returns
        -------
        dict
            A dictionary containing total files, total subfolders, and files with unique sizes.
        """
        total_files = 0
        total_subfolders = 0
        for _, dirnames, filenames in os.walk(self.root_folder):
            total_subfolders += len(dirnames)
            total_files += len(filenames)
        unique_size_files = 0
        size_dict = self.group_files_by_size()
        for files in size_dict.values():
            if len(files) == 1:
                unique_size_files += 1
        return {"total_files": total_files, "total_subfolders": total_subfolders, "unique_size_files": unique_size_files}

    def _append_duplicate_csv(self, duplicate_file: str, original_file: str) -> None:
        """
        Appends information about a duplicate file to the CSV file.

        Parameters
        ----------
        duplicate_file : str
            Path to the duplicate file.
        original_file : str
            Path to the original file.
        """
        header = ['timestamp', 'duplicate_file', 'original_file']
        file_exists = os.path.exists(self.csv_file)
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(header)
                writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), duplicate_file, original_file])
        except Exception as e:
            logger.error(f"Error writing to CSV file '{self.csv_file}': {e}")

    def find_duplicates(self) -> list:
        """
        Identifies duplicate files by comparing their hashes.

        Returns
        -------
        list
            A list of tuples where each tuple contains the path to a duplicate file and its original.
        """
        size_dict = self.group_files_by_size()
        duplicates = []
        logger.info(f"Starting full scan in folder: {self.root_folder}")

        for size, files in size_dict.items():
            if len(files) < 2:
                continue
            quick_groups = {}
            for file_path in files:
                quick_hash = self.calculate_quick_hash(file_path)
                if not quick_hash:
                    continue
                quick_groups.setdefault(quick_hash, []).append(file_path)

            for quick, file_list in quick_groups.items():
                if len(file_list) < 2:
                    continue
                full_hashes = {}
                for file_path in file_list:
                    full_hash = self.calculate_full_hash(file_path)
                    if not full_hash:
                        continue
                    if full_hash in full_hashes:
                        orig = full_hashes[full_hash]
                        if os.path.dirname(file_path).lower() < os.path.dirname(orig).lower():
                            original, duplicate = file_path, orig
                            full_hashes[full_hash] = original
                        else:
                            original, duplicate = orig, file_path
                        logger.info(f"Duplicate found: {duplicate} (duplicate) -> {original} (original)")
                        duplicates.append((duplicate, original))
                    else:
                        full_hashes[full_hash] = file_path
        self.save_hash_cache()
        return duplicates

    def find_duplicates_stream(self, stop_requested_callback=lambda: False):
        """
        Generator that yields status updates while finding duplicates, allowing for real-time progress tracking.

        Parameters
        ----------
        stop_requested_callback : callable, optional
            A callback function that returns True if a stop has been requested. Defaults to a no-op.

        Yields
        ------
        tuple
            A tuple containing status message, accumulated duplicate HTML, progress HTML, and statistics info.
        """
        # Step 1: Group files by size and remove files with unique sizes.
        size_dict = self.group_files_by_size()
        candidate_files = []
        for files in size_dict.values():
            if len(files) > 1:
                candidate_files.extend(files)

        # Get initial statistics.
        initial_stats = self.get_initial_stats()
        total_candidate_files = len(candidate_files)
        start_time = time.time()
        progress_html = (
            f"<progress value='0' max='100'></progress>"
            f"<p>Processed 0 / {total_candidate_files} files.<br>Elapsed Time: 00:00:00, ETA: Calculating...</p>"
        )
        stats_info = (
            f"<p>Total Files in Folder: {initial_stats['total_files']}<br>"
            f"Total Subfolders: {initial_stats['total_subfolders']}<br>"
            f"Files with Unique Size: {initial_stats['unique_size_files']}<br>"
            f"Duplicates Found: 0</p>"
        )
        init_message = (
            f"<p>Initialization: {initial_stats['total_files']} total files found. "
            f"{total_candidate_files} candidate files for duplicate analysis (unique files excluded).</p>"
        )
        yield ("Initialization", init_message, progress_html, stats_info)

        # Step 2: Begin scanning hashes.
        yield ("Scanning Hashes", f"<p>Scanning {total_candidate_files} candidate files for duplicates...</p>", progress_html, stats_info)

        processed_files = 0
        total_duplicates = 0
        accumulated_html = ""
        quick_groups_stream = defaultdict(list)

        for file_path in candidate_files:
            if stop_requested_callback():
                progress_html = self._build_progress_html(processed_files, total_candidate_files, start_time)
                yield (
                    "Stopped",
                    accumulated_html + f"<p>Scan stopped by user after processing {processed_files} files.</p>",
                    progress_html,
                    stats_info
                )
                self.save_hash_cache()
                return

            quick_hash = self.calculate_quick_hash(file_path)
            if not quick_hash:
                processed_files += 1
                progress_html = self._build_progress_html(processed_files, total_candidate_files, start_time)
                yield ("Scanning Hashes", accumulated_html, progress_html, stats_info)
                continue

            duplicate_found = False
            for candidate in quick_groups_stream[quick_hash]:
                if candidate["full"] is None:
                    candidate["full"] = self.calculate_full_hash(candidate["path"])
                current_full = self.calculate_full_hash(file_path)
                if current_full == candidate["full"]:
                    # Determine original vs duplicate based on folder name comparison.
                    orig = candidate["path"]
                    if os.path.dirname(file_path).lower() < os.path.dirname(orig).lower():
                        original, duplicate = file_path, orig
                        candidate["path"] = original  # update candidate to new original
                    else:
                        original, duplicate = orig, file_path
                    duplicate_html = (
                        f"<p><b>Duplicate Found:</b><br>"
                        f"Duplicate: <a href='file://{duplicate}' target='_blank'>{duplicate}</a><br>"
                        f"Original: <a href='file://{original}' target='_blank'>{original}</a></p>"
                    )
                    accumulated_html += duplicate_html
                    logger.info(f"Streaming duplicate: {duplicate} duplicates {original}")
                    total_duplicates += 1
                    if self.save_csv:
                        self._append_duplicate_csv(duplicate, original)
                    duplicate_found = True
                    break

            if not duplicate_found:
                quick_groups_stream[quick_hash].append({"path": file_path, "full": None})

            processed_files += 1
            progress_html = self._build_progress_html(processed_files, total_candidate_files, start_time)
            stats_info = (
                f"<p>Total Files in Folder: {initial_stats['total_files']}<br>"
                f"Total Subfolders: {initial_stats['total_subfolders']}<br>"
                f"Files with Unique Size: {initial_stats['unique_size_files']}<br>"
                f"Duplicates Found: {total_duplicates}</p>"
            )
            yield ("Scanning Hashes", accumulated_html, progress_html, stats_info)

            if processed_files % 50 == 0:
                self.save_hash_cache()

        # Step 3: Finalization.
        final_summary = f"<p><b>Finalization:</b> Total Duplicates Found: {total_duplicates}</p>"
        accumulated_html += final_summary
        final_progress = (
            f"<progress value='100' max='100'></progress>"
            f"<p>Processed {total_candidate_files} / {total_candidate_files} files.<br>"
            f"Elapsed Time: {time.strftime('%H:%M:%S', time.gmtime(time.time()-start_time))}, ETA: 00:00:00</p>"
        )
        stats_info = (
            f"<p>Total Files in Folder: {initial_stats['total_files']}<br>"
            f"Total Subfolders: {initial_stats['total_subfolders']}<br>"
            f"Files with Unique Size: {initial_stats['unique_size_files']}<br>"
            f"Duplicates Found: {total_duplicates}</p>"
        )
        yield ("Finalization", accumulated_html, final_progress, stats_info)
        self.save_hash_cache()

    def _build_progress_html(self, processed_files: int, total_files: int, start_time: float) -> str:
        """
        Builds the HTML string for displaying progress.

        Parameters
        ----------
        processed_files : int
            Number of files processed so far.
        total_files : int
            Total number of files to process.
        start_time : float
            Timestamp when the processing started.

        Returns
        -------
        str
            HTML string representing the progress bar and time metrics.
        """
        elapsed_time = time.time() - start_time
        estimated_remaining = (elapsed_time / processed_files) * (total_files - processed_files) if processed_files > 0 else 0
        progress_percent = int((processed_files / total_files) * 100) if total_files > 0 else 100
        elapsed_formatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        eta_formatted = time.strftime("%H:%M:%S", time.gmtime(estimated_remaining)) if processed_files > 0 else "Calculating..."
        return (
            f"<progress value='{progress_percent}' max='100'></progress>"
            f"<p>Processed {processed_files} / {total_files} files.<br>"
            f"Elapsed Time: {elapsed_formatted}, ETA: {eta_formatted}</p>"
        )