import os
import json
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import List, Dict, Optional, Any
import threading
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
from datetime import datetime

class YouTubePlaylistManager:
    """
    Comprehensive YouTube Playlist Management Tool
    
    Features:
    - Create, update, delete playlists
    - Add/remove videos from playlists
    - Reorder videos within playlists
    - Export playlist data to CSV/JSON
    - Batch operations for multiple videos
    - Persistent authentication
    """
    
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.pickle"):
        """
        Initialize the YouTube API client
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store authentication tokens
        """
        self.SCOPES = ['https://www.googleapis.com/auth/youtube']
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.youtube = None
        self._authenticated = False
    
    def authenticate(self):
        """
        Authenticate with YouTube API using OAuth2 or service account
        Returns authenticated YouTube service object
        """
        if self._authenticated and self.youtube:
            return self.youtube
            
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if os.path.exists(self.credentials_file):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise FileNotFoundError(f"Credentials file '{self.credentials_file}' not found")
            
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        self._authenticated = True
        return self.youtube
    
    def create_playlist(self, title: str, description: str = "", privacy_status: str = "private") -> Dict[str, Any]:
        """Create a new YouTube playlist"""
        try:
            request = self.youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description
                    },
                    "status": {
                        "privacyStatus": privacy_status
                    }
                }
            )
            response = request.execute()
            
            playlist_info = {
                "id": response["id"],
                "title": response["snippet"]["title"],
                "description": response["snippet"]["description"],
                "privacy_status": response["status"]["privacyStatus"],
                "created": response["snippet"]["publishedAt"]
            }
            
            return playlist_info
            
        except Exception as e:
            raise Exception(f"Error creating playlist: {e}")
    
    def get_playlists(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get all playlists for the authenticated user"""
        try:
            playlists = []
            next_page_token = None
            
            while True:
                request = self.youtube.playlists().list(
                    part="snippet,status,contentDetails",
                    mine=True,
                    maxResults=min(max_results, 50),
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for item in response["items"]:
                    playlist_info = {
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"]["description"],
                        "privacy_status": item["status"]["privacyStatus"],
                        "video_count": item["contentDetails"]["itemCount"],
                        "created": item["snippet"]["publishedAt"]
                    }
                    playlists.append(playlist_info)
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(playlists) >= max_results:
                    break
            
            return playlists[:max_results]
            
        except Exception as e:
            raise Exception(f"Error retrieving playlists: {e}")
    
    def update_playlist(self, playlist_id: str, title: str = None, description: str = None, 
                       privacy_status: str = None) -> bool:
        """Update an existing playlist"""
        try:
            current = self.youtube.playlists().list(
                part="snippet,status",
                id=playlist_id
            ).execute()
            
            if not current["items"]:
                raise Exception(f"Playlist {playlist_id} not found")
            
            current_item = current["items"][0]
            snippet = current_item["snippet"]
            status = current_item["status"]
            
            if title is not None:
                snippet["title"] = title
            if description is not None:
                snippet["description"] = description
            if privacy_status is not None:
                status["privacyStatus"] = privacy_status
            
            request = self.youtube.playlists().update(
                part="snippet,status",
                body={
                    "id": playlist_id,
                    "snippet": snippet,
                    "status": status
                }
            )
            request.execute()
            return True
            
        except Exception as e:
            raise Exception(f"Error updating playlist: {e}")
    
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist"""
        try:
            request = self.youtube.playlists().delete(id=playlist_id)
            request.execute()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting playlist: {e}")
    
    def add_video_to_playlist(self, playlist_id: str, video_id: str, position: int = None) -> bool:
        """Add a video to a playlist"""
        try:
            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
            
            if position is not None:
                body["snippet"]["position"] = position
            
            request = self.youtube.playlistItems().insert(
                part="snippet",
                body=body
            )
            response = request.execute()
            return True
            
        except Exception as e:
            raise Exception(f"Error adding video to playlist: {e}")
    
    def add_multiple_videos_to_playlist(self, playlist_id: str, video_ids: List[str]) -> Dict[str, int]:
        """Add multiple videos to a playlist"""
        results = {"success": 0, "failed": 0, "failed_ids": []}
        
        for video_id in video_ids:
            try:
                self.add_video_to_playlist(playlist_id, video_id)
                results["success"] += 1
            except:
                results["failed"] += 1
                results["failed_ids"].append(video_id)
        
        return results
    
    def remove_video_from_playlist(self, playlist_id: str, video_id: str) -> bool:
        """Remove a video from a playlist"""
        try:
            playlist_items = self.get_playlist_videos(playlist_id)
            
            item_id = None
            for item in playlist_items:
                if item["video_id"] == video_id:
                    item_id = item["item_id"]
                    break
            
            if not item_id:
                raise Exception(f"Video {video_id} not found in playlist")
            
            request = self.youtube.playlistItems().delete(id=item_id)
            request.execute()
            return True
            
        except Exception as e:
            raise Exception(f"Error removing video from playlist: {e}")
    
    def get_playlist_videos(self, playlist_id: str, max_results: int = 500) -> List[Dict[str, Any]]:
        """Get all videos in a playlist"""
        try:
            videos = []
            next_page_token = None
            
            while True:
                request = self.youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=playlist_id,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for i, item in enumerate(response["items"]):
                    video_info = {
                        "item_id": item["id"],
                        "video_id": item["snippet"]["resourceId"]["videoId"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"]["description"],
                        "position": item["snippet"]["position"],
                        "added_date": item["snippet"]["publishedAt"],
                        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"]
                    }
                    videos.append(video_info)
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(videos) >= max_results:
                    break
            
            return videos[:max_results]
            
        except Exception as e:
            raise Exception(f"Error retrieving playlist videos: {e}")
    
    def reorder_playlist_video(self, playlist_id: str, video_id: str, new_position: int) -> bool:
        """Change the position of a video within a playlist"""
        try:
            playlist_items = self.get_playlist_videos(playlist_id)
            
            item_to_move = None
            for item in playlist_items:
                if item["video_id"] == video_id:
                    item_to_move = item
                    break
            
            if not item_to_move:
                raise Exception(f"Video {video_id} not found in playlist")
            
            request = self.youtube.playlistItems().update(
                part="snippet",
                body={
                    "id": item_to_move["item_id"],
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        },
                        "position": new_position
                    }
                }
            )
            request.execute()
            return True
            
        except Exception as e:
            raise Exception(f"Error reordering video: {e}")
    
    def export_playlist_to_csv(self, playlist_id: str, filename: str = None) -> str:
        """Export playlist data to CSV file"""
        try:
            videos = self.get_playlist_videos(playlist_id)
            
            if not filename:
                playlist_info = self.youtube.playlists().list(
                    part="snippet",
                    id=playlist_id
                ).execute()
                
                playlist_title = playlist_info["items"][0]["snippet"]["title"]
                filename = f"{playlist_title.replace(' ', '_')}_{playlist_id}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['position', 'video_id', 'title', 'description', 'added_date', 'thumbnail']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for video in videos:
                    writer.writerow({
                        'position': video['position'],
                        'video_id': video['video_id'],
                        'title': video['title'],
                        'description': video['description'][:200] + '...' if len(video['description']) > 200 else video['description'],
                        'added_date': video['added_date'],
                        'thumbnail': video['thumbnail']
                    })
            
            return filename
            
        except Exception as e:
            raise Exception(f"Error exporting to CSV: {e}")
    
    def export_playlist_to_json(self, playlist_id: str, filename: str = None) -> str:
        """Export playlist data to JSON file"""
        try:
            videos = self.get_playlist_videos(playlist_id)
            
            playlist_info = self.youtube.playlists().list(
                part="snippet,status,contentDetails",
                id=playlist_id
            ).execute()
            
            if not playlist_info["items"]:
                raise Exception(f"Playlist {playlist_id} not found")
            
            playlist_data = playlist_info["items"][0]
            
            export_data = {
                "playlist_info": {
                    "id": playlist_data["id"],
                    "title": playlist_data["snippet"]["title"],
                    "description": playlist_data["snippet"]["description"],
                    "privacy_status": playlist_data["status"]["privacyStatus"],
                    "video_count": playlist_data["contentDetails"]["itemCount"],
                    "created": playlist_data["snippet"]["publishedAt"]
                },
                "videos": videos,
                "export_timestamp": datetime.now().isoformat()
            }
            
            if not filename:
                playlist_title = playlist_data["snippet"]["title"]
                filename = f"{playlist_title.replace(' ', '_')}_{playlist_id}.json"
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
            
            return filename
            
        except Exception as e:
            raise Exception(f"Error exporting to JSON: {e}")
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for videos on YouTube"""
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results
            )
            response = request.execute()
            
            videos = []
            for item in response["items"]:
                video_info = {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "channel": item["snippet"]["channelTitle"],
                    "published": item["snippet"]["publishedAt"],
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"]
                }
                videos.append(video_info)
            
            return videos
            
        except Exception as e:
            raise Exception(f"Error searching videos: {e}")


class YouTubePlaylistGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Playlist Manager")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize YouTube manager
        self.manager = YouTubePlaylistManager()
        self.current_playlist_id = None
        self.playlists = []
        self.videos = []
        
        # Setup GUI
        self.setup_gui()
        
        # Initialize authentication
        self.authenticate()
    
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎵 YouTube Playlist Manager", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Left panel - Playlists
        left_frame = ttk.LabelFrame(main_frame, text="Playlists", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.rowconfigure(1, weight=1)
        
        # Playlist buttons
        playlist_buttons_frame = ttk.Frame(left_frame)
        playlist_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(playlist_buttons_frame, text="➕ Create Playlist", 
                  command=self.create_playlist_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_buttons_frame, text="🔄 Refresh", 
                  command=self.refresh_playlists).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_buttons_frame, text="✏️ Edit", 
                  command=self.edit_playlist_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_buttons_frame, text="🗑️ Delete", 
                  command=self.delete_playlist).pack(side=tk.LEFT)
        
        # Playlists listbox
        playlist_frame = ttk.Frame(left_frame)
        playlist_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        playlist_frame.columnconfigure(0, weight=1)
        playlist_frame.rowconfigure(0, weight=1)
        
        self.playlist_listbox = tk.Listbox(playlist_frame, height=15)
        playlist_scrollbar = ttk.Scrollbar(playlist_frame, orient=tk.VERTICAL, command=self.playlist_listbox.yview)
        self.playlist_listbox.configure(yscrollcommand=playlist_scrollbar.set)
        
        self.playlist_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        playlist_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.playlist_listbox.bind('<<ListboxSelect>>', self.on_playlist_select)
        
        # Export buttons
        export_frame = ttk.Frame(left_frame)
        export_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(export_frame, text="💾 Export JSON", 
                  command=self.export_json).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="📊 Export CSV", 
                  command=self.export_csv).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="📁 Export All", 
                  command=self.export_all).pack(side=tk.LEFT)
        
        # Right panel - Videos
        right_frame = ttk.LabelFrame(main_frame, text="Videos", padding="10")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)
        
        # Video management buttons
        video_buttons_frame = ttk.Frame(right_frame)
        video_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(video_buttons_frame, text="🔍 Search & Add", 
                  command=self.search_and_add_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(video_buttons_frame, text="➕ Add Video ID", 
                  command=self.add_video_id_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(video_buttons_frame, text="➕ Batch Add", 
                  command=self.batch_add_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(video_buttons_frame, text="🗑️ Remove", 
                  command=self.remove_video).pack(side=tk.LEFT)
        
        # Reorder buttons
        reorder_frame = ttk.Frame(right_frame)
        reorder_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(reorder_frame, text="⬆️ Move Up", 
                  command=self.move_video_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(reorder_frame, text="⬇️ Move Down", 
                  command=self.move_video_down).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(reorder_frame, text="🔢 Set Position", 
                  command=self.set_video_position).pack(side=tk.LEFT, padx=(0, 5))
        
        # Videos treeview
        video_frame = ttk.Frame(right_frame)
        video_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        columns = ('Position', 'Title', 'Video ID')
        self.video_tree = ttk.Treeview(video_frame, columns=columns, show='headings', height=20)
        
        # Configure columns
        self.video_tree.heading('Position', text='Position')
        self.video_tree.heading('Title', text='Title')
        self.video_tree.heading('Video ID', text='Video ID')
        
        self.video_tree.column('Position', width=80, minwidth=50)
        self.video_tree.column('Title', width=400, minwidth=200)
        self.video_tree.column('Video ID', width=120, minwidth=100)
        
        video_scrollbar = ttk.Scrollbar(video_frame, orient=tk.VERTICAL, command=self.video_tree.yview)
        self.video_tree.configure(yscrollcommand=video_scrollbar.set)
        
        self.video_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        video_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def authenticate(self):
        """Authenticate with YouTube API"""
        def auth_worker():
            try:
                self.status_var.set("Authenticating...")
                self.manager.authenticate()
                self.status_var.set("Authentication successful")
                self.root.after(0, self.refresh_playlists)
            except Exception as e:
                self.status_var.set(f"Authentication failed: {str(e)}")
                messagebox.showerror("Authentication Error", 
                                   f"Failed to authenticate with YouTube API:\n{str(e)}\n\n"
                                   f"Make sure credentials.json file exists in the same directory.")
        
        threading.Thread(target=auth_worker, daemon=True).start()
    
    def refresh_playlists(self):
        """Refresh the playlists list"""
        def refresh_worker():
            try:
                self.status_var.set("Loading playlists...")
                self.playlists = self.manager.get_playlists()
                
                # Update UI in main thread
                self.root.after(0, self.update_playlist_listbox)
                self.status_var.set(f"Loaded {len(self.playlists)} playlists")
            except Exception as e:
                self.status_var.set(f"Error loading playlists: {str(e)}")
                messagebox.showerror("Error", f"Failed to load playlists:\n{str(e)}")
        
        threading.Thread(target=refresh_worker, daemon=True).start()
    
    def update_playlist_listbox(self):
        """Update the playlist listbox with current playlists"""
        self.playlist_listbox.delete(0, tk.END)
        for playlist in self.playlists:
            display_text = f"{playlist['title']} ({playlist['video_count']} videos)"
            self.playlist_listbox.insert(tk.END, display_text)
    
    def on_playlist_select(self, event):
        """Handle playlist selection"""
        selection = self.playlist_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_playlist_id = self.playlists[index]['id']
            self.load_playlist_videos()
    
    def load_playlist_videos(self):
        """Load videos for the selected playlist"""
        if not self.current_playlist_id:
            return
        
        def load_worker():
            try:
                self.status_var.set("Loading videos...")
                self.videos = self.manager.get_playlist_videos(self.current_playlist_id)
                
                # Update UI in main thread
                self.root.after(0, self.update_video_tree)
                self.status_var.set(f"Loaded {len(self.videos)} videos")
            except Exception as e:
                self.status_var.set(f"Error loading videos: {str(e)}")
                messagebox.showerror("Error", f"Failed to load videos:\n{str(e)}")
        
        threading.Thread(target=load_worker, daemon=True).start()
    
    def update_video_tree(self):
        """Update the video tree with current videos"""
        # Clear existing items
        for item in self.video_tree.get_children():
            self.video_tree.delete(item)
        
        # Add videos
        for video in self.videos:
            self.video_tree.insert('', 'end', values=(
                video['position'] + 1,  # Display 1-based position
                video['title'][:50] + '...' if len(video['title']) > 50 else video['title'],
                video['video_id']
            ))
    
    def create_playlist_dialog(self):
        """Show create playlist dialog"""
        dialog = PlaylistDialog(self.root, "Create Playlist")
        if dialog.result:
            title, description, privacy = dialog.result
            
            def create_worker():
                try:
                    self.status_var.set("Creating playlist...")
                    playlist = self.manager.create_playlist(title, description, privacy)
                    self.status_var.set(f"Created playlist: {title}")
                    self.root.after(0, self.refresh_playlists)
                    messagebox.showinfo("Success", f"Playlist '{title}' created successfully!")
                except Exception as e:
                    self.status_var.set(f"Error creating playlist: {str(e)}")
                    messagebox.showerror("Error", f"Failed to create playlist:\n{str(e)}")
            
            threading.Thread(target=create_worker, daemon=True).start()
    
    def edit_playlist_dialog(self):
        """Show edit playlist dialog"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        # Get current playlist data
        current_playlist = None
        for playlist in self.playlists:
            if playlist['id'] == self.current_playlist_id:
                current_playlist = playlist
                break
        
        if not current_playlist:
            return
        
        dialog = PlaylistDialog(self.root, "Edit Playlist", current_playlist)
        if dialog.result:
            title, description, privacy = dialog.result
            
            def update_worker():
                try:
                    self.status_var.set("Updating playlist...")
                    self.manager.update_playlist(self.current_playlist_id, title, description, privacy)
                    self.status_var.set("Playlist updated successfully")
                    self.root.after(0, self.refresh_playlists)
                    messagebox.showinfo("Success", "Playlist updated successfully!")
                except Exception as e:
                    self.status_var.set(f"Error updating playlist: {str(e)}")
                    messagebox.showerror("Error", f"Failed to update playlist:\n{str(e)}")
            
            threading.Thread(target=update_worker, daemon=True).start()
    
    def delete_playlist(self):
        """Delete the selected playlist"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        # Get playlist title for confirmation
        playlist_title = "the selected playlist"
        for playlist in self.playlists:
            if playlist['id'] == self.current_playlist_id:
                playlist_title = f"'{playlist['title']}'"
                break
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {playlist_title}?\n\nThis action cannot be undone."):
            def delete_worker():
                try:
                    self.status_var.set("Deleting playlist...")
                    self.manager.delete_playlist(self.current_playlist_id)
                    self.current_playlist_id = None
                    self.videos = []
                    self.status_var.set("Playlist deleted successfully")
                    self.root.after(0, self.refresh_playlists)
                    self.root.after(0, self.update_video_tree)
                    messagebox.showinfo("Success", "Playlist deleted successfully!")
                except Exception as e:
                    self.status_var.set(f"Error deleting playlist: {str(e)}")
                    messagebox.showerror("Error", f"Failed to delete playlist:\n{str(e)}")
            
            threading.Thread(target=delete_worker, daemon=True).start()
    
    def search_and_add_dialog(self):
        """Show search and add videos dialog"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        dialog = SearchDialog(self.root)
        if dialog.result:
            query, max_results = dialog.result
            
            def search_worker():
                try:
                    self.status_var.set(f"Searching for: {query}")
                    videos = self.manager.search_videos(query, max_results)
                    
                    if videos:
                        # Show search results dialog
                        self.root.after(0, lambda: self.show_search_results(videos))
                    else:
                        self.status_var.set("No videos found")
                        messagebox.showinfo("No Results", "No videos found for your search query.")
                except Exception as e:
                    self.status_var.set(f"Error searching: {str(e)}")
                    messagebox.showerror("Error", f"Failed to search videos:\n{str(e)}")
            
            threading.Thread(target=search_worker, daemon=True).start()
    
    def show_search_results(self, videos):
        """Show search results in a selection dialog"""
        dialog = SearchResultsDialog(self.root, videos)
        if dialog.selected_videos:
            video_ids = [video['video_id'] for video in dialog.selected_videos]
            self.add_videos_to_playlist(video_ids)
    
    def add_video_id_dialog(self):
        """Show add video by ID dialog"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        video_id = simpledialog.askstring("Add Video", "Enter YouTube Video ID or URL:")
        if video_id:
            # Extract video ID from URL if needed
            if 'youtube.com/watch?v=' in video_id:
                video_id = video_id.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in video_id:
                video_id = video_id.split('youtu.be/')[1].split('?')[0]
            
            self.add_videos_to_playlist([video_id])
    
    def batch_add_dialog(self):
        """Show batch add videos dialog"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        dialog = BatchAddDialog(self.root)
        if dialog.result:
            video_ids = dialog.result
            self.add_videos_to_playlist(video_ids)
    
    def add_videos_to_playlist(self, video_ids):
        """Add multiple videos to the current playlist"""
        def add_worker():
            try:
                self.status_var.set(f"Adding {len(video_ids)} videos...")
                results = self.manager.add_multiple_videos_to_playlist(self.current_playlist_id, video_ids)
                
                success_msg = f"Added {results['success']} videos successfully"
                if results['failed'] > 0:
                    success_msg += f", {results['failed']} failed"
                
                self.status_var.set(success_msg)
                self.root.after(0, self.load_playlist_videos)
                self.root.after(0, self.refresh_playlists)  # Update video count
                
                if results['failed'] > 0:
                    messagebox.showwarning("Partial Success", 
                                         f"{success_msg}\n\nFailed video IDs:\n" + 
                                         "\n".join(results['failed_ids']))
                else:
                    messagebox.showinfo("Success", success_msg)
                    
            except Exception as e:
                self.status_var.set(f"Error adding videos: {str(e)}")
                messagebox.showerror("Error", f"Failed to add videos:\n{str(e)}")
        
        threading.Thread(target=add_worker, daemon=True).start()
    
    def remove_video(self):
        """Remove selected video from playlist"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to remove.")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['values'][2]  # Video ID is in the third column
        
        if messagebox.askyesno("Confirm Remove", "Are you sure you want to remove this video from the playlist?"):
            def remove_worker():
                try:
                    self.status_var.set("Removing video...")
                    self.manager.remove_video_from_playlist(self.current_playlist_id, video_id)
                    self.status_var.set("Video removed successfully")
                    self.root.after(0, self.load_playlist_videos)
                    self.root.after(0, self.refresh_playlists)  # Update video count
                    messagebox.showinfo("Success", "Video removed successfully!")
                except Exception as e:
                    self.status_var.set(f"Error removing video: {str(e)}")
                    messagebox.showerror("Error", f"Failed to remove video:\n{str(e)}")
            
            threading.Thread(target=remove_worker, daemon=True).start()
    
    def move_video_up(self):
        """Move selected video up one position"""
        self.move_video(-1)
    
    def move_video_down(self):
        """Move selected video down one position"""
        self.move_video(1)
    
    def move_video(self, direction):
        """Move video up (-1) or down (1)"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to move.")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['values'][2]
        current_position = int(item['values'][0]) - 1  # Convert to 0-based
        new_position = current_position + direction
        
        if new_position < 0 or new_position >= len(self.videos):
            messagebox.showwarning("Warning", "Cannot move video beyond playlist boundaries.")
            return
        
        def move_worker():
            try:
                self.status_var.set("Moving video...")
                self.manager.reorder_playlist_video(self.current_playlist_id, video_id, new_position)
                self.status_var.set("Video moved successfully")
                self.root.after(0, self.load_playlist_videos)
            except Exception as e:
                self.status_var.set(f"Error moving video: {str(e)}")
                messagebox.showerror("Error", f"Failed to move video:\n{str(e)}")
        
        threading.Thread(target=move_worker, daemon=True).start()
    
    def set_video_position(self):
        """Set video to specific position"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to reposition.")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['values'][2]
        
        new_position = simpledialog.askinteger("Set Position", 
                                             f"Enter new position (1-{len(self.videos)}):",
                                             minvalue=1, maxvalue=len(self.videos))
        if new_position:
            new_position -= 1  # Convert to 0-based
            
            def move_worker():
                try:
                    self.status_var.set("Moving video...")
                    self.manager.reorder_playlist_video(self.current_playlist_id, video_id, new_position)
                    self.status_var.set("Video moved successfully")
                    self.root.after(0, self.load_playlist_videos)
                except Exception as e:
                    self.status_var.set(f"Error moving video: {str(e)}")
                    messagebox.showerror("Error", f"Failed to move video:\n{str(e)}")
            
            threading.Thread(target=move_worker, daemon=True).start()
    
    def export_json(self):
        """Export current playlist to JSON"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            def export_worker():
                try:
                    self.status_var.set("Exporting to JSON...")
                    result_file = self.manager.export_playlist_to_json(self.current_playlist_id, filename)
                    self.status_var.set(f"Exported to: {result_file}")
                    messagebox.showinfo("Success", f"Playlist exported to:\n{result_file}")
                except Exception as e:
                    self.status_var.set(f"Error exporting: {str(e)}")
                    messagebox.showerror("Error", f"Failed to export playlist:\n{str(e)}")
            
            threading.Thread(target=export_worker, daemon=True).start()
    
    def export_csv(self):
        """Export current playlist to CSV"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            def export_worker():
                try:
                    self.status_var.set("Exporting to CSV...")
                    result_file = self.manager.export_playlist_to_csv(self.current_playlist_id, filename)
                    self.status_var.set(f"Exported to: {result_file}")
                    messagebox.showinfo("Success", f"Playlist exported to:\n{result_file}")
                except Exception as e:
                    self.status_var.set(f"Error exporting: {str(e)}")
                    messagebox.showerror("Error", f"Failed to export playlist:\n{str(e)}")
            
            threading.Thread(target=export_worker, daemon=True).start()
    
    def export_all(self):
        """Export all playlists"""
        format_choice = messagebox.askyesnocancel("Export Format", 
                                                 "Choose export format:\n\nYes = JSON\nNo = CSV\nCancel = Cancel")
        
        if format_choice is None:  # Cancel
            return
        
        format_type = "json" if format_choice else "csv"
        
        def export_worker():
            try:
                self.status_var.set(f"Exporting all playlists to {format_type.upper()}...")
                
                exported_files = []
                for playlist in self.playlists:
                    try:
                        if format_type == "json":
                            filename = self.manager.export_playlist_to_json(playlist['id'])
                        else:
                            filename = self.manager.export_playlist_to_csv(playlist['id'])
                        
                        if filename:
                            exported_files.append(filename)
                    except Exception as e:
                        print(f"Failed to export {playlist['title']}: {e}")
                
                self.status_var.set(f"Exported {len(exported_files)} playlists")
                messagebox.showinfo("Success", f"Exported {len(exported_files)} playlists to {format_type.upper()} format")
                
            except Exception as e:
                self.status_var.set(f"Error exporting: {str(e)}")
                messagebox.showerror("Error", f"Failed to export playlists:\n{str(e)}")
        
        threading.Thread(target=export_worker, daemon=True).start()


class PlaylistDialog:
    def __init__(self, parent, title, playlist_data=None):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Title:").pack(anchor=tk.W)
        self.title_var = tk.StringVar(value=playlist_data['title'] if playlist_data else "")
        self.title_entry = ttk.Entry(main_frame, textvariable=self.title_var, width=50)
        self.title_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Description
        ttk.Label(main_frame, text="Description:").pack(anchor=tk.W)
        self.description_text = tk.Text(main_frame, height=6, width=50)
        if playlist_data:
            self.description_text.insert(tk.END, playlist_data['description'])
        self.description_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Privacy
        ttk.Label(main_frame, text="Privacy:").pack(anchor=tk.W)
        self.privacy_var = tk.StringVar(value=playlist_data['privacy_status'] if playlist_data else "private")
        privacy_frame = ttk.Frame(main_frame)
        privacy_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Radiobutton(privacy_frame, text="Private", variable=self.privacy_var, 
                       value="private").pack(side=tk.LEFT)
        ttk.Radiobutton(privacy_frame, text="Unlisted", variable=self.privacy_var, 
                       value="unlisted").pack(side=tk.LEFT, padx=(20, 0))
        ttk.Radiobutton(privacy_frame, text="Public", variable=self.privacy_var, 
                       value="public").pack(side=tk.LEFT, padx=(20, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Focus and bind
        self.title_entry.focus()
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def ok(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Warning", "Title is required!")
            return
        
        description = self.description_text.get(1.0, tk.END).strip()
        privacy = self.privacy_var.get()
        
        self.result = (title, description, privacy)
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()


class SearchDialog:
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Search Videos")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search query
        ttk.Label(main_frame, text="Search Query:").pack(anchor=tk.W)
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(main_frame, textvariable=self.query_var, width=50)
        self.query_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Max results
        ttk.Label(main_frame, text="Maximum Results:").pack(anchor=tk.W)
        self.max_results_var = tk.IntVar(value=10)
        max_results_frame = ttk.Frame(main_frame)
        max_results_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Scale(max_results_frame, from_=1, to=50, variable=self.max_results_var, 
                 orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(max_results_frame, textvariable=self.max_results_var).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Search", command=self.search).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Focus and bind
        self.query_entry.focus()
        self.dialog.bind('<Return>', lambda e: self.search())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def search(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Search query is required!")
            return
        
        max_results = self.max_results_var.get()
        self.result = (query, max_results)
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()


class SearchResultsDialog:
    def __init__(self, parent, videos):
        self.selected_videos = []
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Search Results")
        self.dialog.geometry("800x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        ttk.Label(main_frame, text="Select videos to add to playlist:").pack(anchor=tk.W, pady=(0, 10))
        
        # Results frame
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for results
        columns = ('Select', 'Title', 'Channel', 'Video ID')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        self.results_tree.heading('Select', text='✓')
        self.results_tree.heading('Title', text='Title')
        self.results_tree.heading('Channel', text='Channel')
        self.results_tree.heading('Video ID', text='Video ID')
        
        self.results_tree.column('Select', width=30, minwidth=30)
        self.results_tree.column('Title', width=400, minwidth=200)
        self.results_tree.column('Channel', width=150, minwidth=100)
        self.results_tree.column('Video ID', width=120, minwidth=100)
        
        # Add videos to tree
        for video in videos:
            self.results_tree.insert('', 'end', values=(
                '',  # Empty select column
                video['title'][:60] + '...' if len(video['title']) > 60 else video['title'],
                video['channel'],
                video['video_id']
            ))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to toggle selection
        self.results_tree.bind('<Double-1>', self.toggle_selection)
        
        # Selection tracking
        self.selected_items = set()
        self.videos = videos
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Add Selected", command=self.add_selected).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def toggle_selection(self, event):
        item = self.results_tree.selection()[0]
        if item in self.selected_items:
            self.selected_items.remove(item)
            self.results_tree.set(item, 'Select', '')
        else:
            self.selected_items.add(item)
            self.results_tree.set(item, 'Select', '✓')
    
    def select_all(self):
        for item in self.results_tree.get_children():
            self.selected_items.add(item)
            self.results_tree.set(item, 'Select', '✓')
    
    def clear_all(self):
        for item in self.results_tree.get_children():
            self.selected_items.discard(item)
            self.results_tree.set(item, 'Select', '')
    
    def add_selected(self):
        if not self.selected_items:
            messagebox.showwarning("Warning", "Please select at least one video!")
            return
        
        # Get selected videos
        for item in self.selected_items:
            values = self.results_tree.item(item)['values']
            video_id = values[3]
            
            # Find the corresponding video data
            for video in self.videos:
                if video['video_id'] == video_id:
                    self.selected_videos.append(video)
                    break
        
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()


class BatchAddDialog:
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Add Videos")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                               text="Enter video IDs or URLs (one per line):\n" +
                                    "Supports: Video IDs, youtube.com/watch?v=..., youtu.be/...")
        instructions.pack(anchor=tk.W, pady=(0, 10))
        
        # Text area
        self.text_area = tk.Text(main_frame, height=15, width=60)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollbar for text area
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Add Videos", command=self.add_videos).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Focus
        self.text_area.focus()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def add_videos(self):
        content = self.text_area.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "Please enter at least one video ID or URL!")
            return
        
        lines = content.split('\n')
        video_ids = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Extract video ID from different formats
            if 'youtube.com/watch?v=' in line:
                video_id = line.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in line:
                video_id = line.split('youtu.be/')[1].split('?')[0]
            else:
                video_id = line  # Assume it's already a video ID
            
            if video_id:
                video_ids.append(video_id)
        
        if not video_ids:
            messagebox.showwarning("Warning", "No valid video IDs found!")
            return
        
        self.result = video_ids
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()


def main():
    """Main function to run the YouTube Playlist Manager GUI"""
    root = tk.Tk()
    app = YouTubePlaylistGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()





    # please add the connection button for the authenication(but don't ask every time to autheticate), view playlist on youtube,particular video watch on youtube, total views along with the view on the youtube videos and import the playlist functionality added in the above GUI. give me the final code