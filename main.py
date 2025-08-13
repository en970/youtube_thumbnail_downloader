import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
from PIL import Image, ImageTk
import io
import os
import threading
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class YouTubeThumbnailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Channel Thumbnail Downloader")
        self.root.geometry("1000x700")
        
        # YouTube API setup - You need to replace with your API key
        self.api_key = ""  # Replace with your actual API key
        self.youtube = None
        
        # Data storage
        self.videos_data = []
        self.thumbnail_images = []
        self.download_directory = os.getcwd()
        self.selected_thumbnails = set()  # Store indices of selected thumbnails
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # API Key section
        ttk.Label(main_frame, text="YouTube API Key:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.api_key_entry = ttk.Entry(main_frame, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(5, 0))
        self.api_key_entry.insert(0, self.api_key)
        
        # Search section
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="Channel Username:").grid(row=0, column=0, sticky=tk.W)
        self.username_entry = ttk.Entry(search_frame, width=30)
        self.username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.username_entry.bind('<Return>', self.search_channel)
        
        self.search_button = ttk.Button(search_frame, text="Search", command=self.search_channel)
        self.search_button.grid(row=0, column=2, padx=(5, 0))
        
        # Timeline filter section
        timeline_frame = ttk.Frame(main_frame)
        timeline_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        timeline_frame.columnconfigure(1, weight=1)
        timeline_frame.columnconfigure(3, weight=1)
        
        ttk.Label(timeline_frame, text="Max Results:").grid(row=0, column=0, sticky=tk.W)
        self.max_results_var = tk.StringVar(value="50")
        max_results_combo = ttk.Combobox(timeline_frame, textvariable=self.max_results_var, 
                                       values=["10", "25", "50", "100", "200"], width=10, state="readonly")
        max_results_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(timeline_frame, text="Time Period:").grid(row=0, column=2, sticky=tk.W)
        self.time_period_var = tk.StringVar(value="all")
        time_period_combo = ttk.Combobox(timeline_frame, textvariable=self.time_period_var,
                                       values=["all", "last_week", "last_month", "last_3_months", "last_year"], 
                                       width=15, state="readonly")
        time_period_combo.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Results frame with scrollbar
        self.setup_results_frame(main_frame)
        
        # Selection controls
        selection_frame = ttk.Frame(main_frame)
        selection_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(selection_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(selection_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=(0, 5))
        
        self.selection_label = ttk.Label(selection_frame, text="Selected: 0")
        self.selection_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Download section
        download_frame = ttk.Frame(main_frame)
        download_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        download_frame.columnconfigure(1, weight=1)
        
        ttk.Label(download_frame, text="Download Directory:").grid(row=0, column=0, sticky=tk.W)
        self.directory_label = ttk.Label(download_frame, text=self.download_directory, 
                                       background="white", relief="sunken", width=50)
        self.directory_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        ttk.Button(download_frame, text="Browse", command=self.browse_directory).grid(row=0, column=2, padx=(5, 5))
        
        self.download_button = ttk.Button(download_frame, text="Download Selected Thumbnails", 
                                        command=self.download_thumbnails, state="disabled")
        self.download_button.grid(row=1, column=0, columnspan=3, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken")
        status_bar.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
    def setup_results_frame(self, parent):
        # Create scrollable frame for results
        results_frame = ttk.Frame(parent)
        results_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(results_frame, height=300)
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.canvas = canvas
        
    def search_channel(self, event=None):
        username = self.username_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        if not username:
            messagebox.showwarning("Warning", "Please enter a channel username")
            return
            
        if not api_key:
            messagebox.showwarning("Warning", "Please enter your YouTube API key")
            return
        
        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.videos_data = []
        self.thumbnail_images = []
        self.selected_thumbnails = set()
        self.download_button.config(state="disabled")
        self.update_selection_display()
        
        # Start search in a separate thread
        threading.Thread(target=self._search_channel_thread, args=(username, api_key), daemon=True).start()
        
    def _search_channel_thread(self, username, api_key):
        try:
            self.root.after(0, lambda: self.progress.start())
            self.root.after(0, lambda: self.status_var.set("Searching channel..."))
            
            # Initialize YouTube API client
            self.youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Search for channel
            search_response = self.youtube.search().list(
                q=username,
                type='channel',
                part='id,snippet',
                maxResults=1
            ).execute()
            
            if not search_response['items']:
                self.root.after(0, lambda: messagebox.showinfo("Info", "No channel found with that username"))
                return
                
            channel_id = search_response['items'][0]['id']['channelId']
            
            # Get channel's videos
            self.root.after(0, lambda: self.status_var.set("Fetching videos..."))
            
            # Get channel's upload playlist
            channel_response = self.youtube.channels().list(
                id=channel_id,
                part='contentDetails'
            ).execute()
            
            playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from upload playlist with timeline filter
            max_results = int(self.max_results_var.get())
            
            # Calculate publishedAfter date based on time period
            published_after = None
            time_period = self.time_period_var.get()
            if time_period != "all":
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                if time_period == "last_week":
                    published_after = (now - timedelta(days=7)).isoformat() + 'Z'
                elif time_period == "last_month":
                    published_after = (now - timedelta(days=30)).isoformat() + 'Z'
                elif time_period == "last_3_months":
                    published_after = (now - timedelta(days=90)).isoformat() + 'Z'
                elif time_period == "last_year":
                    published_after = (now - timedelta(days=365)).isoformat() + 'Z'
            
            # Get all videos with pagination if needed
            all_videos = []
            next_page_token = None
            
            while len(all_videos) < max_results:
                remaining_results = min(50, max_results - len(all_videos))  # API limit is 50 per request
                
                request_params = {
                    'playlistId': playlist_id,
                    'part': 'snippet',
                    'maxResults': remaining_results
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                playlist_response = self.youtube.playlistItems().list(**request_params).execute()
                
                # Filter by date if specified
                videos_in_page = playlist_response['items']
                if published_after:
                    videos_in_page = [
                        video for video in videos_in_page 
                        if video['snippet']['publishedAt'] >= published_after
                    ]
                
                all_videos.extend(videos_in_page)
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token or len(playlist_response['items']) == 0:
                    break
            
            self.videos_data = all_videos[:max_results]
            
            # Load thumbnails
            self.root.after(0, self._load_thumbnails)
            
        except HttpError as e:
            if e.resp.status == 403:
                if "YouTube Data API v3 has not been used" in str(e) or "not been enabled" in str(e):
                    error_msg = ("YouTube Data API v3 is not enabled for your project.\n\n"
                               "To fix this:\n"
                               "1. Go to https://console.developers.google.com\n"
                               "2. Select your project\n"
                               "3. Go to 'APIs & Services' > 'Library'\n"
                               "4. Search for 'YouTube Data API v3'\n"
                               "5. Click on it and press 'ENABLE'\n"
                               "6. Wait a few minutes and try again")
                elif "accessNotConfigured" in str(e):
                    error_msg = ("API access not configured.\n\n"
                               "Make sure you:\n"
                               "1. Created an API Key in Google Cloud Console\n"
                               "2. Enabled YouTube Data API v3\n"
                               "3. Set up proper restrictions (if any)")
                else:
                    error_msg = f"YouTube API Error (403): {str(e)}"
            else:
                error_msg = f"YouTube API Error: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("API Error", error_msg))
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        finally:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.status_var.set("Ready"))
            
    def _load_thumbnails(self):
        if not self.videos_data:
            messagebox.showinfo("Info", "No videos found in this channel")
            return
            
        self.status_var.set("Loading thumbnails...")
        
        # Load thumbnails in a separate thread
        threading.Thread(target=self._load_thumbnails_thread, daemon=True).start()
        
    def _load_thumbnails_thread(self):
        try:
            for i, video in enumerate(self.videos_data):
                snippet = video['snippet']
                title = snippet['title']
                thumbnail_url = snippet['thumbnails']['medium']['url']  # You can change to 'high' for better quality
                
                # Download thumbnail
                response = requests.get(thumbnail_url)
                img = Image.open(io.BytesIO(response.content))
                img.thumbnail((200, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                self.thumbnail_images.append({
                    'photo': photo,
                    'title': title,
                    'url': thumbnail_url,
                    'original_img': Image.open(io.BytesIO(response.content))
                })
                
                # Update UI in main thread
                self.root.after(0, lambda i=i: self._add_thumbnail_to_ui(i))
                
            self.root.after(0, lambda: self.download_button.config(state="normal"))
            self.root.after(0, lambda: self.status_var.set(f"Loaded {len(self.videos_data)} thumbnails"))
            self.root.after(0, self.update_selection_display)
            
        except Exception as e:
            error_msg = f"Error loading thumbnails: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            
    def _add_thumbnail_to_ui(self, index):
        if index >= len(self.thumbnail_images):
            return
            
        thumb_data = self.thumbnail_images[index]
        
        # Create frame for each thumbnail
        thumb_frame = ttk.Frame(self.scrollable_frame, padding="5")
        thumb_frame.grid(row=index//4, column=index%4, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Selection checkbox
        var = tk.BooleanVar()
        checkbox = ttk.Checkbutton(thumb_frame, variable=var, command=lambda i=index: self.toggle_selection(i))
        checkbox.grid(row=0, column=0, sticky=tk.W)
        
        # Store the checkbox variable for later reference
        thumb_data['checkbox_var'] = var
        
        # Thumbnail image
        thumb_label = ttk.Label(thumb_frame, image=thumb_data['photo'])
        thumb_label.grid(row=1, column=0, pady=(0, 5))
        
        # Title (truncated if too long)
        title = thumb_data['title']
        if len(title) > 25:
            title = title[:25] + "..."
        title_label = ttk.Label(thumb_frame, text=title, width=25, wraplength=200)
        title_label.grid(row=2, column=0)
        
        # Update canvas scroll region
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def toggle_selection(self, index):
        if index in self.selected_thumbnails:
            self.selected_thumbnails.remove(index)
        else:
            self.selected_thumbnails.add(index)
        self.update_selection_display()
        
    def select_all(self):
        self.selected_thumbnails = set(range(len(self.thumbnail_images)))
        for i, thumb_data in enumerate(self.thumbnail_images):
            if 'checkbox_var' in thumb_data:
                thumb_data['checkbox_var'].set(True)
        self.update_selection_display()
        
    def deselect_all(self):
        self.selected_thumbnails = set()
        for thumb_data in self.thumbnail_images:
            if 'checkbox_var' in thumb_data:
                thumb_data['checkbox_var'].set(False)
        self.update_selection_display()
        
    def update_selection_display(self):
        count = len(self.selected_thumbnails)
        self.selection_label.config(text=f"Selected: {count}")
        
        # Update download button text
        if count == 0:
            self.download_button.config(text="Download Selected Thumbnails", state="disabled")
        elif count == len(self.thumbnail_images):
            self.download_button.config(text=f"Download All Thumbnails ({count})", state="normal")
        else:
            self.download_button.config(text=f"Download Selected Thumbnails ({count})", state="normal")
            
    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.download_directory)
        if directory:
            self.download_directory = directory
            self.directory_label.config(text=directory)
            
    def download_thumbnails(self):
        if not self.selected_thumbnails:
            messagebox.showwarning("Warning", "Please select thumbnails to download")
            return
            
        # Start download in separate thread
        threading.Thread(target=self._download_thumbnails_thread, daemon=True).start()
        
    def _download_thumbnails_thread(self):
        try:
            self.root.after(0, lambda: self.progress.start())
            self.root.after(0, lambda: self.download_button.config(state="disabled"))
            
            success_count = 0
            selected_indices = sorted(self.selected_thumbnails)
            
            for count, index in enumerate(selected_indices):
                try:
                    thumb_data = self.thumbnail_images[index]
                    
                    # Create safe filename
                    title = thumb_data['title']
                    # Remove invalid characters for filename
                    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    if len(safe_title) > 50:
                        safe_title = safe_title[:50]
                    
                    filename = f"{index+1:02d}_{safe_title}.jpg"
                    filepath = os.path.join(self.download_directory, filename)
                    
                    # Save original quality image
                    thumb_data['original_img'].save(filepath, 'JPEG', quality=95)
                    success_count += 1
                    
                    # Update status
                    self.root.after(0, lambda c=count+1, t=len(selected_indices): 
                                  self.status_var.set(f"Downloaded {c}/{t}"))
                    
                except Exception as e:
                    print(f"Error downloading thumbnail {index+1}: {e}")
                    
            message = f"Successfully downloaded {success_count} thumbnails to:\n{self.download_directory}"
            self.root.after(0, lambda: messagebox.showinfo("Download Complete", message))
            
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        finally:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.download_button.config(state="normal"))
            self.root.after(0, lambda: self.status_var.set("Ready"))

def main():
    root = tk.Tk()
    app = YouTubeThumbnailApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()