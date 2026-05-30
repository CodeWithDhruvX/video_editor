import os
import subprocess
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import moviepy as mp
import ffmpeg

class VideoAudioTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Audio Tool")
        self.root.geometry("450x400")
        self.setup_gui()
    
    def setup_gui(self):
        # Title
        title_label = tk.Label(self.root, text="Video Audio Tool", font=("Arial", 18, "bold"))
        title_label.pack(pady=20)
        
        # Extract Audio Button
        extract_btn = tk.Button(
            self.root, 
            text="Extract Audio from Videos", 
            command=self.extract_audio_from_videos,
            width=30,
            height=2,
            font=("Arial", 10),
            bg="#4CAF50",
            fg="white"
        )
        extract_btn.pack(pady=10)
        
        # Replace Audio Button
        replace_btn = tk.Button(
            self.root, 
            text="Replace Audio in Videos", 
            command=self.replace_audio_in_videos,
            width=30,
            height=2,
            font=("Arial", 10),
            bg="#2196F3",
            fg="white"
        )
        replace_btn.pack(pady=10)
        
        # Merge Videos Button
        merge_btn = tk.Button(
            self.root, 
            text="Merge Videos", 
            command=self.merge_videos_interface,
            width=30,
            height=2,
            font=("Arial", 10),
            bg="#FF9800",
            fg="white"
        )
        merge_btn.pack(pady=10)
        
        # Exit Button
        exit_btn = tk.Button(
            self.root, 
            text="Exit", 
            command=self.root.quit,
            width=30,
            height=1,
            font=("Arial", 10),
            bg="#f44336",
            fg="white"
        )
        exit_btn.pack(pady=20)
    
    def extract_audio_from_videos(self):
        """Extract audio from selected video files"""
        # Select video files
        video_files = filedialog.askopenfilenames(
            title="Select Video Files", 
            filetypes=[
                ("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.flv"),
                ("MP4 files", "*.mp4"),
                ("MKV files", "*.mkv"),
                ("AVI files", "*.avi"),
                ("MOV files", "*.mov"),
                ("FLV files", "*.flv"),
                ("All files", "*.*")
            ]
        )
        
        if not video_files:
            messagebox.showinfo("Info", "No files selected.")
            return

        # Select output folder
        output_dir = filedialog.askdirectory(title="Select Output Folder")
        if not output_dir:
            messagebox.showinfo("Info", "No output folder selected.")
            return

        # Process each video file
        success_count = 0
        error_count = 0
        
        for video_path in video_files:
            try:
                print(f"Processing: {os.path.basename(video_path)}")
                video = mp.VideoFileClip(video_path)
                
                if video.audio is None:
                    print(f"Warning: No audio track found in {os.path.basename(video_path)}")
                    error_count += 1
                    video.close()
                    continue
                
                output_file = os.path.join(
                    output_dir, 
                    os.path.splitext(os.path.basename(video_path))[0] + ".wav"
                )
                
                video.audio.write_audiofile(output_file, codec='pcm_s16le', logger=None)
                video.close()  # Important: close the clip to free resources
                
                print(f"Extracted: {output_file}")
                success_count += 1
                
            except Exception as e:
                print(f"Error processing {video_path}: {e}")
                error_count += 1
        
        # Show completion message
        message = f"Audio extraction completed!\nSuccess: {success_count}\nErrors: {error_count}"
        messagebox.showinfo("Extraction Complete", message)
    
    def replace_audio_in_videos(self):
        """Replace audio in selected video files"""
        # Select video files
        video_paths = filedialog.askopenfilenames(
            title="Select Video Files", 
            filetypes=[
                ("Video Files", "*.mkv;*.mp4;*.avi;*.mov"),
                ("MKV files", "*.mkv"),
                ("MP4 files", "*.mp4"),
                ("AVI files", "*.avi"),
                ("MOV files", "*.mov"),
                ("All files", "*.*")
            ]
        )
        
        # Select audio files
        audio_paths = filedialog.askopenfilenames(
            title="Select Audio Files", 
            filetypes=[
                ("Audio Files", "*.wav;*.mp3;*.aac;*.flac"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("AAC files", "*.aac"),
                ("FLAC files", "*.flac"),
                ("All files", "*.*")
            ]
        )

        if not video_paths or not audio_paths:
            messagebox.showinfo("Info", "File selection canceled or incomplete.")
            return

        # Select output folder
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if not output_folder:
            messagebox.showinfo("Info", "Output folder selection canceled.")
            return

        # Get output format
        output_format = simpledialog.askstring(
            "Output Format", 
            "Enter output format (mp4/mkv/avi):", 
            initialvalue="mp4"
        )
        
        if not output_format or output_format.strip().lower() not in ["mp4", "mkv", "avi"]:
            messagebox.showinfo("Info", "Invalid format selected. Defaulting to MP4.")
            output_format = "mp4"
        else:
            output_format = output_format.strip().lower()

        # Create dictionaries for matching files by name
        video_dict = {os.path.splitext(os.path.basename(v))[0]: v for v in video_paths}
        audio_dict = {os.path.splitext(os.path.basename(a))[0]: a for a in audio_paths}

        # Process matched files
        success_count = 0
        error_count = 0
        unmatched_videos = []

        for name, video_path in video_dict.items():
            if name in audio_dict:
                audio_path = audio_dict[name]
                output_path = os.path.join(output_folder, f"{name}_output.{output_format}")
                
                if self.replace_audio(video_path, audio_path, output_path):
                    success_count += 1
                else:
                    error_count += 1
            else:
                unmatched_videos.append(name)
                print(f"No matching audio found for {name}")

        # Show completion message
        message = f"Audio replacement completed!\nSuccess: {success_count}\nErrors: {error_count}"
        if unmatched_videos:
            message += f"\nUnmatched videos: {len(unmatched_videos)}"
        
        messagebox.showinfo("Replacement Complete", message)
    
    def replace_audio(self, video_path, audio_path, output_path):
        """Replace audio in a single video file using FFmpeg"""
        try:
            print(f"Processing: {os.path.basename(video_path)} -> {os.path.basename(audio_path)}")
            
            command = [
                "ffmpeg", "-i", video_path, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-strict", "experimental",
                "-map", "0:v:0", "-map", "1:a:0", "-y",  # -y to overwrite output files
                output_path
            ]
            
            # Run with minimal output
            result = subprocess.run(
                command, 
                check=True, 
                capture_output=True, 
                text=True
            )
            
            print(f"Successfully created: {os.path.basename(output_path)}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error processing {video_path}: {e}")
            print(f"FFmpeg error output: {e.stderr}")
            return False
        except FileNotFoundError:
            print("Error: FFmpeg not found. Please make sure FFmpeg is installed and in your PATH.")
            messagebox.showerror("Error", "FFmpeg not found. Please install FFmpeg and add it to your PATH.")
            return False
    
    def merge_videos_interface(self):
        """Interface for merging videos functionality"""
        # Select video files
        video_files = filedialog.askopenfilenames(
            title="Select Video Files to Merge", 
            filetypes=[
                ("Video Files", "*.mp4;*.mkv;*.avi;*.mov"),
                ("MP4 files", "*.mp4"),
                ("MKV files", "*.mkv"),
                ("AVI files", "*.avi"),
                ("MOV files", "*.mov"),
                ("All files", "*.*")
            ]
        )
        
        if not video_files:
            messagebox.showinfo("Info", "No video files selected.")
            return
        
        if len(video_files) < 2:
            messagebox.showwarning("Warning", "Please select at least 2 video files to merge.")
            return
        
        # Select output folder
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if not output_folder:
            messagebox.showinfo("Info", "No output folder selected.")
            return
        
        # Get output filename
        output_filename = simpledialog.askstring(
            "Output Filename", 
            "Enter output filename (without extension):", 
            initialvalue="merged_video"
        )
        
        if not output_filename:
            output_filename = "merged_video"
        
        # Merge videos
        if self.merge_videos(list(video_files), output_folder, output_filename):
            messagebox.showinfo("Success", f"Videos merged successfully!\nOutput: {output_filename}.mp4")
        else:
            messagebox.showerror("Error", "Failed to merge videos. Check console for details.")
    
    def merge_videos(self, video_files, output_folder, output_filename):
        """Merge multiple video files using ffmpeg-python"""
        if not video_files:
            print("No video files provided. Exiting...")
            return False

        if not output_folder:
            print("No output folder provided. Exiting...")
            return False

        output_file = os.path.join(output_folder, f"{output_filename}.mp4")
        list_file = os.path.join(output_folder, "input_videos.txt")
        
        try:
            # Create input list file
            with open(list_file, "w") as f:
                for video in video_files:
                    # Normalize path for cross-platform compatibility
                    normalized_path = os.path.normpath(video).replace("\\", "/")
                    f.write(f"file '{normalized_path}'\n")
            
            print(f"Merging {len(video_files)} videos...")
            for i, video in enumerate(video_files, 1):
                print(f"{i}. {os.path.basename(video)}")
            
            # Use ffmpeg-python to merge videos
            ffmpeg.input(list_file, format='concat', safe=0).output(
                output_file, 
                c='copy'
            ).run(overwrite_output=True, quiet=True)
            
            print(f"Videos merged successfully into {output_file}")
            return True
            
        except ffmpeg.Error as e:
            print("Error merging videos:", e)
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
        finally:
            # Clean up the temporary list file
            if os.path.exists(list_file):
                try:
                    os.remove(list_file)
                except:
                    pass
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main function to run the application"""
    try:
        app = VideoAudioTool()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        messagebox.showerror("Error", f"Application error: {e}")

if __name__ == "__main__":
    main()