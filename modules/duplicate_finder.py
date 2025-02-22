# -----------------------------------------------------------------------------
# Duplicate_finder.py
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
    Scans the given directory recursively for duplicate files based on their content,
    using a two‑step approach:
      1. Group files by size (removing files unique in size).
      2. Calculate a quick hash based on the first few kilobytes.
      3. For candidate groups, compute a full hash (with persistent caching) to confirm duplicates.
    
    Attributes:
        root_folder (str): Folder path to scan.
        file_extension (Optional[str]): Optional file extension filter.
        min_size (int): Minimum file size in bytes.
        csv_file (str): CSV output file path.
        save_csv (bool): Flag to determine whether duplicate info should be saved to CSV.
    """
    def __init__(self, root_folder: str, file_extension: str = None, min_size: int = 0) -> None:
        self.root_folder = os.path.abspath(os.path.expanduser(root_folder))
        self.file_extension = file_extension.strip() if file_extension and file_extension.strip() != "" else None
        self.min_size = min_size  # in bytes
        self.cache_file = "hash_cache.pkl"
        self.hash_cache = self.load_hash_cache()
        self.csv_file = "duplicates.csv"
        self.save_csv = False

    def load_hash_cache(self) -> dict:
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
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.hash_cache, f)
            logger.info("Hash cache saved.")
        except Exception as e:
            logger.error(f"Error saving hash cache: {e}")

    def calculate_quick_hash(self, file_path: str, sample_size: int = 4096) -> str:
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
        size_dict = self.group_files_by_size()
        candidate_files = []
        for files in size_dict.values():
            if len(files) > 1:
                candidate_files.extend(files)

        initial_stats = self.get_initial_stats()  # get initial stats once
        total_files = len(candidate_files)
        processed_files = 0
        total_duplicates = 0
        accumulated_html = ""
        start_time = time.time()
        quick_groups_stream = defaultdict(list)

        stats_info = (
            f"<p>Total Files in Folder: {initial_stats['total_files']}<br>"
            f"Total Subfolders: {initial_stats['total_subfolders']}<br>"
            f"Files with Unique Size: {initial_stats['unique_size_files']}<br>"
            f"Duplicates Found: {total_duplicates}</p>"
        )

        progress_html = (
            f"<progress value='0' max='100'></progress>"
            f"<p>Processed 0 / {total_files} files.<br>Elapsed Time: 00:00:00, ETA: Calculating...</p>"
        )
        yield ("Scanning", f"<p>Starting scan in folder: <i>{self.root_folder}</i></p>", progress_html, stats_info)

        for file_path in candidate_files:
            if stop_requested_callback():
                progress_html = self._build_progress_html(processed_files, total_files, start_time)
                yield ("Stopped", accumulated_html + f"<p>Scan stopped by user after processing {processed_files} files.</p>", progress_html, stats_info)
                self.save_hash_cache()
                return

            quick_hash = self.calculate_quick_hash(file_path)
            if not quick_hash:
                processed_files += 1
                progress_html = self._build_progress_html(processed_files, total_files, start_time)
                yield ("Scanning", accumulated_html, progress_html, stats_info)
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
                        f"<p><b>Duplicate:</b> <a href='file://{duplicate}' target='_blank'>{duplicate}</a><br>"
                        f"<b>Original:</b> <a href='file://{original}' target='_blank'>{original}</a></p>"
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
            progress_html = self._build_progress_html(processed_files, total_files, start_time)
            stats_info = (
                f"<p>Total Files in Folder: {initial_stats['total_files']}<br>"
                f"Total Subfolders: {initial_stats['total_subfolders']}<br>"
                f"Files with Unique Size: {initial_stats['unique_size_files']}<br>"
                f"Duplicates Found: {total_duplicates}</p>"
            )
            yield ("Scanning", accumulated_html, progress_html, stats_info)

            if processed_files % 50 == 0:
                self.save_hash_cache()

        summary_text = f"<p><b>Total Duplicates Found:</b> {total_duplicates}</p>"
        accumulated_html += summary_text
        final_progress = (
            f"<progress value='100' max='100'></progress>"
            f"<p>Processed {total_files} / {total_files} files.<br>"
            f"Elapsed Time: {time.strftime('%H:%M:%S', time.gmtime(time.time()-start_time))}, ETA: 00:00:00</p>"
        )
        stats_info = (
            f"<p>Total Files in Folder: {initial_stats['total_files']}<br>"
            f"Total Subfolders: {initial_stats['total_subfolders']}<br>"
            f"Files with Unique Size: {initial_stats['unique_size_files']}<br>"
            f"Duplicates Found: {total_duplicates}</p>"
        )
        yield ("Finished", accumulated_html, final_progress, stats_info)
        self.save_hash_cache()

    def _build_progress_html(self, processed_files: int, total_files: int, start_time: float) -> str:
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