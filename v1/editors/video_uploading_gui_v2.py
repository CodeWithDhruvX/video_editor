import os
import json
import time
import threading
from datetime import datetime
import pytz
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Constants
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
CATEGORY_MAP = {
    "Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10", "Pets & Animals": "15",
    "Sports": "17", "Travel & Events": "19", "Gaming": "20", "People & Blogs": "22", 
    "Comedy": "23", "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26", 
    "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"
}

class YouTubeUploaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Uploader Pro")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.youtube_service = None
        self.client_secret_file = None
        self.video_file = None
        self.thumbnail_file = None
        self.videos_list = []
        
        # Setup GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Main container
        main_frame = Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = Label(main_frame, text="🎥 YouTube Video Uploader Pro", 
                           font=('Arial', 18, 'bold'), bg='#f0f0f0', fg='#d73527')
        title_label.pack(pady=10)
        
        # Authentication Frame
        auth_frame = LabelFrame(main_frame, text="🔐 Authentication", 
                               font=('Arial', 12, 'bold'), bg='#f0f0f0')
        auth_frame.pack(fill=X, pady=5)
        
        Button(auth_frame, text="📁 Select client_secret.json", 
               command=self.select_client_secret, bg='#4285f4', fg='white',
               font=('Arial', 10, 'bold')).pack(side=LEFT, padx=5, pady=5)
        
        self.auth_status = Label(auth_frame, text="❌ Not Authenticated", 
                                bg='#f0f0f0', fg='red')
        self.auth_status.pack(side=LEFT, padx=10)
        
        Button(auth_frame, text="🔗 Connect to YouTube", 
               command=self.authenticate_youtube, bg='#0f9d58', fg='white',
               font=('Arial', 10, 'bold')).pack(side=RIGHT, padx=5, pady=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True, pady=10)
        
        # Single Upload Tab
        self.create_single_upload_tab()
        
        # Batch Upload Tab
        self.create_batch_upload_tab()
        
        # Video Management Tab
        self.create_management_tab()
        
    def create_single_upload_tab(self):
        # Single Upload Frame
        single_frame = Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(single_frame, text="📤 Single Upload")
        
        # Create scrollable frame
        canvas = Canvas(single_frame, bg='#f0f0f0')
        scrollbar = Scrollbar(single_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas, bg='#f0f0f0')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # File Selection
        file_frame = LabelFrame(scrollable_frame, text="📁 File Selection", 
                               font=('Arial', 11, 'bold'), bg='#f0f0f0')
        file_frame.pack(fill=X, padx=5, pady=5)
        
        Button(file_frame, text="🎬 Select Video File", 
               command=self.select_video_file, bg='#ea4335', fg='white').pack(side=LEFT, padx=5, pady=5)
        
        self.video_file_label = Label(file_frame, text="No video selected", bg='#f0f0f0')
        self.video_file_label.pack(side=LEFT, padx=10)
        
        Button(file_frame, text="🖼️ Select Thumbnail", 
               command=self.select_thumbnail, bg='#fbbc05', fg='black').pack(side=RIGHT, padx=5, pady=5)
        
        self.thumbnail_label = Label(file_frame, text="No thumbnail selected", bg='#f0f0f0')
        self.thumbnail_label.pack(side=RIGHT, padx=10)
        
        # Video Details
        details_frame = LabelFrame(scrollable_frame, text="📝 Video Details", 
                                  font=('Arial', 11, 'bold'), bg='#f0f0f0')
        details_frame.pack(fill=X, padx=5, pady=5)
        
        # Title
        Label(details_frame, text="Title:", bg='#f0f0f0').grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.title_entry = Entry(details_frame, width=60)
        self.title_entry.grid(row=0, column=1, padx=5, pady=5, sticky=W+E)
        
        # Description
        Label(details_frame, text="Description:", bg='#f0f0f0').grid(row=1, column=0, sticky=NW, padx=5, pady=5)
        self.description_text = ScrolledText(details_frame, height=5, width=60)
        self.description_text.grid(row=1, column=1, padx=5, pady=5, sticky=W+E)
        
        # Tags
        Label(details_frame, text="Tags (comma separated):", bg='#f0f0f0').grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.tags_entry = Entry(details_frame, width=60)
        self.tags_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W+E)
        
        # Category
        Label(details_frame, text="Category:", bg='#f0f0f0').grid(row=3, column=0, sticky=W, padx=5, pady=5)
        self.category_var = StringVar(value="Entertainment")
        category_combo = ttk.Combobox(details_frame, textvariable=self.category_var, 
                                     values=list(CATEGORY_MAP.keys()), width=30)
        category_combo.grid(row=3, column=1, padx=5, pady=5, sticky=W)
        
        # Privacy
        Label(details_frame, text="Privacy:", bg='#f0f0f0').grid(row=4, column=0, sticky=W, padx=5, pady=5)
        self.privacy_var = StringVar(value="public")
        privacy_frame = Frame(details_frame, bg='#f0f0f0')
        privacy_frame.grid(row=4, column=1, sticky=W, padx=5, pady=5)
        
        Radiobutton(privacy_frame, text="Public", variable=self.privacy_var, 
                   value="public", bg='#f0f0f0').pack(side=LEFT)
        Radiobutton(privacy_frame, text="Unlisted", variable=self.privacy_var, 
                   value="unlisted", bg='#f0f0f0').pack(side=LEFT)
        Radiobutton(privacy_frame, text="Private", variable=self.privacy_var, 
                   value="private", bg='#f0f0f0').pack(side=LEFT)
        
        # Made for Kids
        self.kids_var = BooleanVar()
        Checkbutton(details_frame, text="Made for Kids", variable=self.kids_var, 
                   bg='#f0f0f0').grid(row=5, column=1, sticky=W, padx=5, pady=5)
        
        # Schedule Publishing
        schedule_frame = LabelFrame(scrollable_frame, text="📅 Schedule Publishing", 
                                   font=('Arial', 11, 'bold'), bg='#f0f0f0')
        schedule_frame.pack(fill=X, padx=5, pady=5)
        
        self.schedule_var = BooleanVar()
        Checkbutton(schedule_frame, text="Schedule for later", variable=self.schedule_var,
                   command=self.toggle_schedule, bg='#f0f0f0').pack(anchor=W, padx=5, pady=5)
        
        self.schedule_frame_inner = Frame(schedule_frame, bg='#f0f0f0')
        self.schedule_frame_inner.pack(fill=X, padx=5, pady=5)
        
        Label(self.schedule_frame_inner, text="Date (YYYY-MM-DD):", bg='#f0f0f0').grid(row=0, column=0, padx=5, pady=5)
        self.date_entry = Entry(self.schedule_frame_inner, width=15)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        
        Label(self.schedule_frame_inner, text="Time (HH:MM:SS):", bg='#f0f0f0').grid(row=0, column=2, padx=5, pady=5)
        self.time_entry = Entry(self.schedule_frame_inner, width=15)
        self.time_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Initially disable schedule frame
        for widget in self.schedule_frame_inner.winfo_children():
            widget.configure(state='disabled')
        
        # Playlist
        playlist_frame = LabelFrame(scrollable_frame, text="📋 Playlist", 
                                   font=('Arial', 11, 'bold'), bg='#f0f0f0')
        playlist_frame.pack(fill=X, padx=5, pady=5)
        
        Label(playlist_frame, text="Playlist Name (optional):", bg='#f0f0f0').pack(side=LEFT, padx=5, pady=5)
        self.playlist_entry = Entry(playlist_frame, width=40)
        self.playlist_entry.pack(side=LEFT, padx=5, pady=5)
        
        # Upload Button
        upload_frame = Frame(scrollable_frame, bg='#f0f0f0')
        upload_frame.pack(fill=X, pady=20)
        
        self.upload_btn = Button(upload_frame, text="🚀 Upload Video", 
                               command=self.upload_single_video, bg='#0f9d58', fg='white',
                               font=('Arial', 14, 'bold'), height=2)
        self.upload_btn.pack(pady=10)
        
        # Progress
        self.progress_var = StringVar(value="Ready to upload")
        self.progress_label = Label(upload_frame, textvariable=self.progress_var, 
                                   bg='#f0f0f0', font=('Arial', 10))
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(upload_frame, mode='determinate')
        self.progress_bar.pack(fill=X, padx=50, pady=5)
        
        # Configure grid weights
        details_frame.columnconfigure(1, weight=1)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_batch_upload_tab(self):
        batch_frame = Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(batch_frame, text="📦 Batch Upload")
        
        # Instructions
        Label(batch_frame, text="📋 Batch Upload from JSON Metadata", 
              font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=10)
        
        # File selection
        file_frame = Frame(batch_frame, bg='#f0f0f0')
        file_frame.pack(pady=10)
        
        Button(file_frame, text="📁 Select Metadata JSON", 
               command=self.select_metadata_file, bg='#4285f4', fg='white',
               font=('Arial', 12, 'bold')).pack(side=LEFT, padx=5)
        
        self.metadata_label = Label(file_frame, text="No file selected", bg='#f0f0f0')
        self.metadata_label.pack(side=LEFT, padx=10)
        
        # Videos list
        list_frame = LabelFrame(batch_frame, text="📹 Videos to Upload", 
                               font=('Arial', 11, 'bold'), bg='#f0f0f0')
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.videos_listbox = Listbox(list_frame, height=15)
        self.videos_listbox.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # Batch upload button
        Button(batch_frame, text="🚀 Upload All Videos", 
               command=self.upload_batch_videos, bg='#0f9d58', fg='white',
               font=('Arial', 14, 'bold'), height=2).pack(pady=10)
        
        # Batch progress
        self.batch_progress_var = StringVar(value="Ready for batch upload")
        Label(batch_frame, textvariable=self.batch_progress_var, 
              bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
        
        self.batch_progress_bar = ttk.Progressbar(batch_frame, mode='determinate')
        self.batch_progress_bar.pack(fill=X, padx=50, pady=5)
        
    def create_management_tab(self):
        mgmt_frame = Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(mgmt_frame, text="⚙️ Management")
        
        Label(mgmt_frame, text="🔧 Video Management Tools", 
              font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=20)
        
        # Coming soon features
        features = [
            "📊 View uploaded videos",
            "✏️ Update video metadata", 
            "🖼️ Change thumbnails",
            "📋 Manage playlists",
            "📈 View analytics"
        ]
        
        for feature in features:
            Label(mgmt_frame, text=f"{feature} - Coming Soon!", 
                  bg='#f0f0f0', font=('Arial', 11)).pack(pady=5)
    
    def toggle_schedule(self):
        state = 'normal' if self.schedule_var.get() else 'disabled'
        for widget in self.schedule_frame_inner.winfo_children():
            widget.configure(state=state)
    
    def select_client_secret(self):
        file_path = filedialog.askopenfilename(
            title="Select client_secret.json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            self.client_secret_file = file_path
            messagebox.showinfo("Success", "client_secret.json selected successfully!")
    
    def authenticate_youtube(self):
        if not self.client_secret_file:
            messagebox.showerror("Error", "Please select client_secret.json first!")
            return
        
        try:
            self.youtube_service = self.get_authenticated_service(self.client_secret_file)
            self.auth_status.config(text="✅ Authenticated", fg='green')
            messagebox.showinfo("Success", "Successfully authenticated with YouTube!")
        except Exception as e:
            messagebox.showerror("Error", f"Authentication failed: {str(e)}")
    
    def get_authenticated_service(self, client_secret_file):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build("youtube", "v3", credentials=creds)
    
    def select_video_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv")]
        )
        if file_path:
            self.video_file = file_path
            self.video_file_label.config(text=os.path.basename(file_path))
    
    def select_thumbnail(self):
        file_path = filedialog.askopenfilename(
            title="Select Thumbnail",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            self.thumbnail_file = file_path
            self.thumbnail_label.config(text=os.path.basename(file_path))
    
    def select_metadata_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Metadata JSON",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    metadata = json.load(file)
                
                self.videos_list = metadata.get("videos", [])
                self.metadata_label.config(text=os.path.basename(file_path))
                
                # Update listbox
                self.videos_listbox.delete(0, END)
                for i, video in enumerate(self.videos_list):
                    self.videos_listbox.insert(END, f"{i+1}. {video.get('title', 'Untitled')}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load metadata: {str(e)}")
    
    def upload_single_video(self):
        if not self.youtube_service:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        if not self.video_file:
            messagebox.showerror("Error", "Please select a video file!")
            return
        
        if not self.title_entry.get().strip():
            messagebox.showerror("Error", "Please enter a title!")
            return
        
        # Disable upload button
        self.upload_btn.config(state='disabled')
        
        # Start upload in separate thread
        threading.Thread(target=self.perform_single_upload, daemon=True).start()
    
    def perform_single_upload(self):
        try:
            # Prepare video data
            video_data = {
                "videoFile": self.video_file,
                "title": self.title_entry.get().strip(),
                "description": self.description_text.get(1.0, END).strip(),
                "tags": [tag.strip() for tag in self.tags_entry.get().split(',') if tag.strip()],
                "categoryName": self.category_var.get(),
                "privacyStatus": self.privacy_var.get(),
                "madeForKids": self.kids_var.get(),
                "playlistName": self.playlist_entry.get().strip() if self.playlist_entry.get().strip() else None
            }
            
            if self.thumbnail_file:
                video_data["thumbnail"] = self.thumbnail_file
            
            if self.schedule_var.get():
                date_str = self.date_entry.get().strip()
                time_str = self.time_entry.get().strip()
                if date_str and time_str:
                    video_data["publishAt"] = f"{date_str} {time_str}"
            
            # Upload video
            self.upload_video_with_progress(video_data)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Upload failed: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.upload_btn.config(state='normal'))
    
    def upload_video_with_progress(self, video_data):
        try:
            self.root.after(0, lambda: self.progress_var.set(f"📤 Uploading: {video_data['title']}"))
            
            category_id = CATEGORY_MAP.get(video_data["categoryName"], "22")
            
            request_body = {
                "snippet": {
                    "title": video_data["title"],
                    "description": video_data["description"],
                    "tags": video_data.get("tags", []),
                    "categoryId": category_id,
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en"
                },
                "status": {
                    "privacyStatus": video_data["privacyStatus"],
                    "selfDeclaredMadeForKids": video_data.get("madeForKids", False),
                    "embeddable": True,
                    "publicStatsViewable": True,
                }
            }
            
            if video_data.get("publishAt"):
                utc_publish_time = self.convert_ist_to_utc(video_data["publishAt"])
                request_body["status"]["publishAt"] = utc_publish_time
                request_body["status"]["privacyStatus"] = "private"
            
            media = MediaFileUpload(video_data["videoFile"], chunksize=-1, resumable=True)
            request = self.youtube_service.videos().insert(
                part="snippet,status",
                body=request_body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.root.after(0, lambda p=progress: self.progress_bar.config(value=p))
                    self.root.after(0, lambda p=progress: self.progress_var.set(f"🚀 Upload Progress: {p}%"))
            
            video_id = response["id"]
            
            # Upload thumbnail if provided
            if "thumbnail" in video_data and video_data["thumbnail"]:
                self.upload_thumbnail(video_id, video_data["thumbnail"])
            
            # Add to playlist if specified
            if video_data.get("playlistName"):
                playlist_id = self.get_playlist_id(video_data["playlistName"])
                self.add_video_to_playlist(video_id, playlist_id)
            
            self.root.after(0, lambda: self.progress_var.set(f"✅ Successfully uploaded: {video_data['title']}"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Video uploaded successfully!\nVideo ID: {video_id}"))
            
        except Exception as e:
            self.root.after(0, lambda: self.progress_var.set(f"❌ Upload failed: {str(e)}"))
            raise e
    
    def upload_batch_videos(self):
        if not self.youtube_service:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        if not self.videos_list:
            messagebox.showerror("Error", "Please select a metadata file with videos!")
            return
        
        # Start batch upload in separate thread
        threading.Thread(target=self.perform_batch_upload, daemon=True).start()
    
    def perform_batch_upload(self):
        total_videos = len(self.videos_list)
        
        for i, video_data in enumerate(self.videos_list):
            try:
                self.root.after(0, lambda i=i, total=total_videos: 
                               self.batch_progress_var.set(f"Uploading video {i+1} of {total}"))
                
                self.upload_video_with_batch_progress(video_data, i, total_videos)
                
                # Wait between uploads
                time.sleep(10)
                
            except Exception as e:
                self.root.after(0, lambda e=e, i=i: 
                               messagebox.showerror("Error", f"Failed to upload video {i+1}: {str(e)}"))
        
        self.root.after(0, lambda: self.batch_progress_var.set("✅ Batch upload completed!"))
        self.root.after(0, lambda: messagebox.showinfo("Success", "Batch upload completed!"))
    
    def upload_video_with_batch_progress(self, video_data, current_index, total_videos):
        # Similar to upload_video_with_progress but updates batch progress
        progress = ((current_index + 1) / total_videos) * 100
        self.root.after(0, lambda: self.batch_progress_bar.config(value=progress))
        
        # Use existing upload logic
        self.upload_video_with_progress(video_data)
    
    def convert_ist_to_utc(self, ist_time_str):
        ist = pytz.timezone("Asia/Kolkata")
        local_time = datetime.strptime(ist_time_str, "%Y-%m-%d %H:%M:%S")
        local_time = ist.localize(local_time)
        utc_time = local_time.astimezone(pytz.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def get_playlist_id(self, playlist_name):
        request = self.youtube_service.playlists().list(part="snippet", mine=True, maxResults=50)
        response = request.execute()
        for playlist in response.get("items", []):
            if playlist["snippet"]["title"] == playlist_name:
                return playlist["id"]
        
        # Create new playlist
        create_request = self.youtube_service.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_name,
                    "description": f"Playlist for {playlist_name}",
                    "defaultLanguage": "en"
                },
                "status": {"privacyStatus": "public"}
            }
        )
        return create_request.execute()["id"]
    
    def add_video_to_playlist(self, video_id, playlist_id):
        self.youtube_service.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}
                }
            }
        ).execute()
    
    def upload_thumbnail(self, video_id, thumbnail_path):
        if os.path.exists(thumbnail_path):
            self.youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()

if __name__ == "__main__":
    root = Tk()
    app = YouTubeUploaderGUI(root)
    root.mainloop()
