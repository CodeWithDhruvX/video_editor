import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import csv
import webbrowser
from datetime import datetime
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import threading
import pyperclip
import re

class YouTubePlaylistManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Playlist Manager")
        self.root.geometry("1400x900")  # Increased width to accommodate new panel
        
        # YouTube API setup
        self.youtube = None
        self.credentials = None
        self.scopes = ['https://www.googleapis.com/auth/youtube']
        
        # Data storage
        self.playlists = {}
        self.current_playlist_id = None
        self.current_playlist_items = {}  # Store playlist items with their IDs
        self.unassigned_videos = {}  # Store videos not in any playlist
        self.channel_videos = {}  # Store all channel videos
        
        # Setup GUI
        self.setup_gui()
        
        # Try to load existing credentials
        self.load_credentials()
        
    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for authentication and controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Authentication section
        auth_frame = ttk.LabelFrame(top_frame, text="Authentication", padding=10)
        auth_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(auth_frame, text="Load Credentials JSON", command=self.load_credentials_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(auth_frame, text="Authenticate", command=self.authenticate).pack(side=tk.LEFT, padx=(0, 5))
        
        self.auth_status = ttk.Label(auth_frame, text="Not Authenticated", foreground="red")
        self.auth_status.pack(side=tk.LEFT, padx=(10, 0))
        
        # Control buttons frame
        control_frame = ttk.LabelFrame(top_frame, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Playlist controls
        playlist_controls = ttk.Frame(control_frame)
        playlist_controls.pack(fill=tk.X)
        
        ttk.Label(playlist_controls, text="Playlist Controls:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(playlist_controls, text="Create Playlist", command=self.create_playlist).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_controls, text="Import Playlist", command=self.import_playlist).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_controls, text="Delete Playlist", command=self.delete_playlist).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(playlist_controls, text="Refresh Playlists", command=self.refresh_playlists).pack(side=tk.LEFT, padx=(0, 5))
        
        # Channel controls
        channel_controls = ttk.Frame(control_frame)
        channel_controls.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(channel_controls, text="Channel Controls:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(channel_controls, text="Load Channel Videos", command=self.load_channel_videos).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(channel_controls, text="Find Unassigned Videos", command=self.find_unassigned_videos).pack(side=tk.LEFT, padx=(0, 5))
        
        # Export buttons
        export_frame = ttk.Frame(control_frame)
        export_frame.pack(side=tk.RIGHT)
        ttk.Button(export_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="Export JSON", command=self.export_json).pack(side=tk.LEFT)
        
        # Main content area with notebook for tabs
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Playlist tab
        self.setup_playlist_tab()
        
        # Unassigned videos tab
        self.setup_unassigned_videos_tab()
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    def setup_playlist_tab(self):
        """Setup the playlist management tab"""
        playlist_frame = ttk.Frame(self.notebook)
        self.notebook.add(playlist_frame, text="Playlists")
        
        # Left panel - Playlists
        left_frame = ttk.LabelFrame(playlist_frame, text="Playlists", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Playlist listbox with scrollbar
        playlist_scroll_frame = ttk.Frame(left_frame)
        playlist_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.playlist_listbox = tk.Listbox(playlist_scroll_frame, width=30)
        playlist_scrollbar = ttk.Scrollbar(playlist_scroll_frame, orient=tk.VERTICAL, command=self.playlist_listbox.yview)
        self.playlist_listbox.configure(yscrollcommand=playlist_scrollbar.set)
        
        self.playlist_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        playlist_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlist_listbox.bind('<<ListboxSelect>>', self.on_playlist_select)
        
        # Playlist info with copy buttons
        info_frame = ttk.Frame(left_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.playlist_info = ttk.Label(info_frame, text="Select a playlist to view details")
        self.playlist_info.pack()
        
        # Copy buttons frame
        copy_frame = ttk.Frame(info_frame)
        copy_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(copy_frame, text="Copy ID", command=self.copy_playlist_id).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(copy_frame, text="Copy Title", command=self.copy_playlist_title).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(copy_frame, text="Copy URL", command=self.copy_playlist_url).pack(side=tk.LEFT)
        
        # View playlist on YouTube button
        ttk.Button(left_frame, text="View on YouTube", command=self.view_playlist_on_youtube).pack(pady=(5, 0))
        
        # Right panel - Videos
        right_frame = ttk.LabelFrame(playlist_frame, text="Videos", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Video controls
        video_control_frame = ttk.Frame(right_frame)
        video_control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # First row of controls
        control_row1 = ttk.Frame(video_control_frame)
        control_row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(control_row1, text="Add Video", command=self.add_video).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="Remove Video", command=self.remove_video).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="Remove Selected", command=self.remove_selected_videos).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="Move Up", command=self.move_video_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="Move Down", command=self.move_video_down).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="Watch Video", command=self.watch_video).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="Edit Video", command=self.edit_video_in_studio).pack(side=tk.LEFT, padx=(0, 5))
        
        # Second row of controls
        control_row2 = ttk.Frame(video_control_frame)
        control_row2.pack(fill=tk.X)
        
        ttk.Button(control_row2, text="Move to Playlist", command=self.move_to_playlist).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row2, text="Copy to Playlist", command=self.copy_to_playlist).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row2, text="Select All", command=self.select_all_videos).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row2, text="Select None", command=self.select_none_videos).pack(side=tk.LEFT)
        
        # Videos treeview
        video_frame = ttk.Frame(right_frame)
        video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for videos
        columns = ('Title', 'Channel', 'Duration', 'Views', 'Published')
        self.video_tree = ttk.Treeview(video_frame, columns=columns, show='tree headings', selectmode='extended')
        
        # Configure columns
        self.video_tree.heading('#0', text='#')
        self.video_tree.column('#0', width=50, minwidth=50)
        
        for col in columns:
            self.video_tree.heading(col, text=col)
            if col == 'Title':
                self.video_tree.column(col, width=300, minwidth=200)
            elif col == 'Channel':
                self.video_tree.column(col, width=150, minwidth=100)
            elif col == 'Views':
                self.video_tree.column(col, width=100, minwidth=80)
            else:
                self.video_tree.column(col, width=120, minwidth=80)
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(video_frame, orient=tk.VERTICAL, command=self.video_tree.yview)
        tree_scroll_x = ttk.Scrollbar(video_frame, orient=tk.HORIZONTAL, command=self.video_tree.xview)
        self.video_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.video_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_unassigned_videos_tab(self):
        """Setup the unassigned videos tab"""
        unassigned_frame = ttk.Frame(self.notebook)
        self.notebook.add(unassigned_frame, text="Unassigned Videos")
        
        # Top frame for controls
        control_frame = ttk.Frame(unassigned_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="Videos not in any playlist:", font=('TkDefaultFont', 12, 'bold')).pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Refresh", command=self.find_unassigned_videos).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Add to Playlist", command=self.add_unassigned_to_playlist).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Delete Video", command=self.delete_unassigned_video).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_unassigned_videos).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Edit Video", command=self.edit_unassigned_video).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Edit in Studio", command=self.edit_unassigned_video_in_studio).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Watch Video", command=self.watch_unassigned_video).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Select All", command=self.select_all_unassigned).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Select None", command=self.select_none_unassigned).pack(side=tk.LEFT)
        
        # Unassigned videos treeview
        unassigned_video_frame = ttk.Frame(unassigned_frame)
        unassigned_video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for unassigned videos
        columns = ('Title', 'Description', 'Duration', 'Views', 'Published', 'Privacy Status')
        self.unassigned_tree = ttk.Treeview(unassigned_video_frame, columns=columns, show='tree headings', selectmode='extended')
        
        # Configure columns
        self.unassigned_tree.heading('#0', text='#')
        self.unassigned_tree.column('#0', width=50, minwidth=50)
        
        for col in columns:
            self.unassigned_tree.heading(col, text=col)
            if col == 'Title':
                self.unassigned_tree.column(col, width=250, minwidth=200)
            elif col == 'Description':
                self.unassigned_tree.column(col, width=300, minwidth=150)
            elif col == 'Views':
                self.unassigned_tree.column(col, width=100, minwidth=80)
            else:
                self.unassigned_tree.column(col, width=120, minwidth=80)
        
        # Scrollbars for unassigned treeview
        unassigned_scroll_y = ttk.Scrollbar(unassigned_video_frame, orient=tk.VERTICAL, command=self.unassigned_tree.yview)
        unassigned_scroll_x = ttk.Scrollbar(unassigned_video_frame, orient=tk.HORIZONTAL, command=self.unassigned_tree.xview)
        self.unassigned_tree.configure(yscrollcommand=unassigned_scroll_y.set, xscrollcommand=unassigned_scroll_x.set)
        
        self.unassigned_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        unassigned_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        unassigned_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Info label
        self.unassigned_info = ttk.Label(unassigned_frame, text="Click 'Find Unassigned Videos' to scan your channel")
        self.unassigned_info.pack(pady=(10, 0))

    # NEW METHODS FOR EDIT VIDEO IN STUDIO FUNCTIONALITY
    def edit_video_in_studio(self):
        """Open selected video in YouTube Studio for editing"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to edit!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        
        if video_id:
            studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
            webbrowser.open(studio_url)
            self.update_status(f"Opened video in YouTube Studio for editing")
        else:
            messagebox.showerror("Error", "Could not get video ID!")

    def edit_unassigned_video_in_studio(self):
        """Open selected unassigned video in YouTube Studio for editing"""
        selection = self.unassigned_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to edit!")
            return
        
        item = self.unassigned_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        
        if video_id:
            studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
            webbrowser.open(studio_url)
            self.update_status(f"Opened video in YouTube Studio for editing")
        else:
            messagebox.showerror("Error", "Could not get video ID!")

    # EXISTING METHODS FOR MULTIPLE SELECTION FUNCTIONALITY
    def select_all_videos(self):
        """Select all videos in the current playlist"""
        for item in self.video_tree.get_children():
            self.video_tree.selection_add(item)

    def select_none_videos(self):
        """Deselect all videos in the current playlist"""
        for item in self.video_tree.selection():
            self.video_tree.selection_remove(item)

    def select_all_unassigned(self):
        """Select all unassigned videos"""
        for item in self.unassigned_tree.get_children():
            self.unassigned_tree.selection_add(item)

    def select_none_unassigned(self):
        """Deselect all unassigned videos"""
        for item in self.unassigned_tree.selection():
            self.unassigned_tree.selection_remove(item)

    def remove_selected_videos(self):
        """Remove multiple selected videos from playlist"""
        selections = self.video_tree.selection()
        if not selections:
            messagebox.showwarning("Warning", "Please select videos to remove!")
            return

        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return

        # Get video details for confirmation
        video_titles = []
        video_data = []
        
        for selection in selections:
            item = self.video_tree.item(selection)
            video_id = item['tags'][0] if item['tags'] else None
            video_title = item['values'][0] if item['values'] else "Unknown"
            
            if video_id and video_id in self.current_playlist_items:
                video_titles.append(video_title)
                video_data.append({
                    'id': video_id,
                    'title': video_title,
                    'playlist_item_id': self.current_playlist_items[video_id]['playlist_item_id']
                })

        if not video_data:
            messagebox.showerror("Error", "No valid videos selected!")
            return

        # Confirmation dialog
        if len(video_data) == 1:
            message = f"Are you sure you want to remove '{video_data[0]['title']}' from the playlist?"
        else:
            message = f"Are you sure you want to remove {len(video_data)} videos from the playlist?\n\nVideos to remove:\n"
            for i, video in enumerate(video_data[:5]):  # Show first 5 videos
                message += f"• {video['title']}\n"
            if len(video_data) > 5:
                message += f"... and {len(video_data) - 5} more videos"

        if messagebox.askyesno("Confirm Remove", message):
            def remove_videos():
                try:
                    self.update_status(f"Removing {len(video_data)} videos...")
                    success_count = 0
                    error_count = 0
                    
                    for video in video_data:
                        try:
                            request = self.youtube.playlistItems().delete(id=video['playlist_item_id'])
                            request.execute()
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            print(f"Error removing video '{video['title']}': {str(e)}")

                    # Show results
                    if error_count == 0:
                        messagebox.showinfo("Success", f"Successfully removed {success_count} videos from playlist!")
                    else:
                        messagebox.showwarning("Partial Success", 
                                             f"Removed {success_count} videos successfully.\n{error_count} videos failed to remove.")

                    # Reload playlist
                    self.load_playlist_videos(self.current_playlist_id)
                    self.update_status(f"Removed {success_count} videos from playlist")

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to remove videos: {str(e)}")
                    self.update_status("Error removing videos")

            threading.Thread(target=remove_videos, daemon=True).start()

    def delete_selected_unassigned_videos(self):
        """Delete multiple selected unassigned videos"""
        selections = self.unassigned_tree.selection()
        if not selections:
            messagebox.showwarning("Warning", "Please select videos to delete!")
            return

        # Get video details for confirmation
        video_data = []
        
        for selection in selections:
            item = self.unassigned_tree.item(selection)
            video_id = item['tags'][0] if item['tags'] else None
            video_title = item['values'][0] if item['values'] else "Unknown"
            
            if video_id:
                video_data.append({
                    'id': video_id,
                    'title': video_title
                })

        if not video_data:
            messagebox.showerror("Error", "No valid videos selected!")
            return

        # Confirmation dialog
        if len(video_data) == 1:
            message = f"Are you sure you want to permanently delete '{video_data[0]['title']}'?\n\nThis action cannot be undone!"
        else:
            message = f"Are you sure you want to permanently delete {len(video_data)} videos?\n\nThis action cannot be undone!\n\nVideos to delete:\n"
            for i, video in enumerate(video_data[:5]):  # Show first 5 videos
                message += f"• {video['title']}\n"
            if len(video_data) > 5:
                message += f"... and {len(video_data) - 5} more videos"

        if messagebox.askyesno("Confirm Delete", message):
            def delete_videos():
                try:
                    self.update_status(f"Deleting {len(video_data)} videos...")
                    success_count = 0
                    error_count = 0
                    
                    for video in video_data:
                        try:
                            request = self.youtube.videos().delete(id=video['id'])
                            request.execute()
                            
                            # Remove from local storage
                            if video['id'] in self.unassigned_videos:
                                del self.unassigned_videos[video['id']]
                            if video['id'] in self.channel_videos:
                                del self.channel_videos[video['id']]
                            
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            print(f"Error deleting video '{video['title']}': {str(e)}")

                    # Update display
                    self.display_unassigned_videos()

                    # Show results
                    if error_count == 0:
                        messagebox.showinfo("Success", f"Successfully deleted {success_count} videos!")
                    else:
                        messagebox.showwarning("Partial Success", 
                                             f"Deleted {success_count} videos successfully.\n{error_count} videos failed to delete.")

                    self.update_status(f"Deleted {success_count} videos")

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete videos: {str(e)}")
                    self.update_status("Error deleting videos")

            threading.Thread(target=delete_videos, daemon=True).start()

    # EXISTING METHODS CONTINUE HERE...
    def load_channel_videos(self):
        """Load all videos from the user's channel"""
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        def fetch_channel_videos():
            try:
                self.update_status("Loading channel videos...")
                self.channel_videos = {}
                
                # Get channel info
                channel_response = self.youtube.channels().list(
                    part="contentDetails",
                    mine=True
                ).execute()
                
                if not channel_response['items']:
                    messagebox.showerror("Error", "No channel found!")
                    return
                
                uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                # Get all videos from uploads playlist
                next_page_token = None
                video_count = 0
                
                while True:
                    request = self.youtube.playlistItems().list(
                        part="snippet,contentDetails",
                        playlistId=uploads_playlist_id,
                        maxResults=50,
                        pageToken=next_page_token
                    )
                    response = request.execute()
                    
                    video_ids = []
                    for item in response['items']:
                        video_id = item['contentDetails']['videoId']
                        video_ids.append(video_id)
                        self.channel_videos[video_id] = {
                            'title': item['snippet']['title'],
                            'description': item['snippet']['description'][:100] + '...' if len(item['snippet']['description']) > 100 else item['snippet']['description'],
                            'published': item['snippet']['publishedAt'][:10],
                        }
                    
                    # Get additional video details
                    if video_ids:
                        video_request = self.youtube.videos().list(
                            part="statistics,contentDetails,status",
                            id=','.join(video_ids)
                        )
                        video_response = video_request.execute()
                        
                        for video_item in video_response['items']:
                            video_id = video_item['id']
                            if video_id in self.channel_videos:
                                self.channel_videos[video_id].update({
                                    'duration': self.format_duration(video_item['contentDetails']['duration']),
                                    'views': f"{int(video_item['statistics'].get('viewCount', 0)):,}",
                                    'privacy_status': video_item['status']['privacyStatus']
                                })
                    
                    video_count += len(response['items'])
                    next_page_token = response.get('nextPageToken')
                    
                    if not next_page_token:
                        break
                
                self.update_status(f"Loaded {video_count} channel videos")
                messagebox.showinfo("Success", f"Loaded {video_count} videos from your channel!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load channel videos: {str(e)}")
                self.update_status("Error loading channel videos")
        
        threading.Thread(target=fetch_channel_videos, daemon=True).start()
    
    def find_unassigned_videos(self):
        """Find videos that are not in any playlist"""
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        if not self.channel_videos:
            if messagebox.askyesno("Channel Videos", "Channel videos not loaded. Load them first?"):
                self.load_channel_videos()
            return
        
        def find_unassigned():
            try:
                self.update_status("Finding unassigned videos...")
                
                # Get all playlist items
                playlist_video_ids = set()
                
                # First get all playlists if not already loaded
                if not self.playlists:
                    # Temporarily refresh playlists in this thread
                    request = self.youtube.playlists().list(
                        part="snippet,contentDetails",
                        mine=True,
                        maxResults=50
                    )
                    response = request.execute()
                    
                    temp_playlists = {}
                    for item in response['items']:
                        playlist_id = item['id']
                        temp_playlists[playlist_id] = {
                            'title': item['snippet']['title'],
                            'video_count': item['contentDetails']['itemCount'],
                            'description': item['snippet'].get('description', ''),
                            'published': item['snippet']['publishedAt']
                        }
                    
                    # Get video IDs from all playlists
                    for playlist_id in temp_playlists.keys():
                        try:
                            request = self.youtube.playlistItems().list(
                                part="contentDetails",
                                playlistId=playlist_id,
                                maxResults=50
                            )
                            response = request.execute()
                            
                            for item in response['items']:
                                playlist_video_ids.add(item['contentDetails']['videoId'])
                        except:
                            continue  # Skip if playlist is inaccessible
                else:
                    # Get video IDs from all playlists
                    for playlist_id in self.playlists.keys():
                        try:
                            request = self.youtube.playlistItems().list(
                                part="contentDetails",
                                playlistId=playlist_id,
                                maxResults=50
                            )
                            response = request.execute()
                            
                            for item in response['items']:
                                playlist_video_ids.add(item['contentDetails']['videoId'])
                        except:
                            continue  # Skip if playlist is inaccessible
                
                # Find videos not in any playlist
                self.unassigned_videos = {}
                for video_id, video_data in self.channel_videos.items():
                    if video_id not in playlist_video_ids:
                        self.unassigned_videos[video_id] = video_data
                
                # Update the unassigned videos display
                self.display_unassigned_videos()
                
                self.update_status(f"Found {len(self.unassigned_videos)} unassigned videos")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to find unassigned videos: {str(e)}")
                self.update_status("Error finding unassigned videos")
        
        threading.Thread(target=find_unassigned, daemon=True).start()
    
    def display_unassigned_videos(self):
        """Display unassigned videos in the treeview"""
        # Clear existing items
        for item in self.unassigned_tree.get_children():
            self.unassigned_tree.delete(item)
        
        # Add unassigned videos
        for i, (video_id, video_data) in enumerate(self.unassigned_videos.items()):
            self.unassigned_tree.insert('', 'end', text=str(i+1),
                                      values=(
                                          video_data.get('title', 'N/A'),
                                          video_data.get('description', 'N/A'),
                                          video_data.get('duration', 'N/A'),
                                          video_data.get('views', 'N/A'),
                                          video_data.get('published', 'N/A'),
                                          video_data.get('privacy_status', 'N/A')
                                      ),
                                      tags=(video_id,))
        
        self.unassigned_info.config(text=f"Found {len(self.unassigned_videos)} videos not in any playlist")
    
    def add_unassigned_to_playlist(self):
        """Add selected unassigned video to a playlist"""
        selection = self.unassigned_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to add to playlist!")
            return
        
        item = self.unassigned_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        video_title = item['values'][0] if item['values'] else "Unknown"
        
        if not video_id:
            messagebox.showerror("Error", "Could not get video ID!")
            return
        
        # Show playlist selection dialog
        self.show_playlist_selection_dialog(video_id, video_title, move=False, from_unassigned=True)
    
    def delete_unassigned_video(self):
        """Delete selected unassigned video"""
        selection = self.unassigned_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to delete!")
            return
        
        item = self.unassigned_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        video_title = item['values'][0] if item['values'] else "Unknown"
        
        if not video_id:
            messagebox.showerror("Error", "Could not get video ID!")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete '{video_title}'?\n\nThis action cannot be undone!"):
            def delete_video():
                try:
                    self.update_status("Deleting video...")
                    
                    request = self.youtube.videos().delete(id=video_id)
                    request.execute()
                    
                    # Remove from local storage
                    if video_id in self.unassigned_videos:
                        del self.unassigned_videos[video_id]
                    if video_id in self.channel_videos:
                        del self.channel_videos[video_id]
                    
                    self.display_unassigned_videos()
                    messagebox.showinfo("Success", "Video deleted successfully!")
                    self.update_status("Video deleted successfully")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete video: {str(e)}")
                    self.update_status("Error deleting video")
            
            threading.Thread(target=delete_video, daemon=True).start()
    
    def edit_unassigned_video(self):
        """Edit selected unassigned video details"""
        selection = self.unassigned_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to edit!")
            return
        
        item = self.unassigned_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        current_title = item['values'][0] if item['values'] else ""
        
        if not video_id:
            messagebox.showerror("Error", "Could not get video ID!")
            return
        
        # Create edit dialog
        self.show_video_edit_dialog(video_id, current_title)
    
    def show_video_edit_dialog(self, video_id, current_title):
        """Show dialog to edit video details"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Video")
        dialog.geometry("500x400")
        dialog.resizable(True, True)
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Title:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        title_entry = tk.Text(main_frame, height=2, wrap=tk.WORD)
        title_entry.pack(fill=tk.X, pady=(5, 10))
        title_entry.insert('1.0', current_title)
        
        # Description
        ttk.Label(main_frame, text="Description:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        desc_entry = tk.Text(main_frame, height=8, wrap=tk.WORD)
        desc_entry.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Privacy status
        privacy_frame = ttk.Frame(main_frame)
        privacy_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(privacy_frame, text="Privacy Status:", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        privacy_var = tk.StringVar(value="private")
        privacy_combo = ttk.Combobox(privacy_frame, textvariable=privacy_var, 
                                   values=["private", "public", "unlisted"], state="readonly")
        privacy_combo.pack(side=tk.RIGHT)
        
        # Load current video details
        def load_current_details():
            try:
                request = self.youtube.videos().list(
                    part="snippet,status",
                    id=video_id
                )
                response = request.execute()
                
                if response['items']:
                    video = response['items'][0]
                    desc_entry.insert('1.0', video['snippet'].get('description', ''))
                    privacy_var.set(video['status']['privacyStatus'])
                
            except Exception as e:
                self.update_status(f"Could not load video details: {str(e)}")
        
        load_current_details()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def on_save():
            new_title = title_entry.get('1.0', tk.END).strip()
            new_description = desc_entry.get('1.0', tk.END).strip()
            new_privacy = privacy_var.get()
            
            if not new_title:
                messagebox.showwarning("Warning", "Title cannot be empty!")
                return
            
            dialog.destroy()
            self.update_video_details(video_id, new_title, new_description, new_privacy)
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=on_save).pack(side=tk.RIGHT)
    
    def update_video_details(self, video_id, title, description, privacy_status):
        """Update video details using YouTube API"""
        def update_video():
            try:
                self.update_status("Updating video...")
                
                request = self.youtube.videos().update(
                    part="snippet,status",
                    body={
                        "id": video_id,
                        "snippet": {
                            "title": title,
                            "description": description,
                            "categoryId": "22"  # Default category
                        },
                        "status": {
                            "privacyStatus": privacy_status
                        }
                    }
                )
                response = request.execute()
                
                # Update local storage
                if video_id in self.unassigned_videos:
                    self.unassigned_videos[video_id]['title'] = title
                    self.unassigned_videos[video_id]['description'] = description[:100] + '...' if len(description) > 100 else description
                    self.unassigned_videos[video_id]['privacy_status'] = privacy_status
                
                if video_id in self.channel_videos:
                    self.channel_videos[video_id]['title'] = title
                    self.channel_videos[video_id]['description'] = description[:100] + '...' if len(description) > 100 else description
                    self.channel_videos[video_id]['privacy_status'] = privacy_status
                
                self.display_unassigned_videos()
                messagebox.showinfo("Success", "Video updated successfully!")
                self.update_status("Video updated successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update video: {str(e)}")
                self.update_status("Error updating video")
        
        threading.Thread(target=update_video, daemon=True).start()
    
    def watch_unassigned_video(self):
        """Open selected unassigned video on YouTube"""
        selection = self.unassigned_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to watch!")
            return
        
        item = self.unassigned_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        
        if video_id:
            webbrowser.open(f"https://www.youtube.com/watch?v={video_id}")
    
    def load_credentials_file(self):
        """Load credentials from JSON file"""
        file_path = filedialog.askopenfilename(
            title="Select Credentials JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.credentials_file = file_path
                self.update_status("Credentials file loaded. Click 'Authenticate' to proceed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load credentials file: {str(e)}")
    
    def load_credentials(self):
        """Load saved credentials if they exist"""
        if os.path.exists('token.json'):
            try:
                self.credentials = Credentials.from_authorized_user_file('token.json', self.scopes)
                if self.credentials and self.credentials.valid:
                    self.youtube = build('youtube', 'v3', credentials=self.credentials)
                    self.auth_status.config(text="Authenticated", foreground="green")
                    self.refresh_playlists()
                elif self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self.youtube = build('youtube', 'v3', credentials=self.credentials)
                    self.save_credentials()
                    self.auth_status.config(text="Authenticated", foreground="green")
                    self.refresh_playlists()
            except Exception as e:
                self.update_status(f"Error loading saved credentials: {str(e)}")
    
    def authenticate(self):
        """Authenticate with YouTube API"""
        if not hasattr(self, 'credentials_file'):
            messagebox.showerror("Error", "Please load credentials JSON file first!")
            return
        
        try:
            flow = Flow.from_client_secrets_file(self.credentials_file, self.scopes)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            webbrowser.open(auth_url)
            
            auth_code = simpledialog.askstring("Authentication", "Enter the authorization code:")
            
            if auth_code:
                flow.fetch_token(code=auth_code)
                self.credentials = flow.credentials
                self.youtube = build('youtube', 'v3', credentials=self.credentials)
                
                self.save_credentials()
                self.auth_status.config(text="Authenticated", foreground="green")
                self.update_status("Authentication successful!")
                self.refresh_playlists()
            
        except Exception as e:
            messagebox.showerror("Authentication Error", f"Failed to authenticate: {str(e)}")
    
    def save_credentials(self):
        """Save credentials to file"""
        with open('token.json', 'w') as token:
            token.write(self.credentials.to_json())
    
    def refresh_playlists(self):
        """Refresh playlists from YouTube"""
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        def fetch_playlists():
            try:
                self.update_status("Fetching playlists...")
                request = self.youtube.playlists().list(
                    part="snippet,contentDetails",
                    mine=True,
                    maxResults=50
                )
                response = request.execute()
                
                self.playlists = {}
                self.playlist_listbox.delete(0, tk.END)
                
                for item in response['items']:
                    playlist_id = item['id']
                    title = item['snippet']['title']
                    video_count = item['contentDetails']['itemCount']
                    
                    self.playlists[playlist_id] = {
                        'title': title,
                        'video_count': video_count,
                        'description': item['snippet'].get('description', ''),
                        'published': item['snippet']['publishedAt']
                    }
                    
                    display_text = f"{title} ({video_count} videos)"
                    self.playlist_listbox.insert(tk.END, display_text)
                
                self.update_status(f"Loaded {len(self.playlists)} playlists")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to fetch playlists: {str(e)}")
                self.update_status("Error fetching playlists")
        
        threading.Thread(target=fetch_playlists, daemon=True).start()
    
    def on_playlist_select(self, event):
        """Handle playlist selection"""
        selection = self.playlist_listbox.curselection()
        if selection:
            index = selection[0]
            playlist_id = list(self.playlists.keys())[index]
            self.current_playlist_id = playlist_id
            playlist = self.playlists[playlist_id]
            
            info_text = f"Title: {playlist['title']}\nVideos: {playlist['video_count']}\nCreated: {playlist['published'][:10]}"
            self.playlist_info.config(text=info_text)
            
            self.load_playlist_videos(playlist_id)
    
    def load_playlist_videos(self, playlist_id):
        """Load videos for selected playlist"""
        def fetch_videos():
            try:
                self.update_status("Loading videos...")
                
                # Clear existing videos
                for item in self.video_tree.get_children():
                    self.video_tree.delete(item)
                
                self.current_playlist_items = {}
                
                request = self.youtube.playlistItems().list(
                    part="snippet,contentDetails,id",
                    playlistId=playlist_id,
                    maxResults=50
                )
                response = request.execute()
                
                video_ids = []
                for item in response['items']:
                    video_id = item['contentDetails']['videoId']
                    playlist_item_id = item['id']
                    video_ids.append(video_id)
                    # Store playlist item ID for reordering
                    self.current_playlist_items[video_id] = {
                        'playlist_item_id': playlist_item_id,
                        'position': len(video_ids) - 1
                    }
                
                # Get video statistics
                if video_ids:
                    video_request = self.youtube.videos().list(
                        part="statistics,contentDetails,snippet",
                        id=','.join(video_ids)
                    )
                    video_response = video_request.execute()
                    video_stats = {item['id']: item for item in video_response['items']}
                
                for i, item in enumerate(response['items']):
                    video_id = item['contentDetails']['videoId']
                    snippet = item['snippet']
                    
                    title = snippet['title']
                    channel = snippet['channelTitle']
                    published = snippet['publishedAt'][:10]
                    
                    # Get video stats
                    stats = video_stats.get(video_id, {})
                    views = stats.get('statistics', {}).get('viewCount', 'N/A')
                    duration = stats.get('contentDetails', {}).get('duration', 'N/A')
                    
                    # Format views
                    if views != 'N/A':
                        views = f"{int(views):,}"
                    
                    # Format duration
                    if duration != 'N/A':
                        duration = self.format_duration(duration)
                    
                    self.video_tree.insert('', 'end', text=str(i+1), 
                                         values=(title, channel, duration, views, published),
                                         tags=(video_id,))
                
                self.update_status(f"Loaded {len(response['items'])} videos")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load videos: {str(e)}")
                self.update_status("Error loading videos")
        
        threading.Thread(target=fetch_videos, daemon=True).start()
    
    def format_duration(self, duration):
        """Format ISO 8601 duration to readable format"""
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return duration
        
        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0
        
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def move_video_up(self):
        """Move selected video up in playlist"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to move!")
            return
        
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        current_position = int(item['text']) - 1
        
        if current_position == 0:
            messagebox.showinfo("Info", "Video is already at the top!")
            return
        
        if video_id and video_id in self.current_playlist_items:
            self.move_video_to_position(video_id, current_position - 1)
    
    def move_video_down(self):
        """Move selected video down in playlist"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to move!")
            return
        
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        current_position = int(item['text']) - 1
        total_videos = len(self.video_tree.get_children())
        
        if current_position == total_videos - 1:
            messagebox.showinfo("Info", "Video is already at the bottom!")
            return
        
        if video_id and video_id in self.current_playlist_items:
            self.move_video_to_position(video_id, current_position + 1)
    
    def move_video_to_position(self, video_id, new_position):
        """Move video to specific position"""
        def move_video():
            try:
                self.update_status("Moving video...")
                
                playlist_item_id = self.current_playlist_items[video_id]['playlist_item_id']
                
                # Update the position using the YouTube API
                request = self.youtube.playlistItems().update(
                    part="snippet",
                    body={
                        "id": playlist_item_id,
                        "snippet": {
                            "playlistId": self.current_playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            },
                            "position": new_position
                        }
                    }
                )
                response = request.execute()
                
                # Reload the playlist to reflect changes
                self.load_playlist_videos(self.current_playlist_id)
                self.update_status("Video moved successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move video: {str(e)}")
                self.update_status("Error moving video")
        
        threading.Thread(target=move_video, daemon=True).start()
    
    def move_to_playlist(self):
        """Move selected video to another playlist"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to move!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        video_title = item['values'][0] if item['values'] else "Unknown"
        
        if not video_id:
            messagebox.showerror("Error", "Could not get video ID!")
            return
        
        # Create playlist selection dialog
        self.show_playlist_selection_dialog(video_id, video_title, move=True)
    
    def copy_to_playlist(self):
        """Copy selected video to another playlist"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to copy!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        video_title = item['values'][0] if item['values'] else "Unknown"
        
        if not video_id:
            messagebox.showerror("Error", "Could not get video ID!")
            return
        
        # Create playlist selection dialog
        self.show_playlist_selection_dialog(video_id, video_title, move=False)
    
    def show_playlist_selection_dialog(self, video_id, video_title, move=False, from_unassigned=False):
        """Show dialog to select target playlist"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{'Move' if move else 'Add'} Video to Playlist")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Video info
        info_frame = ttk.Frame(dialog, padding=10)
        info_frame.pack(fill=tk.X)
        
        action_text = "Moving" if move else "Adding"
        ttk.Label(info_frame, text=f"{action_text} video:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        ttk.Label(info_frame, text=video_title, wraplength=350).pack(anchor=tk.W, pady=(5, 10))
        
        # Playlist selection
        ttk.Label(info_frame, text="Select target playlist:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        
        # Playlist listbox
        list_frame = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        playlist_list = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=playlist_list.yview)
        playlist_list.configure(yscrollcommand=scrollbar.set)
        
        playlist_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate playlist list
        playlist_ids = []
        for playlist_id, playlist_data in self.playlists.items():
            if not from_unassigned and playlist_id == self.current_playlist_id:
                continue  # Skip current playlist if moving from playlist
            playlist_list.insert(tk.END, f"{playlist_data['title']} ({playlist_data['video_count']} videos)")
            playlist_ids.append(playlist_id)
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding=10)
        button_frame.pack(fill=tk.X)
        
        def on_confirm():
            selection = playlist_list.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a playlist!")
                return
            
            target_playlist_id = playlist_ids[selection[0]]
            target_playlist_title = self.playlists[target_playlist_id]['title']
            
            dialog.destroy()
            
            if move and not from_unassigned:
                self.execute_move_video(video_id, video_title, target_playlist_id, target_playlist_title)
            else:
                self.execute_copy_video(video_id, video_title, target_playlist_id, target_playlist_title, from_unassigned)
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text=f"{'Move' if move else 'Add'}", command=on_confirm).pack(side=tk.RIGHT)
    
    def execute_move_video(self, video_id, video_title, target_playlist_id, target_playlist_title):
        """Execute moving video to another playlist"""
        def move_video():
            try:
                self.update_status(f"Moving video to {target_playlist_title}...")
                
                # Add video to target playlist
                add_request = self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": target_playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                )
                add_request.execute()
                
                # Remove from current playlist
                if video_id in self.current_playlist_items:
                    playlist_item_id = self.current_playlist_items[video_id]['playlist_item_id']
                    delete_request = self.youtube.playlistItems().delete(id=playlist_item_id)
                    delete_request.execute()
                
                messagebox.showinfo("Success", f"Video moved to '{target_playlist_title}' successfully!")
                self.load_playlist_videos(self.current_playlist_id)
                self.update_status("Video moved successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move video: {str(e)}")
                self.update_status("Error moving video")
        
        threading.Thread(target=move_video, daemon=True).start()
    
    def execute_copy_video(self, video_id, video_title, target_playlist_id, target_playlist_title, from_unassigned=False):
        """Execute copying video to another playlist"""
        def copy_video():
            try:
                self.update_status(f"Adding video to {target_playlist_title}...")
                
                # Add video to target playlist
                request = self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": target_playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                )
                response = request.execute()
                
                if from_unassigned:
                    # Remove from unassigned videos list
                    if video_id in self.unassigned_videos:
                        del self.unassigned_videos[video_id]
                    self.display_unassigned_videos()
                
                messagebox.showinfo("Success", f"Video added to '{target_playlist_title}' successfully!")
                self.update_status("Video added successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add video: {str(e)}")
                self.update_status("Error adding video")
        
        threading.Thread(target=copy_video, daemon=True).start()
    
    def copy_playlist_id(self):
        """Copy current playlist ID to clipboard"""
        if self.current_playlist_id:
            try:
                pyperclip.copy(self.current_playlist_id)
                self.update_status("Playlist ID copied to clipboard!")
            except:
                # Fallback if pyperclip is not available
                self.root.clipboard_clear()
                self.root.clipboard_append(self.current_playlist_id)
                self.update_status("Playlist ID copied to clipboard!")
        else:
            messagebox.showwarning("Warning", "Please select a playlist first!")
    
    def copy_playlist_title(self):
        """Copy current playlist title to clipboard"""
        if self.current_playlist_id:
            title = self.playlists[self.current_playlist_id]['title']
            try:
                pyperclip.copy(title)
                self.update_status("Playlist title copied to clipboard!")
            except:
                # Fallback if pyperclip is not available
                self.root.clipboard_clear()
                self.root.clipboard_append(title)
                self.update_status("Playlist title copied to clipboard!")
        else:
            messagebox.showwarning("Warning", "Please select a playlist first!")
    
    def copy_playlist_url(self):
        """Copy current playlist URL to clipboard"""
        if self.current_playlist_id:
            url = f"https://www.youtube.com/playlist?list={self.current_playlist_id}"
            try:
                pyperclip.copy(url)
                self.update_status("Playlist URL copied to clipboard!")
            except:
                # Fallback if pyperclip is not available
                self.root.clipboard_clear()
                self.root.clipboard_append(url)
                self.update_status("Playlist URL copied to clipboard!")
        else:
            messagebox.showwarning("Warning", "Please select a playlist first!")
    
    def create_playlist(self):
        """Create a new playlist"""
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        title = simpledialog.askstring("Create Playlist", "Enter playlist title:")
        if not title:
            return
        
        description = simpledialog.askstring("Create Playlist", "Enter playlist description (optional):") or ""
        
        try:
            request = self.youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description
                    },
                    "status": {
                        "privacyStatus": "private"
                    }
                }
            )
            response = request.execute()
            
            messagebox.showinfo("Success", f"Playlist '{title}' created successfully!")
            self.refresh_playlists()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create playlist: {str(e)}")
    
    def delete_playlist(self):
        """Delete selected playlist"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        playlist_title = self.playlists[self.current_playlist_id]['title']
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete playlist '{playlist_title}'?"):
            try:
                request = self.youtube.playlists().delete(id=self.current_playlist_id)
                request.execute()
                
                messagebox.showinfo("Success", f"Playlist '{playlist_title}' deleted successfully!")
                self.refresh_playlists()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete playlist: {str(e)}")
    
    def add_video(self):
        """Add video to current playlist"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        video_url = simpledialog.askstring("Add Video", "Enter YouTube video URL or ID:")
        if not video_url:
            return
        
        # Extract video ID from URL
        video_id = self.extract_video_id(video_url)
        if not video_id:
            messagebox.showerror("Error", "Invalid YouTube video URL or ID!")
            return
        
        try:
            request = self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": self.current_playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            )
            response = request.execute()
            
            messagebox.showinfo("Success", "Video added to playlist!")
            self.load_playlist_videos(self.current_playlist_id)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add video: {str(e)}")
    
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        if len(url) == 11 and url.isalnum():
            return url
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def remove_video(self):
        """Remove selected video from playlist"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to remove!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        video_title = item['values'][0] if item['values'] else "Unknown"
        
        if not video_id or video_id not in self.current_playlist_items:
            messagebox.showerror("Error", "Could not find video in playlist!")
            return
        
        if messagebox.askyesno("Confirm Remove", f"Are you sure you want to remove '{video_title}' from the playlist?"):
            try:
                playlist_item_id = self.current_playlist_items[video_id]['playlist_item_id']
                request = self.youtube.playlistItems().delete(id=playlist_item_id)
                request.execute()
                
                messagebox.showinfo("Success", "Video removed from playlist!")
                self.load_playlist_videos(self.current_playlist_id)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove video: {str(e)}")
    
    def watch_video(self):
        """Open selected video on YouTube"""
        selection = self.video_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a video to watch!")
            return
        
        item = self.video_tree.item(selection[0])
        video_id = item['tags'][0] if item['tags'] else None
        
        if video_id:
            webbrowser.open(f"https://www.youtube.com/watch?v={video_id}")
    
    def view_playlist_on_youtube(self):
        """Open current playlist on YouTube"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        webbrowser.open(f"https://www.youtube.com/playlist?list={self.current_playlist_id}")
    
    def import_playlist(self):
        """Import playlist from URL"""
        playlist_url = simpledialog.askstring("Import Playlist", "Enter YouTube playlist URL:")
        if not playlist_url:
            return
        
        # Extract playlist ID from URL
        playlist_id = self.extract_playlist_id(playlist_url)
        if not playlist_id:
            messagebox.showerror("Error", "Invalid YouTube playlist URL!")
            return
        
        try:
            # Get playlist details
            request = self.youtube.playlists().list(
                part="snippet",
                id=playlist_id
            )
            response = request.execute()
            
            if not response['items']:
                messagebox.showerror("Error", "Playlist not found or not accessible!")
                return
            
            playlist_title = response['items'][0]['snippet']['title']
            
            # Create new playlist
            new_title = simpledialog.askstring("Import Playlist", f"Enter title for imported playlist:", initialvalue=f"Imported - {playlist_title}")
            if not new_title:
                return
            
            create_request = self.youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": new_title,
                        "description": f"Imported from: {playlist_url}"
                    },
                    "status": {
                        "privacyStatus": "private"
                    }
                }
            )
            new_playlist = create_request.execute()
            new_playlist_id = new_playlist['id']
            
            # Get all videos from source playlist
            videos_request = self.youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50
            )
            videos_response = videos_request.execute()
            
            # Add videos to new playlist
            for item in videos_response['items']:
                video_id = item['contentDetails']['videoId']
                
                add_request = self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": new_playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                )
                add_request.execute()
            
            messagebox.showinfo("Success", f"Playlist imported successfully with {len(videos_response['items'])} videos!")
            self.refresh_playlists()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import playlist: {str(e)}")
    
    def extract_playlist_id(self, url):
        """Extract playlist ID from YouTube URL"""
        patterns = [
            r'list=([a-zA-Z0-9_-]+)',
            r'playlist\?list=([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def export_csv(self):
        """Export current playlist to CSV"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save CSV Export"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Position', 'Title', 'Channel', 'Duration', 'Views', 'Published', 'Video ID', 'Video URL'])
                    
                    for item in self.video_tree.get_children():
                        values = self.video_tree.item(item)
                        position = values['text']
                        title, channel, duration, views, published = values['values']
                        video_id = values['tags'][0] if values['tags'] else ''
                        video_url = f'https://www.youtube.com/watch?v={video_id}' if video_id else ''
                        
                        writer.writerow([position, title, channel, duration, views, published, video_id, video_url])
                
                messagebox.showinfo("Success", f"Playlist exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")
    
    def export_json(self):
        """Export current playlist to JSON"""
        if not self.current_playlist_id:
            messagebox.showwarning("Warning", "Please select a playlist first!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save JSON Export"
        )
        
        if file_path:
            try:
                export_data = {
                    'playlist_info': self.playlists[self.current_playlist_id],
                    'playlist_id': self.current_playlist_id,
                    'playlist_url': f'https://www.youtube.com/playlist?list={self.current_playlist_id}',
                    'exported_at': datetime.now().isoformat(),
                    'videos': []
                }
                
                for item in self.video_tree.get_children():
                    values = self.video_tree.item(item)
                    position = values['text']
                    title, channel, duration, views, published = values['values']
                    video_id = values['tags'][0] if values['tags'] else ''
                    
                    export_data['videos'].append({
                        'position': position,
                        'title': title,
                        'channel': channel,
                        'duration': duration,
                        'views': views,
                        'published': published,
                        'video_id': video_id,
                        'video_url': f'https://www.youtube.com/watch?v={video_id}' if video_id else ''
                    })
                
                with open(file_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Success", f"Playlist exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export JSON: {str(e)}")
    
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    # Install pyperclip if not available
    try:
        import pyperclip
    except ImportError:
        print("pyperclip not found. Install it with: pip install pyperclip")
        print("Clipboard functionality will use tkinter fallback.")
    
    app = YouTubePlaylistManager()
    app.run()