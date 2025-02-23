# -----------------------------------------------------------------------------
# app.py
# -----------------------------------------------------------------------------
import gradio as gr
from modules.processing import processAction  # Ensure processAction is a generator
import os
import threading
from typing import List, Any

# Use threading.Event for a thread-safe stop flag
STOP_EVENT = threading.Event()

def stopScan() -> str:
	"""
	Sets the stop flag using threading.Event to request the scanning process to stop.
	Returns a message indicating that the stop has been requested.
	"""
	STOP_EVENT.set()
	return "Scan stop requested."

def resetStopFlag() -> None:
	"""
	Resets the stop flag by clearing the threading.Event.
	"""
	STOP_EVENT.clear()

def updateLogs() -> str:
	"""
	Reads and returns the content of the log file ('duplicate_finder.log').
	If an error occurs during file reading, returns an error message.
	"""
	try:
		with open("duplicate_finder.log", "r", encoding="utf-8") as f:
			return f.read()
	except Exception as e:
		return f"Error reading log file: {e}"

def validateFolders(folders: str) -> List[str]:
	"""
	Validates folder paths provided in a multiline string (one folder per line).
	Strips whitespace, filters out empty entries, and verifies that the folders exist.
	
	Parameters:
	    folders (str): Multiline string with folder paths.
	
	Returns:
	    List[str]: List of validated folder paths.
	
	Raises:
	    ValueError: If no folders are provided or if any folder does not exist.
	"""
	folderList: List[str] = [folder.strip() for folder in folders.splitlines() if folder.strip()]
	if not folderList:
		raise ValueError("No folders provided; please enter at least one folder path.")
	invalidFolders: List[str] = [folder for folder in folderList if not os.path.isdir(folder)]
	if invalidFolders:
		raise ValueError(f"Invalid folder(s): {', '.join(invalidFolders)}")
	return folderList

def handleSubmit(
	folders: str,
	fileExt: str,
	minSize: float,
	actionSelected: str,
	targetFolder: str,
	saveCsvFlag: bool
) -> Any:
	"""
	Handles the submit button click event for initiating the scanning process.
	Validates inputs, resets the stop flag, and starts the scanning process via the processAction generator.
	
	Parameters:
	    folders (str): Multiline string with folder paths.
	    fileExt (str): Optional file extension filter.
	    minSize (float): Minimum file size in MB.
	    actionSelected (str): Action to perform (e.g., "Find Duplicates").
	    targetFolder (str): Target folder for actions like "Move Duplicates".
	    saveCsvFlag (bool): Whether to save duplicate info to CSV.
	
	Returns:
	    A generator yielding updates for:
	    - Status messages
	    - Main output results
	    - Progress updates (HTML)
	    - Scan statistics (HTML)
	    - Advanced report (HTML)
	    - Log output (HTML)
	"""
	# Reset the stop flag for a new scan
	resetStopFlag()
	
	# Validate the folder inputs and catch issues before starting the process
	try:
		validFolders = validateFolders(folders)
	except Exception as e:
		errorMsg = f"Input validation error: {str(e)}"
		# Yield error messages to all output components
		yield errorMsg, "<div></div>", "<div></div>", "<div></div>", "<div></div>", errorMsg
		return
	
	# Clean and validate the file extension: ensure it starts with a dot if provided
	newFileExt = fileExt.strip()
	if newFileExt and not newFileExt.startswith('.'):
		newFileExt = '.' + newFileExt
	
	# Start the scanning process using the processAction generator.
	# Pass a lambda that checks if the stop flag is set.
	yield from processAction(
		"\n".join(validFolders),
		newFileExt,
		minSize,
		actionSelected,
		targetFolder,
		saveCsvFlag,
		lambda: STOP_EVENT.is_set()
	)

# Build the Gradio interface
with gr.Blocks(title="Duplicate Deducer") as app:
	gr.Markdown("# Duplicate Deducer")
	
	# Custom CSS for the log box styling
	gr.Markdown("""
	<style>
	#log-box {
		background-color: #f9f9f9;
		padding: 10px;
		border: 1px solid #ddd;
		height: 300px;
		overflow-y: scroll;
		white-space: pre-wrap;
	}
	</style>
	""")
	
	with gr.Tabs():
		# Controls & Status Tab
		with gr.TabItem("Controls & Status"):
			gr.Markdown("**Settings and Status**")
			
			with gr.Row():
				foldersInput = gr.Textbox(
					label="Folders to Scan (one per line)",
					placeholder="Enter one folder path per line.",
					lines=5
				)
				fileExtensionInput = gr.Textbox(
					label="File Extension (Optional)",
					placeholder="e.g., .txt, .jpg"
				)
			
			with gr.Row():
				minSizeInput = gr.Number(
					label="Minimum File Size (MB)",
					value=0,
					precision=2
				)
				actionRadio = gr.Radio(
					["Find Duplicates", "Delete Duplicates", "Simulate Deletion", "Move Duplicates"],
					label="Action",
					value="Find Duplicates"
				)
			
			with gr.Row():
				targetFolderInput = gr.Textbox(
					label="Target Folder (For Moving Duplicates)",
					placeholder="Enter folder path here."
				)
				saveCsvCheckbox = gr.Checkbox(
					label="Save duplicate info to CSV",
					value=False
				)
			
			with gr.Row():
				submitButton = gr.Button("Submit", variant="primary")
				stopButton = gr.Button("Stop", variant="secondary")
			
			statusOutput = gr.Textbox(
				label="Status Messages",
				interactive=False,
				lines=2,
				placeholder="Status will appear here."
			)
			progressOutput = gr.HTML(label="Progress")
			statDetails = gr.HTML(label="Scan Statistics")
		
		# Duplicates/Results Tab
		with gr.TabItem("Duplicates/Results"):
			mainOutput = gr.HTML(label="Results")
		
		# Advanced Reports Tab
		with gr.TabItem("Advanced Reports"):
			reportOutput = gr.HTML(label="Advanced Report")
		
		# Logs Tab with a Refresh button for updating log content
		with gr.TabItem("Logs"):
			logOutput = gr.HTML(
				label="Log Output",
				elem_id="log-box",
				value="<div style='height:300px; overflow:auto;'></div>"
			)
			refreshLogsButton = gr.Button("Refresh Logs", variant="secondary")
			# Bind the refresh button to updateLogs
			refreshLogsButton.click(
				fn=updateLogs,
				inputs=[],
				outputs=[logOutput],
				queue=False
			)
	
	# Bind the submit button click event to handleSubmit;
	# Streaming responses are supported via the generator from handleSubmit.
	submitButton.click(
		fn=handleSubmit,
		inputs=[
			foldersInput,
			fileExtensionInput,
			minSizeInput,
			actionRadio,
			targetFolderInput,
			saveCsvCheckbox
		],
		outputs=[
			statusOutput,
			mainOutput,
			progressOutput,
			statDetails,
			reportOutput,
			logOutput  # Updated log output
		],
		queue=True,
		concurrency_limit=1
	)
	
	# Bind the stop button click event to stopScan
	stopButton.click(
		fn=stopScan,
		inputs=[],
		outputs=[statusOutput],
		queue=False
	)

if __name__ == "__main__":
	app.launch()

# -----------------------------------------------------------------------------
# End of app.py
# -----------------------------------------------------------------------------