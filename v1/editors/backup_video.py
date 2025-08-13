import tkinter as tk
from tkinter import filedialog
import shutil
import os

# Supported video formats
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov")

def backup_videos_from_folder():
    # Hide main window
    root = tk.Tk()
    root.withdraw()

    # Ask user to select a folder
    source_folder = filedialog.askdirectory(title="Select folder containing videos")

    if not source_folder:
        print("❌ No folder selected.")
        return

    # Create backup folder path inside the selected folder
    backup_folder = os.path.join(source_folder, "videos_backup")
    os.makedirs(backup_folder, exist_ok=True)
    print(f"📁 Backup folder created (if not exist): {backup_folder}")

    # Loop through all files in the selected folder
    copied_files = 0
    for filename in os.listdir(source_folder):
        file_path = os.path.join(source_folder, filename)

        # Check if it's a video file
        if os.path.isfile(file_path) and filename.lower().endswith(VIDEO_EXTENSIONS):
            destination = os.path.join(backup_folder, filename)
            try:
                shutil.copy2(file_path, destination)
                print(f"✅ Copied: {filename}")
                copied_files += 1
            except Exception as e:
                print(f"❌ Failed to copy {filename}: {e}")

    if copied_files == 0:
        print("⚠️ No video files found in the selected folder.")
    else:
        print(f"🎉 {copied_files} video(s) backed up successfully to {backup_folder}")

if __name__ == "__main__":
    backup_videos_from_folder()
