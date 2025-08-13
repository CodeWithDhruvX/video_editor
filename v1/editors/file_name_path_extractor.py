import os
import tkinter as tk
from tkinter import filedialog

def select_folder_and_get_mp4_files():
    root = tk.Tk()
    root.withdraw()

    folder_path = filedialog.askdirectory(title="Select Folder")
    print("Selected folder:", folder_path)  # Debug print

    if not folder_path:
        print("[]")
        return []

    mp4_files = []
    for root_dir, _, files in os.walk(folder_path):
        for file in files:
            print("Checking file:", file)  # Debug print
            if file.lower().endswith(".mp4"):
                full_path = os.path.join(root_dir, file)
                mp4_files.append(full_path.replace("\\", "/"))

    return mp4_files

# Run and print array
if __name__ == "__main__":
    files = select_folder_and_get_mp4_files()
    print("[")
    for f in files:
        print(f'    "{f}",')
    print("]")
