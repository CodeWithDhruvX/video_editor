import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
import os
import webbrowser
from datetime import datetime
import re
from collections import Counter, defaultdict
import sys
import pickle

# Check for required libraries
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    messagebox.showerror("Missing Dependencies", 
                        "Please install required packages:\npip install google-auth-oauthlib google-api-python-client")

class YouTubeCommentManager:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Comment Manager")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize variables
        self.youtube = None
        self.current_videos = []
        self.filtered_videos = []
        self.current_comments = []
        self.client_secrets_path = None
        self.current_video_id = None
        self.selected_video_data = None
        self.token_path = 'token.pickle'
        
        # Filter variables
        self.title_filter = tk.StringVar()
        self.views_filter = tk.StringVar()
        self.comments_filter = tk.StringVar()
        self.date_filter = tk.StringVar()
        
        # Bind filter variables to update function
        self.title_filter.trace('w', self.apply_filters)
        self.views_filter.trace('w', self.apply_filters)
        self.comments_filter.trace('w', self.apply_filters)
        self.date_filter.trace('w', self.apply_filters)
        
        # Create main interface
        self.create_widgets()
        if GOOGLE_API_AVAILABLE:
            self.load_saved_credentials()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Authentication section
        auth_section = ttk.LabelFrame(main_frame, text="Authentication", padding=10)
        auth_section.pack(fill='x', pady=(0, 10))
        
        ttk.Button(auth_section, text="🔑 Select client_secrets.json", 
                  command=self.select_client_secret_file).pack(side='left', padx=5)
        
        self.auth_status = ttk.Label(auth_section, text="❌ Not authenticated", foreground='red')
        self.auth_status.pack(side='left', padx=10)
        
        # NEW: Disconnect button
        ttk.Button(auth_section, text="❌ Disconnect", 
                  command=self.disconnect_youtube).pack(side='right', padx=5)
        
        # Video fetch controls
        fetch_section = ttk.LabelFrame(main_frame, text="Fetch Videos", padding=10)
        fetch_section.pack(fill='x', pady=(0, 10))
        
        controls_frame = ttk.Frame(fetch_section)
        controls_frame.pack(fill='x')
        
        ttk.Label(controls_frame, text="Max Results:").pack(side='left')
        self.max_videos_var = tk.StringVar(value="20")
        ttk.Spinbox(controls_frame, from_=5, to=50, textvariable=self.max_videos_var, width=10).pack(side='left', padx=5)
        
        ttk.Button(controls_frame, text="📺 Fetch Videos", 
                  command=self.fetch_videos_thread).pack(side='left', padx=10)
        
        self.video_progress = ttk.Progressbar(controls_frame, mode='indeterminate')
        self.video_progress.pack(side='right', padx=10)
        
        # Advanced Filters Section
        filters_section = ttk.LabelFrame(main_frame, text="Advanced Filters", padding=10)
        filters_section.pack(fill='x', pady=(0, 10))
        
        # Create filter frame with grid layout
        filter_frame = ttk.Frame(filters_section)
        filter_frame.pack(fill='x')
        
        # Title filter
        ttk.Label(filter_frame, text="Title:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        title_entry = ttk.Entry(filter_frame, textvariable=self.title_filter, width=20)
        title_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        
        # Views filter
        ttk.Label(filter_frame, text="Min Views:").grid(row=0, column=2, padx=5, pady=2, sticky='w')
        views_entry = ttk.Entry(filter_frame, textvariable=self.views_filter, width=15)
        views_entry.grid(row=0, column=3, padx=5, pady=2, sticky='ew')
        
        # Comments filter
        ttk.Label(filter_frame, text="Min Comments:").grid(row=0, column=4, padx=5, pady=2, sticky='w')
        comments_entry = ttk.Entry(filter_frame, textvariable=self.comments_filter, width=15)
        comments_entry.grid(row=0, column=5, padx=5, pady=2, sticky='ew')
        
        # Date filter (second row)
        ttk.Label(filter_frame, text="Published After:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        date_entry = ttk.Entry(filter_frame, textvariable=self.date_filter, width=20)
        date_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        ttk.Label(filter_frame, text="(YYYY-MM-DD)", font=('Arial', 8)).grid(row=1, column=2, padx=5, pady=2, sticky='w')
        
        # Clear filters button
        ttk.Button(filter_frame, text="🗑️ Clear Filters", 
                  command=self.clear_filters).grid(row=1, column=3, padx=5, pady=2)
        
        # Configure column weights for responsive design
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        
        # Videos section
        videos_section = ttk.LabelFrame(main_frame, text="My Videos", padding=10)
        videos_section.pack(fill='both', expand=True, pady=(0, 10))
        
        # Videos list with enhanced columns
        videos_container = ttk.Frame(videos_section)
        videos_container.pack(fill='both', expand=True)
        
        self.videos_tree = ttk.Treeview(videos_container, 
                                      columns=('Title', 'Duration', 'Published', 'Views', 'Comments'), 
                                      show='headings', height=10)
        
        self.videos_tree.heading('Title', text='Video Title')
        self.videos_tree.heading('Duration', text='Duration')
        self.videos_tree.heading('Published', text='Published')
        self.videos_tree.heading('Views', text='Views')
        self.videos_tree.heading('Comments', text='Comments')
        
        self.videos_tree.column('Title', width=450)
        self.videos_tree.column('Duration', width=80)
        self.videos_tree.column('Published', width=100)
        self.videos_tree.column('Views', width=100)
        self.videos_tree.column('Comments', width=80)
        
        videos_scrollbar = ttk.Scrollbar(videos_container, orient='vertical', command=self.videos_tree.yview)
        self.videos_tree.configure(yscrollcommand=videos_scrollbar.set)
        
        self.videos_tree.pack(side='left', fill='both', expand=True)
        videos_scrollbar.pack(side='right', fill='y')
        
        # Video action buttons
        action_frame = ttk.LabelFrame(main_frame, text="Video Actions", padding=10)
        action_frame.pack(fill='x', pady=(0, 10))
        
        # Left side buttons
        left_buttons = ttk.Frame(action_frame)
        left_buttons.pack(side='left')
        
        ttk.Button(left_buttons, text="📋 View Comments", 
                  command=self.view_comments).pack(side='left', padx=5)
        ttk.Button(left_buttons, text="📑 View All Comments", 
                  command=self.view_all_comments).pack(side='left', padx=5)
        ttk.Button(left_buttons, text="➕ Add Comment", 
                  command=self.add_comment).pack(side='left', padx=5)
        ttk.Button(left_buttons, text="✏️ Edit Comment", 
                  command=self.edit_comment).pack(side='left', padx=5)
        ttk.Button(left_buttons, text="🗑️ Delete Comment", 
                  command=self.delete_comment).pack(side='left', padx=5)
        
        # Right side buttons
        right_buttons = ttk.Frame(action_frame)
        right_buttons.pack(side='right')
        
        ttk.Button(right_buttons, text="📋 Copy Title", 
                  command=self.copy_video_title).pack(side='left', padx=5)
        ttk.Button(right_buttons, text="🔗 Open in YouTube", 
                  command=self.open_in_youtube).pack(side='left', padx=5)
        
        # Filter status
        self.filter_status = ttk.Label(action_frame, text="", font=('Arial', 9))
        self.filter_status.pack(pady=5)
        
        # Comments section for selected video
        comments_section = ttk.LabelFrame(main_frame, text="Comments", padding=10)
        comments_section.pack(fill='both', expand=True)
        
        # Selected video info
        self.video_info = ttk.Label(comments_section, text="Select a video to view comments", 
                                   font=('Arial', 10, 'bold'))
        self.video_info.pack(pady=(0, 10))
        
        # Comments list
        comments_container = ttk.Frame(comments_section)
        comments_container.pack(fill='both', expand=True)
        
        self.comments_tree = ttk.Treeview(comments_container, 
                                         columns=('Author', 'Comment', 'Likes', 'Published'), 
                                         show='headings', height=8)
        
        self.comments_tree.heading('Author', text='Author')
        self.comments_tree.heading('Comment', text='Comment')
        self.comments_tree.heading('Likes', text='👍 Likes')
        self.comments_tree.heading('Published', text='Published')
        
        self.comments_tree.column('Author', width=150)
        self.comments_tree.column('Comment', width=400)
        self.comments_tree.column('Likes', width=80)
        self.comments_tree.column('Published', width=120)
        
        comments_scrollbar = ttk.Scrollbar(comments_container, orient='vertical', command=self.comments_tree.yview)
        self.comments_tree.configure(yscrollcommand=comments_scrollbar.set)
        
        self.comments_tree.pack(side='left', fill='both', expand=True)
        comments_scrollbar.pack(side='right', fill='y')
        
        # Action log at bottom
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding=10)
        log_frame.pack(fill='x', pady=(10, 0))
        
        self.action_log = scrolledtext.ScrolledText(log_frame, height=6, wrap=tk.WORD)
        self.action_log.pack(fill='both', expand=True)
        
        # Bind events
        self.videos_tree.bind('<ButtonRelease-1>', self.on_video_select)
        self.comments_tree.bind('<ButtonRelease-1>', self.on_comment_select)
        
    def disconnect_youtube(self):
        """Completely sign out the user."""
        # Clear API object
        self.youtube = None
        
        # Clear current data
        self.current_videos = []
        self.filtered_videos = []
        self.current_comments = []
        self.selected_video_data = None
        self.current_video_id = None
        
        # Delete stored token
        try:
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
        except OSError:
            pass
            
        # Clear GUI displays
        for item in self.videos_tree.get_children():
            self.videos_tree.delete(item)
        for item in self.comments_tree.get_children():
            self.comments_tree.delete(item)
        
        # Reset video info
        self.video_info.config(text="Select a video to view comments")
        self.filter_status.config(text="")
        
        # Update auth status
        self.auth_status.config(text="❌ Not authenticated", foreground='red')
        
        messagebox.showinfo("Disconnected", "You have been signed out successfully.")
        self.log_action("🔌 Disconnected user (token removed)")
        
    def clear_filters(self):
        """Clear all filter fields"""
        self.title_filter.set("")
        self.views_filter.set("")
        self.comments_filter.set("")
        self.date_filter.set("")
        self.log_action("🗑️ Cleared all filters")
        
    def apply_filters(self, *args):
        """Apply filters to the video list"""
        if not self.current_videos:
            return
            
        filtered_videos = []
        
        # Get filter values
        title_filter = self.title_filter.get().lower()
        views_filter = self.views_filter.get()
        comments_filter = self.comments_filter.get()
        date_filter = self.date_filter.get()
        
        for video in self.current_videos:
            # Apply title filter
            if title_filter and title_filter not in video['title'].lower():
                continue
                
            # Apply views filter
            if views_filter:
                try:
                    min_views = int(views_filter)
                    if int(video['views']) < min_views:
                        continue
                except ValueError:
                    pass
                    
            # Apply comments filter
            if comments_filter:
                try:
                    min_comments = int(comments_filter)
                    if int(video['comments']) < min_comments:
                        continue
                except ValueError:
                    pass
                    
            # Apply date filter
            if date_filter:
                try:
                    filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                    video_date = datetime.strptime(video['published'], '%Y-%m-%d').date()
                    if video_date < filter_date:
                        continue
                except ValueError:
                    pass
                    
            filtered_videos.append(video)
            
        self.filtered_videos = filtered_videos
        self.update_video_display()
        
        # Update filter status
        total_videos = len(self.current_videos)
        filtered_count = len(filtered_videos)
        if filtered_count < total_videos:
            self.filter_status.config(text=f"Showing {filtered_count} of {total_videos} videos (filtered)")
        else:
            self.filter_status.config(text=f"Showing all {total_videos} videos")
        
    def copy_video_title(self):
        """Copy the selected video title to clipboard"""
        if not self.selected_video_data:
            messagebox.showwarning("Warning", "Please select a video first")
            return
            
        try:
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(self.selected_video_data['title'])
            self.root.update()  # Ensure clipboard is updated
            
            self.log_action(f"📋 Copied video title to clipboard: {self.selected_video_data['title'][:50]}...")
            messagebox.showinfo("Success", "Video title copied to clipboard!")
            
        except Exception as e:
            self.log_action(f"❌ Error copying title: {str(e)}")
            messagebox.showerror("Error", f"Failed to copy title: {str(e)}")
        
    def select_client_secret_file(self):
        if not GOOGLE_API_AVAILABLE:
            messagebox.showerror("Error", "Google API libraries not installed")
            return
            
        file_path = filedialog.askopenfilename(
            title="Select your client_secrets.json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            self.client_secrets_path = file_path
            self.save_credentials()
            self.authenticate_youtube()
            
    def save_credentials(self):
        if self.client_secrets_path:
            try:
                with open('app_config.json', 'w') as f:
                    json.dump({'client_secrets_path': self.client_secrets_path}, f)
            except Exception as e:
                self.log_action(f"Error saving credentials: {str(e)}")
                
    def load_saved_credentials(self):
        try:
            # Check for saved tokens first
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                    if creds and creds.valid:
                        self.youtube = build("youtube", "v3", credentials=creds)
                        self.auth_status.config(text="✅ Authenticated (from saved session)", foreground='green')
                        self.log_action("✅ Loaded saved authentication session")
                        return
                    elif creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            self.youtube = build("youtube", "v3", credentials=creds)
                            self.auth_status.config(text="✅ Authenticated (refreshed)", foreground='green')
                            self.log_action("✅ Refreshed authentication session")
                            # Save refreshed token
                            with open(self.token_path, 'wb') as token:
                                pickle.dump(creds, token)
                            return
                        except Exception as e:
                            self.log_action(f"Error refreshing token: {str(e)}")
            
            # Load client secrets path if available
            if os.path.exists('app_config.json'):
                with open('app_config.json', 'r') as f:
                    config = json.load(f)
                    self.client_secrets_path = config.get('client_secrets_path')
                    if self.client_secrets_path and os.path.exists(self.client_secrets_path):
                        self.log_action("Client secrets found, ready for authentication")
        except Exception as e:
            self.log_action(f"Error loading saved credentials: {str(e)}")
            
    def authenticate_youtube(self):
        if not GOOGLE_API_AVAILABLE:
            messagebox.showerror("Error", "Google API libraries not installed")
            return
            
        if not self.client_secrets_path:
            messagebox.showerror("Error", "Please select client_secrets.json file first")
            return
            
        try:
            SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                    
            # If there are no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_path, SCOPES)
                    creds = flow.run_local_server(port=8080)
                    
                # Save the credentials for the next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                    
            self.youtube = build("youtube", "v3", credentials=creds)
            
            self.auth_status.config(text="✅ Authenticated successfully", foreground='green')
            self.log_action("✅ YouTube API authenticated successfully")
            messagebox.showinfo("Success", "YouTube API authenticated successfully!")
            
        except Exception as e:
            self.auth_status.config(text="❌ Authentication failed", foreground='red')
            self.log_action(f"❌ Authentication failed: {str(e)}")
            messagebox.showerror("Authentication Error", f"Failed to authenticate: {str(e)}")
            
    def fetch_videos_thread(self):
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first")
            return
            
        threading.Thread(target=self.fetch_videos, daemon=True).start()
        
    def fetch_videos(self):
        try:
            self.root.after(0, self.video_progress.start)
            max_results = int(self.max_videos_var.get())
            
            # Get channel info first
            channels_response = self.youtube.channels().list(
                part="contentDetails",
                mine=True
            ).execute()
            
            if not channels_response['items']:
                self.root.after(0, messagebox.showerror, "Error", "No channel found for authenticated user")
                return
                
            upload_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=upload_playlist_id,
                maxResults=max_results
            ).execute()
            
            video_ids = []
            for item in playlist_response['items']:
                video_id = item['contentDetails']['videoId']
                video_ids.append(video_id)
                
            # Get video statistics and details
            if video_ids:
                stats_response = self.youtube.videos().list(
                    part="statistics,snippet,contentDetails",
                    id=','.join(video_ids)
                ).execute()
                
                self.current_videos = []
                
                for item in stats_response['items']:
                    # Parse duration
                    duration_str = item['contentDetails']['duration']
                    duration_seconds = self.parse_duration(duration_str)
                    
                    video_data = {
                        'id': item['id'],
                        'title': item['snippet']['title'],
                        'published': item['snippet']['publishedAt'][:10],
                        'views': item['statistics'].get('viewCount', '0'),
                        'likes': item['statistics'].get('likeCount', '0'),
                        'comments': item['statistics'].get('commentCount', '0'),
                        'duration': duration_seconds,
                        'duration_str': self.format_duration(duration_seconds)
                    }
                    
                    self.current_videos.append(video_data)
                
                # Apply any existing filters
                self.root.after(0, self.apply_filters)
                    
            self.log_action(f"📺 Fetched {len(self.current_videos)} videos")
            
        except Exception as e:
            error_msg = f"Error fetching videos: {str(e)}"
            self.root.after(0, messagebox.showerror, "Error", error_msg)
            self.log_action(f"❌ {error_msg}")
        finally:
            self.root.after(0, self.video_progress.stop)
            
    def parse_duration(self, duration_str):
        """Parse YouTube duration format (PT1M30S) to seconds"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        hours, minutes, seconds = match.groups()
        return (int(hours or 0) * 3600 + 
                int(minutes or 0) * 60 + 
                int(seconds or 0))
        
    def format_duration(self, seconds):
        """Format seconds to readable duration"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
            
    def update_video_display(self):
        # Clear existing videos
        for item in self.videos_tree.get_children():
            self.videos_tree.delete(item)
            
        # Use filtered videos if filters are applied, otherwise use all videos
        videos_to_show = self.filtered_videos if hasattr(self, 'filtered_videos') else self.current_videos
        
        # Populate videos
        for video in videos_to_show:
            self.videos_tree.insert('', 'end', values=(
                video['title'][:70] + "..." if len(video['title']) > 70 else video['title'],
                video['duration_str'],
                video['published'],
                video['views'],
                video['comments']
            ))
            
    def on_video_select(self, event=None):
        try:
            selection = self.videos_tree.selection()
            if selection:
                index = self.videos_tree.index(selection[0])
                
                # Use filtered videos if filters are applied
                videos_list = self.filtered_videos if hasattr(self, 'filtered_videos') else self.current_videos
                
                if index < len(videos_list):
                    self.selected_video_data = videos_list[index]
                    self.current_video_id = self.selected_video_data['id']
                    self.video_info.config(text=f"🎥 {self.selected_video_data['title']}")
                    
                    # Load comments for selected video
                    threading.Thread(target=self.fetch_comments, daemon=True).start()
        except Exception as e:
            self.log_action(f"Error selecting video: {str(e)}")
            
    def fetch_comments(self):
        try:
            if not self.current_video_id:
                return
                
            # Get comments
            request = self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=self.current_video_id,
                maxResults=50,
                textFormat="plainText",
                order="relevance"
            )
            
            response = request.execute()
            comments = []
            
            for item in response.get("items", []):
                comment_data = item["snippet"]["topLevelComment"]["snippet"]
                comment_info = {
                    'id': item['id'],
                    'video_id': self.current_video_id,
                    'author': comment_data["authorDisplayName"],
                    'text': comment_data["textDisplay"],
                    'likes': comment_data.get("likeCount", 0),
                    'published': comment_data["publishedAt"][:10],
                    'reply_count': item["snippet"]["totalReplyCount"]
                }
                comments.append(comment_info)
                    
            self.current_comments = comments
            self.root.after(0, self.update_comments_display)
            self.log_action(f"💬 Loaded {len(comments)} comments for selected video")
            
        except Exception as e:
            error_msg = f"Error fetching comments: {str(e)}"
            self.log_action(f"❌ {error_msg}")
            
    def update_comments_display(self):
        # Clear existing comments
        for item in self.comments_tree.get_children():
            self.comments_tree.delete(item)
            
        # Add new comments
        for comment in self.current_comments:
            display_text = comment['text'][:80] + "..." if len(comment['text']) > 80 else comment['text']
            display_text = display_text.replace('\n', ' ')
            
            self.comments_tree.insert('', 'end', values=(
                comment['author'],
                display_text,
                comment['likes'],
                comment['published']
            ))
            
    def on_comment_select(self, event=None):
        # This could be expanded to show comment details
        pass
        
    def view_comments(self):
        if not self.selected_video_data:
            messagebox.showwarning("Warning", "Please select a video first")
            return
            
        # Open a detailed comments window
        comments_window = tk.Toplevel(self.root)
        comments_window.title(f"Comments - {self.selected_video_data['title'][:50]}")
        comments_window.geometry("800x600")
        
        # Comments display
        comments_text = scrolledtext.ScrolledText(comments_window, wrap=tk.WORD)
        comments_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Populate comments
        if self.current_comments:
            for i, comment in enumerate(self.current_comments, 1):
                comments_text.insert(tk.END, f"{i}. {comment['author']} ({comment['likes']} likes)\n")
                comments_text.insert(tk.END, f"{comment['text']}\n")
                comments_text.insert(tk.END, f"Published: {comment['published']}\n\n")
        else:
            comments_text.insert(tk.END, "No comments loaded. Please select a video to load comments.")
            
        ttk.Button(comments_window, text="Close", command=comments_window.destroy).pack(pady=10)
        
    def view_all_comments(self):
        """View all comments from all videos with management options"""
        if not self.current_videos:
            messagebox.showwarning("Warning", "Please fetch videos first")
            return
            
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first")
            return
            
        # Create all comments window
        all_comments_window = tk.Toplevel(self.root)
        all_comments_window.title("All Comments Manager")
        all_comments_window.geometry("1200x700")
        all_comments_window.configure(bg='#f0f0f0')
        
        # Progress indicator
        progress_frame = ttk.Frame(all_comments_window)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        progress_label = ttk.Label(progress_frame, text="Loading comments from all videos...")
        progress_label.pack(side='left')
        
        progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress_bar.pack(side='right', padx=10)
        progress_bar.start()
        
        # Action buttons frame
        action_frame = ttk.LabelFrame(all_comments_window, text="Comment Actions", padding=10)
        action_frame.pack(fill='x', padx=10, pady=5)
        
        # Comment management buttons
        ttk.Button(action_frame, text="➕ Add Comment to Selected Video", 
                  command=lambda: self.add_comment_from_all_view(all_comments_tree)).pack(side='left', padx=5)
        ttk.Button(action_frame, text="✏️ Edit Selected Comment", 
                  command=lambda: self.edit_comment_from_all_view(all_comments_tree)).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🗑️ Delete Selected Comment", 
                  command=lambda: self.delete_comment_from_all_view(all_comments_tree)).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🔄 Refresh All Comments", 
                  command=lambda: self.refresh_all_comments(all_comments_tree, progress_label, progress_bar)).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🔗 Open Video in YouTube", 
                  command=lambda: self.open_video_from_comment(all_comments_tree)).pack(side='right', padx=5)
        
        # Comments display frame
        comments_frame = ttk.LabelFrame(all_comments_window, text="All Comments", padding=10)
        comments_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Comments treeview
        tree_container = ttk.Frame(comments_frame)
        tree_container.pack(fill='both', expand=True)
        
        all_comments_tree = ttk.Treeview(tree_container, 
                                        columns=('Video', 'Author', 'Comment', 'Likes', 'Published'), 
                                        show='headings', height=20)
        
        all_comments_tree.heading('Video', text='Video Title')
        all_comments_tree.heading('Author', text='Author')
        all_comments_tree.heading('Comment', text='Comment')
        all_comments_tree.heading('Likes', text='👍 Likes')
        all_comments_tree.heading('Published', text='Published')
        
        all_comments_tree.column('Video', width=200)
        all_comments_tree.column('Author', width=120)
        all_comments_tree.column('Comment', width=350)
        all_comments_tree.column('Likes', width=80)
        all_comments_tree.column('Published', width=100)
        
        tree_scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=all_comments_tree.yview)
        all_comments_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        all_comments_tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')
        
        # Status label
        status_label = ttk.Label(all_comments_window, text="", font=('Arial', 9))
        status_label.pack(pady=5)
        
        # Store references for callback functions
        all_comments_window.all_comments_data = []
        
        # Start loading comments in background
        def load_all_comments():
            try:
                all_comments = []
                total_videos = len(self.current_videos)
                
                for i, video in enumerate(self.current_videos):
                    # Update progress
                    all_comments_window.after(0, lambda v=video, idx=i: progress_label.config(
                        text=f"Loading comments from: {v['title'][:40]}... ({idx+1}/{total_videos})"))
                    
                    try:
                        # Get comments for this video
                        request = self.youtube.commentThreads().list(
                            part="snippet,replies",
                            videoId=video['id'],
                            maxResults=50,
                            textFormat="plainText",
                            order="relevance"
                        )
                        
                        response = request.execute()
                        
                        for item in response.get("items", []):
                            comment_data = item["snippet"]["topLevelComment"]["snippet"]
                            comment_info = {
                                'comment_id': item['id'],
                                'video_id': video['id'],
                                'video_title': video['title'],
                                'author': comment_data["authorDisplayName"],
                                'text': comment_data["textDisplay"],
                                'likes': comment_data.get("likeCount", 0),
                                'published': comment_data["publishedAt"][:10],
                                'reply_count': item["snippet"]["totalReplyCount"]
                            }
                            all_comments.append(comment_info)
                            
                    except Exception as e:
                        print(f"Error loading comments for video {video['title']}: {str(e)}")
                        continue
                
                # Sort comments by likes (descending) then by date (newest first)
                all_comments.sort(key=lambda x: (-int(x['likes']), x['published']), reverse=True)
                
                # Update UI
                all_comments_window.after(0, lambda: self.populate_all_comments(
                    all_comments_tree, all_comments, progress_label, progress_bar, status_label, all_comments_window))
                    
            except Exception as e:
                all_comments_window.after(0, lambda: messagebox.showerror("Error", f"Failed to load comments: {str(e)}"))
                
        # Start loading in background thread
        threading.Thread(target=load_all_comments, daemon=True).start()
        
    def populate_all_comments(self, tree, comments, progress_label, progress_bar, status_label, window):
        """Populate the all comments tree view"""
        try:
            progress_bar.stop()
            progress_label.config(text="Comments loaded successfully!")
            
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
                
            # Add comments to tree
            for comment in comments:
                display_text = comment['text'][:60] + "..." if len(comment['text']) > 60 else comment['text']
                display_text = display_text.replace('\n', ' ')
                video_title = comment['video_title'][:30] + "..." if len(comment['video_title']) > 30 else comment['video_title']
                
                tree.insert('', 'end', values=(
                    video_title,
                    comment['author'],
                    display_text,
                    comment['likes'],
                    comment['published']
                ))
            
            # Store data for reference
            window.all_comments_data = comments
            
            # Update status
            status_label.config(text=f"Loaded {len(comments)} comments from {len(self.current_videos)} videos")
            self.log_action(f"📑 Loaded {len(comments)} comments from all videos")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to populate comments: {str(e)}")
            
    def add_comment_from_all_view(self, tree):
        """Add comment to selected video from all comments view"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a comment row to see which video to add comment to")
            return
            
        try:
            index = tree.index(selection[0])
            window = tree.winfo_toplevel()
            if hasattr(window, 'all_comments_data') and index < len(window.all_comments_data):
                comment_data = window.all_comments_data[index]
                
                # Find the video data
                video_data = None
                for video in self.current_videos:
                    if video['id'] == comment_data['video_id']:
                        video_data = video
                        break
                        
                if not video_data:
                    messagebox.showerror("Error", "Video data not found")
                    return
                    
                # Set current video and call add comment
                old_selected = self.selected_video_data
                old_video_id = self.current_video_id
                
                self.selected_video_data = video_data
                self.current_video_id = video_data['id']
                
                self.add_comment()
                
                # Restore previous selection
                self.selected_video_data = old_selected
                self.current_video_id = old_video_id
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add comment: {str(e)}")
            
    def edit_comment_from_all_view(self, tree):
        """Edit selected comment from all comments view"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a comment to edit")
            return
            
        try:
            index = tree.index(selection[0])
            window = tree.winfo_toplevel()
            if hasattr(window, 'all_comments_data') and index < len(window.all_comments_data):
                comment_data = window.all_comments_data[index]
                
                # Open edit dialog
                edit_window = tk.Toplevel(self.root)
                edit_window.title("Edit Comment")
                edit_window.geometry("500x300")
                
                ttk.Label(edit_window, text=f"Editing comment by: {comment_data['author']}").pack(pady=10)
                ttk.Label(edit_window, text=f"Video: {comment_data['video_title'][:50]}...").pack(pady=5)
                
                comment_text = scrolledtext.ScrolledText(edit_window, height=10, wrap=tk.WORD)
                comment_text.pack(fill='both', expand=True, padx=10, pady=5)
                comment_text.insert('1.0', comment_data['text'])
                
                def save_edit():
                    new_content = comment_text.get('1.0', tk.END).strip()
                    if new_content:
                        try:
                            # Update comment using YouTube API
                            request_body = {
                                'id': comment_data['comment_id'],
                                'snippet': {
                                    'textOriginal': new_content
                                }
                            }
                            
                            response = self.youtube.comments().update(
                                part='snippet',
                                body=request_body
                            ).execute()
                            
                            self.log_action(f"✏️ Edited comment by {comment_data['author']} on video {comment_data['video_title'][:30]}...")
                            messagebox.showinfo("Success", "Comment edited successfully!")
                            edit_window.destroy()
                            
                            # Refresh the all comments view
                            self.refresh_all_comments(tree, None, None)
                            
                        except HttpError as e:
                            error_detail = json.loads(e.content.decode())
                            error_message = error_detail.get('error', {}).get('message', str(e))
                            messagebox.showerror("Error", f"Failed to edit comment: {error_message}")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to edit comment: {str(e)}")
                    else:
                        messagebox.showwarning("Warning", "Comment cannot be empty")
                        
                button_frame = ttk.Frame(edit_window)
                button_frame.pack(pady=10)
                ttk.Button(button_frame, text="Save Changes", command=save_edit).pack(side='left', padx=5)
                ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side='left', padx=5)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit comment: {str(e)}")
            
    def delete_comment_from_all_view(self, tree):
        """Delete selected comment from all comments view"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a comment to delete")
            return
            
        try:
            index = tree.index(selection[0])
            window = tree.winfo_toplevel()
            if hasattr(window, 'all_comments_data') and index < len(window.all_comments_data):
                comment_data = window.all_comments_data[index]
                
                if messagebox.askyesno("Confirm Delete", 
                                     f"Are you sure you want to delete the comment by {comment_data['author']}?\n\nVideo: {comment_data['video_title'][:50]}...\n\nComment: {comment_data['text'][:100]}..."):
                    try:
                        # Delete comment using YouTube API
                        self.youtube.comments().delete(id=comment_data['comment_id']).execute()
                        self.log_action(f"🗑️ Deleted comment by {comment_data['author']} on video {comment_data['video_title'][:30]}...")
                        messagebox.showinfo("Success", "Comment deleted successfully!")
                        
                        # Refresh the all comments view
                        self.refresh_all_comments(tree, None, None)
                        
                    except HttpError as e:
                        error_detail = json.loads(e.content.decode())
                        error_message = error_detail.get('error', {}).get('message', str(e))
                        messagebox.showerror("Error", f"Failed to delete comment: {error_message}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete comment: {str(e)}")
                        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete comment: {str(e)}")
            
    def open_video_from_comment(self, tree):
        """Open YouTube video from selected comment"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a comment to open its video")
            return
            
        try:
            index = tree.index(selection[0])
            window = tree.winfo_toplevel()
            if hasattr(window, 'all_comments_data') and index < len(window.all_comments_data):
                comment_data = window.all_comments_data[index]
                url = f"https://www.youtube.com/watch?v={comment_data['video_id']}"
                webbrowser.open(url)
                self.log_action(f"🔗 Opened video in YouTube: {comment_data['video_title']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open video: {str(e)}")
            
    def refresh_all_comments(self, tree, progress_label, progress_bar):
        """Refresh all comments view"""
        try:
            # Close the current window and reopen
            window = tree.winfo_toplevel()
            window.destroy()
            self.view_all_comments()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh comments: {str(e)}")
        
    def add_comment(self):
        if not self.selected_video_data:
            messagebox.showwarning("Warning", "Please select a video first")
            return
            
        if not self.youtube:
            messagebox.showerror("Error", "Please authenticate first")
            return
            
        # Open add comment dialog
        add_window = tk.Toplevel(self.root)
        add_window.title("Add Comment")
        add_window.geometry("500x300")
        
        ttk.Label(add_window, text=f"Adding comment to: {self.selected_video_data['title'][:50]}...").pack(pady=10)
        
        ttk.Label(add_window, text="Comment:").pack(anchor='w', padx=10)
        comment_text = scrolledtext.ScrolledText(add_window, height=10, wrap=tk.WORD)
        comment_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        def post_comment():
            content = comment_text.get('1.0', tk.END).strip()
            if content:
                try:
                    # Post comment using YouTube API
                    request_body = {
                        'snippet': {
                            'videoId': self.current_video_id,
                            'topLevelComment': {
                                'snippet': {
                                    'textOriginal': content
                                }
                            }
                        }
                    }
                    
                    response = self.youtube.commentThreads().insert(
                        part='snippet',
                        body=request_body
                    ).execute()
                    
                    self.log_action(f"➕ Added comment to {self.selected_video_data['title']}: {content[:50]}...")
                    messagebox.showinfo("Success", "Comment added successfully!")
                    add_window.destroy()
                    # Refresh comments
                    threading.Thread(target=self.fetch_comments, daemon=True).start()
                    
                except HttpError as e:
                    error_detail = json.loads(e.content.decode())
                    error_message = error_detail.get('error', {}).get('message', str(e))
                    messagebox.showerror("Error", f"Failed to add comment: {error_message}")
                    self.log_action(f"❌ Failed to add comment: {error_message}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add comment: {str(e)}")
                    self.log_action(f"❌ Failed to add comment: {str(e)}")
            else:
                messagebox.showwarning("Warning", "Please enter a comment")
                
        button_frame = ttk.Frame(add_window)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Post Comment", command=post_comment).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=add_window.destroy).pack(side='left', padx=5)
        
    def edit_comment(self):
        selection = self.comments_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a comment to edit")
            return
            
        try:
            index = self.comments_tree.index(selection[0])
            if index < len(self.current_comments):
                comment = self.current_comments[index]
                
                # Open edit dialog
                edit_window = tk.Toplevel(self.root)
                edit_window.title("Edit Comment")
                edit_window.geometry("500x300")
                
                ttk.Label(edit_window, text=f"Editing comment by: {comment['author']}").pack(pady=10)
                
                comment_text = scrolledtext.ScrolledText(edit_window, height=10, wrap=tk.WORD)
                comment_text.pack(fill='both', expand=True, padx=10, pady=5)
                comment_text.insert('1.0', comment['text'])
                
                def save_edit():
                    new_content = comment_text.get('1.0', tk.END).strip()
                    if new_content:
                        try:
                            # Update comment using YouTube API
                            request_body = {
                                'id': comment['id'],
                                'snippet': {
                                    'textOriginal': new_content
                                }
                            }
                            
                            response = self.youtube.comments().update(
                                part='snippet',
                                body=request_body
                            ).execute()
                            
                            self.log_action(f"✏️ Edited comment by {comment['author']}")
                            messagebox.showinfo("Success", "Comment edited successfully!")
                            edit_window.destroy()
                            # Refresh comments
                            threading.Thread(target=self.fetch_comments, daemon=True).start()
                            
                        except HttpError as e:
                            error_detail = json.loads(e.content.decode())
                            error_message = error_detail.get('error', {}).get('message', str(e))
                            messagebox.showerror("Error", f"Failed to edit comment: {error_message}")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to edit comment: {str(e)}")
                    else:
                        messagebox.showwarning("Warning", "Comment cannot be empty")
                        
                button_frame = ttk.Frame(edit_window)
                button_frame.pack(pady=10)
                ttk.Button(button_frame, text="Save Changes", command=save_edit).pack(side='left', padx=5)
                ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side='left', padx=5)
                
        except Exception as e:
            self.log_action(f"Error editing comment: {str(e)}")
            
    def delete_comment(self):
        selection = self.comments_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a comment to delete")
            return
            
        try:
            index = self.comments_tree.index(selection[0])
            if index < len(self.current_comments):
                comment = self.current_comments[index]
                
                if messagebox.askyesno("Confirm Delete", 
                                     f"Are you sure you want to delete the comment by {comment['author']}?\n\n{comment['text'][:100]}..."):
                    try:
                        # Delete comment using YouTube API
                        self.youtube.comments().delete(id=comment['id']).execute()
                        
                        self.log_action(f"🗑️ Deleted comment by {comment['author']}")
                        messagebox.showinfo("Success", "Comment deleted successfully!")
                        # Refresh comments
                        threading.Thread(target=self.fetch_comments, daemon=True).start()
                        
                    except HttpError as e:
                        error_detail = json.loads(e.content.decode())
                        error_message = error_detail.get('error', {}).get('message', str(e))
                        messagebox.showerror("Error", f"Failed to delete comment: {error_message}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete comment: {str(e)}")
                        
        except Exception as e:
            self.log_action(f"Error deleting comment: {str(e)}")
            
    def open_in_youtube(self):
        if not self.selected_video_data:
            messagebox.showwarning("Warning", "Please select a video first")
            return
            
        url = f"https://www.youtube.com/watch?v={self.selected_video_data['id']}"
        webbrowser.open(url)
        self.log_action(f"🔗 Opened video in YouTube: {self.selected_video_data['title']}")
        
    def log_action(self, message):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            self.action_log.insert(tk.END, log_entry)
            self.action_log.see(tk.END)
            print(log_entry.strip())
        except Exception as e:
            print(f"Error logging action: {str(e)}")

def main():
    try:
        root = tk.Tk()
        app = YouTubeCommentManager(root)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {str(e)}")
        messagebox.showerror("Application Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
