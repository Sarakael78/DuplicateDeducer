# Duplicate Deducer

## Description

This application, aptly named the "Duplicate Deducer," is a Python-based tool designed to identify and manage duplicate files within a specified directory and its sub directories. It employs a robust, two-step algorithm to accurately pinpoint duplicates, first by comparing file sizes and then by generating and comparing xxHash digests.

## The application offers several functionalities

* **Finding Duplicates:** Identifies and lists duplicate files within the chosen directory, recursively.
* **Deleting Duplicates:** Removes duplicate files, freeing up valuable storage space.
* **Simulating Deletion:** Provides a preview of the deletion process, showing which files would be deleted without actually removing them.
* **Moving Duplicates:** Relocates duplicate files to a designated target folder.
* **Advanced Reporting:** Provides insights into the overall impact of duplicate files, including the total number of duplicates, the amount of storage space they consume, and a visual representation of the size distribution of duplicate files.

## Features

* **Efficient Algorithm:** The two-step duplicate detection process ensures accuracy while minimising resource consumption.
* **Hash Caching:** xxHash digests are cached to expedite subsequent scans.
* **User-Friendly Interface:** The Gradio interface provides a straightforward way to interact with the application.
* **Detailed Logging:** All activities and errors are meticulously logged for review.
* **Progress Monitoring:** Real-time progress updates and scan statistics are displayed.
* **Stop Functionality:** Users can prematurely terminate the scan if needed.
* **CSV Output:** Option to save duplicate information to a CSV file for record-keeping.
* **Advanced Reporting:** Provides an in-depth analysis of duplicate files, including the total number of duplicates, the amount of storage space they consume, and a visual representation of their size distribution.

## Requirements

* Python 3.7 or higher
* Gradio
* xxhash
* matplotlib
  
## Installation and Setup

1. **Install Git:**
    * Download the latest version of Git from the official website: [https://git-scm.com/downloads](https://git-scm.com/downloads)
    * Run the installer and follow the on-screen instructions.

2. **Clone the Repository:**
    * Open a terminal or command prompt.
    * Navigate to the directory where you want to save the application files.
    * Run the command `git clone https://github.com/Sarakael78/DuplicateDeducer.git` to clone the repository.

3. **Install Python:**
    * Download the latest version of Python from the official website: [https://www.python.org/downloads/](https://www.python.org/downloads/)
    * Run the installer and follow the on-screen instructions. Make sure to check the option to "Add Python to PATH" during installation.

4. **Create a Virtual Environment:**
    * Open a terminal or command prompt.
    * Navigate to the `DuplicateDeducer` directory that was created after cloning the repository.
    * Run the command `python -m venv.venv` (or `python3 -m venv.venv` depending on your system setup) to create a virtual environment named ".venv".

5. **Activate the Virtual Environment:**
    * **On Windows:** Run the command `.venv\Scripts\activate`.
    * **On macOS/Linux:** Run the command `source.venv/bin/activate`.

6. **Install Required Packages:**
    * With the virtual environment activated, run the command `pip install -r requirements.txt` to install the necessary packages.

## Running the Application

1. **Open a terminal or command prompt** in the `DuplicateDeducer` directory (make sure the virtual environment is activated).
2. **Activate the virtual environment** (see above).
3. **Run the command** `python app.py`. This will start the application and launch the Gradio web server.

## Accessing the GUI

1. **Open a web browser** (such as Chrome, Firefox, or Safari).
2. **In the address bar, type** `http://localhost:7860` (or the specific address displayed in your terminal) and press Enter. This will open the Duplicate Deducer GUI in your browser.

## Usage

1. **Select the folder** you wish to scan for duplicates.
2. **(Optional) Specify a file extension** to narrow down the search (e.g., ".txt", ".jpg").
3. **(Optional) Set a minimum file size** to exclude smaller files from the scan.
4. **Choose the desired action:** Find, delete, simulate deletion, or move duplicates.
5. **(If moving duplicates) Select the target folder.**
6. **Click "Submit" to initiate the process.**

## Contributing

Contributions are welcome. Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License.
