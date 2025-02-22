# Duplicate Deducer

## Description

This application, aptly named the "Duplicate Deducer," is a Python-based tool designed to identify and manage duplicate files within a specified directory. It employs a robust, two-step algorithm to accurately pinpoint duplicates, first by comparing file sizes and then by generating and comparing xxHash digests.

The application offers several functionalities:

* **Finding Duplicates:** Identifies and lists duplicate files within the chosen directory.
* **Deleting Duplicates:** Removes duplicate files, freeing up valuable storage space.
* **Simulating Deletion:** Provides a preview of the deletion process, showing which files would be deleted without actually removing them.
* **Moving Duplicates:** Relocates duplicate files to a designated target folder.

## Usage

1. **Launch the application.**
2. **Select the folder** you wish to scan for duplicates.
3. **(Optional) Specify a file extension** to narrow down the search (e.g., ".txt", ".jpg").
4. **(Optional) Set a minimum file size** to exclude smaller files from the scan.
5. **Choose the desired action:** Find, delete, simulate deletion, or move duplicates.
6. **(If moving duplicates) Select the target folder.**
7. **Click "Submit" to initiate the process.**

## Features

* **Efficient Algorithm:** The two-step duplicate detection process ensures accuracy while minimising resource consumption.
* **Hash Caching:** xxHash digests are cached to expedite subsequent scans.
* **User-Friendly Interface:** The Gradio interface provides a straightforward way to interact with the application.
* **Detailed Logging:** All activities and errors are meticulously logged for review.
* **Progress Monitoring:** Real-time progress updates and scan statistics are displayed.
* **Stop Functionality:** Users can prematurely terminate the scan if needed.
* **CSV Output:** Option to save duplicate information to a CSV file for record-keeping.

## Requirements

* Python 3.7 or higher
* Gradio
* xxhash

## Installation

1. Clone the repository.
2. Install the required packages: `pip install -r requirements.txt`

## Contributing

Contributions are welcome. Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License.
