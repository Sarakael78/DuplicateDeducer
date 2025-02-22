# -----------------------------------------------------------------------------
# app.py
# -----------------------------------------------------------------------------

import gradio as gr
from modules.processing import process_action
import os
import time

# Remove circular import
STOP_REQUESTED = False

def update_logs():
    try:
        with open("duplicate_finder.log", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading log file: {e}"

# Define stop_scan BEFORE it's referenced in the Blocks context
def stop_scan():
    global STOP_REQUESTED
    STOP_REQUESTED = True

with gr.Blocks() as app:
    gr.Markdown("# Duplicate Deducer")
    with gr.Tabs():
        with gr.TabItem("Controls & Status"):
            gr.Markdown("**Settings and Status**")
            with gr.Row():

                folders_input = gr.Textbox(label="Folders to Scan (one per line)", placeholder="Enter one folder path per line.")
                file_extension_input = gr.Textbox(label="File Extension (Optional)", placeholder="e.g., .txt, .jpg")
            with gr.Row():
                min_size_input = gr.Number(label="Minimum File Size (MB)", value=0)
                action = gr.Radio(
                    ["Find Duplicates", "Delete Duplicates", "Simulate Deletion", "Move Duplicates", "Advanced Report"],
                    label="Action",
                    value="Find Duplicates",
                )
            with gr.Row():
               # Changed target_folder widget from a File component to a Textbox for folder path input.
                target_folder_input = gr.Textbox(label="Target Folder (For Moving Duplicates)", placeholder="Enter folder path here")
                save_csv = gr.Checkbox(label="Save duplicate info to CSV", value=False)
            with gr.Row():
                submit_button = gr.Button("Submit")
                stop_button = gr.Button("Stop")
            status_output = gr.Textbox(label="Status Messages", interactive=False)
            progress_output = gr.HTML(label="Progress")
            stat_details = gr.HTML(label="Scan Statistics")
        with gr.TabItem("Duplicates/Results"):
            main_output = gr.HTML(label="Results")
        with gr.TabItem("Advanced Reports"):
            report_output = gr.HTML(label="Advanced Report")
        with gr.TabItem("Logs"):
            log_output = gr.HTML(label="Log Output")

    def update_logs_periodically():
        while True:
            time.sleep(3)
            yield update_logs()

    log_output.change(
        fn=update_logs_periodically,
        outputs=log_output,
        show_progress=False,
        queue=False
    )

    # Handle the submit button click event
    submit_button.click(
        fn=process_action,
        inputs=[
            folders_input, 
            file_extension_input,
            min_size_input,
            action,
            target_folder_input,
            save_csv,
            gr.State(lambda: STOP_REQUESTED)  # Add as last input
        ],
        outputs=[status_output, main_output, progress_output, stat_details, report_output],
        concurrency_limit=1
    )

    # Handle the stop button click event
    stop_button.click(
        fn=stop_scan,
        inputs=[],
        outputs=[],
        queue=False
    )

if __name__ == "__main__":
    app.queue()  # Enable streaming for Gradio
    app.launch()