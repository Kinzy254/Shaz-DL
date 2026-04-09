# Panel downloader version-4 by ...

# Imports
from io import BytesIO
import json
import mimetypes
from pathlib import Path, PurePosixPath
import hashlib
import re
import subprocess
import threading
import time
from urllib.parse import urlparse, parse_qs, urlunparse
from queue import Queue
from PIL import Image, ImageTk
import pyaudio
import requests
import yt_dlp
import tkinter as tk
import customtkinter as ctk


# Logic Class
class YTDL():
    def __init__(self):
        
        # Variables
        self.download_queue = Queue()
        self.OUT_TYPE = "audio" # or "video"
        self.OUTPUT_FOLDER = Path.home() / "Downloads" / "QByiT"
        self.load_history_status = ""
        self.history_lock = threading.RLock()
        self.search_results_count = 20

        self.STREAM_THREAD_STOP = threading.Event()  # Event to signal stream thread to stop
        self.STREAM_START = False
        self.STREAM_PAUSE = False
        self.STREAM_STOP = False

        self.running_downloads = {}
        self.in_queue_downloads = {}
        self.finished_downloads = {}
        self.cancelled_downloads = {}
        self.errored_downloads = {}


        # Directories
        self.download_path = Path.home() / "Downloads" / "QByiT"
        self.appdata_path = Path.home() / ".qbyit"
        self.cache_folder = self.appdata_path / "cache"
        self.data_folder = self.appdata_path / "data"
        self.thumbnails_folder = self.data_folder / "Thumbnails"

        # Working files
        self.history_file = self.data_folder / "qbyit_history.json" #download history

        try:
            self.create_dirs(
                [
                    self.download_path, 
                    self.appdata_path, 
                    self.cache_folder,
                    self.data_folder,
                self.thumbnails_folder,
            ])
        except Exception as e:
            print("Error creating directories:", e)
    
        # Load and categorize history
        try:
            self.history = self.manage_history()["load_history"]()
            self.load_history_status = "success"
            self.manage_history()["categorize_history"]()
            #print(self.history)
        except Exception as e:
            print("Error loading history.", e)
            self.history = {}
            self.load_history_status = "error"


    def manage_history(self):
        """Manage history and history file

        Returns:
            dict: A dictionary containing the history management functions. ie. {
                "load_history": load_history,
                "save_history": save_history,
                "categorize_history": categorize_history,
                "add_history_entry": add_history_entry
                "modify_history_entry": modify_history_entry}
        """
        with self.history_lock:
            def load_history():
                if self.history_file.exists():
                    try:
                        with self.history_file.open("r", encoding="utf-8") as f:
                            self.history = json.load(f)
                            return self.history
                    except Exception as e:
                        print("Error parsing history file:", e)
                        self.history = {}
                        return {}
                else:
                    self.history = {}
                    return {}
                
            def save_history():
                try:
                    with self.history_file.open("w", encoding="utf-8") as f:
                        json.dump(self.history, f, indent=4)
                except Exception as e:
                    print("Error saving history:", e)

            def categorize_history():
                self.running_downloads = {}
                self.in_queue_downloads = {}
                self.finished_downloads = {}
                self.cancelled_downloads = {}
                self.errored_downloads = {}

                for link, data in self.history.items():
                    status = data.get("download_status")
                    if status == "running":
                        self.running_downloads.update({link: data})
                    elif status == "in_queue":
                        self.in_queue_downloads.update({link: data})
                    elif status == "finished":
                        self.finished_downloads.update({link: data})
                    elif status == "cancelled":
                        self.cancelled_downloads.update({link: data})
                    elif status == "error":
                        self.errored_downloads.update({link: data})

            def add_history_entry(entry: dict):
                """Add a new entry to the history.

                Args:
                    entry (dict): The entry to add. eg. {link : {date_added, title, link, link_id, dl_opts, download_status, destination_path, filesize}}
                """
                if self.load_history_status != "success":
                    try:
                        load_history()
                    except Exception as e:
                        print("Error loading history for add_history_entry:", e)
                        return
                link, values = next(iter(entry.items()))

                dl_opts = {k: v for k, v in values.get("dl_opts", {}).items()
                            if k not in ["progress_hooks", "postprocessor_hooks"]}

                template = {
                    "date_added": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "title": values.get("title", ""),
                    "link": values.get("link", ""),
                    "link_id": values.get("link_id", ""),
                    "dl_opts": dl_opts,
                    "download_status": values.get("download_status", "in_queue"),
                    "download_type": values.get("download_type", ""),
                    "destination_path": values.get("destination_path", ""),
                    "filesize": values.get("filesize", 0),
                }

                self.history.update({link: template})
                save_history()
                categorize_history()

            def modify_history_entry(key, new_values: dict):
                """Modify an existing history entry identified by 'key' with new values provided in 'new_values' dictionary.
                
                Args:
                    key: The unique identifier for the history entry to modify (e.g., a link or ID).
                    new_values: A dictionary containing the fields to update and their new values.
                """
                if self.load_history_status != "success":
                    try:
                        load_history()
                    except Exception as e:
                        print("Error loading history for modify_history_entry:", e)
                        return

                if key in self.history:
                    self.history[key].update(new_values)
                    save_history()
                    categorize_history()


            return {
                "load_history": load_history,
                "save_history": save_history,
                "categorize_history": categorize_history,
                "add_history_entry": add_history_entry,
                "modify_history_entry": modify_history_entry,
            }


    def create_dirs(self, dirs: list):
        """Create directories if they don't exist.

        Args:
            dirs (list): A list of directory paths to create.
        """
        try:
            for dir in dirs:
                Path(dir).mkdir(parents=True, exist_ok=True)
        except:
            pass

    def classify_link(self, value: str) -> tuple[str, str]:
        """
        Returns a tuple (type, id_or_hash[:16]):
        type: 'video', 'playlist', 'link'
        id_or_hash: video ID, playlist ID, or SHA256[:16] hash of value
        """
        value = value.strip()

        # Regex for video ID (11 chars)
        YOUTUBE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
        # Regex for playlist ID (PL, UU, LL, etc)
        YOUTUBE_PLAYLIST_ID_RE = re.compile(r"^(PL|UU|LL)[A-Za-z0-9_-]{13,32}$")

        # --- already a video ID ---
        if YOUTUBE_VIDEO_ID_RE.match(value):
            return "video", value

        # --- already a playlist ID ---
        if YOUTUBE_PLAYLIST_ID_RE.match(value):
            return "playlist", value

        # --- parse as URL ---
        parsed = urlparse(value)
        domain = parsed.netloc.lower()

        # youtu.be short links (video only)
        if "youtu.be" in domain:
            vid = parsed.path.lstrip("/")
            if YOUTUBE_VIDEO_ID_RE.match(vid):
                return "video", vid

        # youtube.com links
        if "youtube.com" in domain:
            qs = parse_qs(parsed.query)

            # playlist in query
            if "list" in qs:
                plist = qs["list"][0]
                if YOUTUBE_PLAYLIST_ID_RE.match(plist):
                    return "playlist", plist

            # video in query
            if "v" in qs:
                vid = qs["v"][0]
                if YOUTUBE_VIDEO_ID_RE.match(vid):
                    return "video", vid

            # path formats: /shorts/ID or /embed/ID
            m = re.search(r"/(shorts|embed)/([^/?]+)", parsed.path)
            if m and YOUTUBE_VIDEO_ID_RE.match(m.group(2)):
                return "video", m.group(2)

        # fallback: generic link
        return "link", hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def get_link_info(self, link: str, write_info_json=True) -> dict | None:
        """
        Extract metadata from a YouTube link using yt_dlp.

        Args:
            link: video or playlist URL
            write_info_json: default True

        Returns:
            info dict or None if extraction failed
        """

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,   # full info for video
            "noplaylist": False,     # allow playlist detection
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)

                # --- optionally write JSON ---
                if write_info_json:
                    info_path = self.cache_folder / f"{self.classify_link(link)[1]}.info.json"

                    # yt-dlp has built-in JSON writer
                    ydl.sanitize_info(info)
                    with info_path.open("w", encoding="utf-8") as f:
                        ydl._write_info_json("info", info, f)

                return info

        except Exception:
            return None

    def find_deepest_metadata_key(self, data, search_key):
        """
        Recursively searches for the 'text' value corresponding to a given 'title' key
        in a deeply nested structure of lists and dictionaries.

        Args:
            data (dict or list): The nested data to search.
            search_key (str): The 'title' value to search for.

        Returns:
            str or None: The 'text' value corresponding to the search_key, or None if not found.
        """
        # If the current level is a dictionary, search within it
        if isinstance(data, dict):
            # Check if the dictionary contains the 'title' and 'text' keys and matches the search_key
            if data.get(search_key):
                return data[search_key]
            # Otherwise, recurse into the dictionary's values
            for value in data.values():
                if isinstance(value, dict):
                    result = self.find_deepest_metadata_key(value, search_key)
                    return result

        # If the current level is a list, iterate through it and search each item
        elif isinstance(data, list):
            for item in data:
                result = self.find_deepest_metadata_key(item, search_key)
                if result is not None:
                    return result

        # If no match is found, return None
        return None

    def get_dl_options(self):
        """Build dl options from current settings"""
        opts = {
            "quiet": True,  # Suppress output
            "no_warnings": True,
            "noprogress": True,  # Disable progress bar
            "windows_filename": True,  # Ensure compatibility with Windows
            "outtmpl": str(self.download_path / "%(title)s.%(ext)s"),
            "noplaylist": True,
        }

        if self.OUT_TYPE == "audio":
            opts["format"] = "bestaudio"
            opts["embedthumbnail"] = True
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
                {"key": "FFmpegMetadata"},
            ]

        elif self.OUT_TYPE == "video":
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"  # Ensure desired video output
            opts["embedsubtitles"] = True
            opts["postprocessors"] = [
                {"key": "FFmpegMetadata"},
            ]

        else:
            opts["format"] = "best"

        opts["progress_hooks"] = [self.progress_callback ]  # Hook for progress updates
        opts["postprocessor_hooks"] = [self.postprocess_callback]  # Hook for postprocessing updates



        return opts
    

    def add_dl_task(self, link, widget):
        """Create a download task for queing"""
        
        task = {
            "link" : link,
            "opts" : "",
            "widget" : widget, # optional: card widget for progress updates
        }

        self.download_queue.put(task)


    def download_worker(self):
        """Continuously process download queue in background thread"""
        while True:
            task = self.download_queue.get()  # blocks until a task is available
            link = task.get("link")
            widget = task.get("widget")  # optional: card widget for progress updates
            opts = task.get("opts") or self.get_dl_options()

            # mark in history as running
            if link in self.history:
                self.manage_history().get("modify_history_entry")(link, {"download_status": "running"})

            # Attach hooks to update this specific card
            if widget:
                opts["progress_hooks"] = [lambda d, w=widget: self.progress_callback(d, w)]
                opts["postprocessor_hooks"] = [lambda d, w=widget: self.postprocess_callback(d, w)]

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([link])

                # finished
                if link in self.history:
                    self.manage_history().get("modify_history_entry")(link, {"download_status": "finished"})
            except Exception as e:
                print("Download worker error:", e)
                if link in self.history:
                    self.manage_history().get("modify_history_entry")(link, {"download_status": "error"})

            self.download_queue.task_done()


    def postprocess_callback(self, d, w): 
        """Handle postprocessing progress updates."""
        
        w.after(0, lambda: w.set_status("Post-processing..."))

        status = d.get('status')
        postprocessor = d.get('postprocessor', 'Unknown')
        template = d.get('_default_template', 'Unknown')

        if status == 'started':
            print(f"Started: {postprocessor}")
            #w.after(0, lambda: w.set_status(f"{template}"))
            w.after(0, lambda: w.update_progress(0.0))  # Reset progress bar for post-processing phase

            #json.dump(d, open(self.data_folder / f"{postprocessor}_started_debug.json", "w"), indent=4)  # Debug: print the entire dictionary to see available keys

        elif status == 'finished':
            print(f"Finished: {postprocessor}" )
            w.after(0, lambda: w.set_status(f"Download complete"))
            w.after(0, lambda: w.update_progress(1.0))

            #json.dump(d, open(self.data_folder / f"{postprocessor}_finished_debug.json", "w"), indent=4)  # Debug: print the entire dictionary to see available keys

        elif status == 'error':
            error_msg = d.get('error', 'Unknown error')
            print(f"Error in {postprocessor}: {error_msg}")
            w.after(0, lambda: w.canvas.itemconfigure(w.status_id, text=f"Error: {postprocessor}"))
            w.after(0, lambda: w.update_progress(0.5))  # Indicate error with half-filled progress bar


    def progress_callback(self, d, w):
        """Update progress bar."""
        if d.get("status") == "downloading":
            percent_raw = d.get("_percent_str", "0%").strip()
            percent_raw = re.sub(r'\x1b\[[0-9;]*m', '', percent_raw)
            bar_value = 0.0
            if "%" in percent_raw:
                try:
                    bar_value = float(percent_raw.rstrip('%').replace(" ", "").strip()) / 100.0
                except Exception as e:
                    print(f"Could not parse value '{percent_raw}': {e}")

            #percent_value = max(0.0, min(1.0, percent_value))

            downloaded = re.sub(r'\x1b\[[0-9;]*m', '', (d.get("_downloaded_bytes_str", "").strip()))
            total_size = re.sub(r'\x1b\[[0-9;]*m', '', (d.get("_total_bytes_str", "Unknown").strip() or "Unknown"))
            speed = re.sub(r'\x1b\[[0-9;]*m', '', (d.get("_speed_str", "N/A").strip() if d.get("_speed_str") else "N/A"))
            eta = re.sub(r'\x1b\[[0-9;]*m', '', d.get("_eta_str", "N/A").strip() if d.get("_eta_str") else "N/A")

            print(f"Downloading: {percent_raw} of {total_size} at {speed}, ETA: {eta}", end="\r")

            w.after(0, lambda: w.update_progress(bar_value)) 
            #w.after(0, lambda: w.set_status(f"{downloaded} of {total_size} at {speed}, ETA: {eta}"))
            w.after(0, lambda: w.set_status(f"{percent_raw} at {speed}, ETA: {eta}"))
            
        elif d.get("status") == "finished":
            print("\nDownload finished, now post-processing..." )
            w.after(0, lambda: w.update_progress(1.0))
            w.after(0, lambda: w.set_status("Finished"))

        elif d.get("status") == "error":
            error_msg = d.get('error', 'Unknown error')
            print(f"Error during download: {error_msg}")
            w.after(0, lambda: w.canvas.itemconfigure(w.status_id, text=f"Error: {error_msg}")) 

    
    def download_thumbnail(self, thumbnail_url):
        def _dl(url: str, out_dir=self.thumbnails_folder) -> Path:
            """
            Download an image and save with correct extension detected by Pillow.
            """
            # Clean YouTube thumbnail URL by stripping query parameters
            if "ytimg.com" in url:
                parsed = urlparse(url)
                url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
            
            # Determine filename
            parsed = urlparse(url)
            path_parts = PurePosixPath(parsed.path).parts

            if "ytimg.com" in parsed.netloc and len(path_parts) >= 3 and path_parts[1] == "vi":
                filename_base = path_parts[2]  # video ID

            else:
                # Use truncated SHA256 of URL
                hash_digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
                filename_base = hash_digest[:16]

            # Check if thumbnail exists
            for _ in Path(self.thumbnails_folder).glob(f"*.*"):
                if filename_base == Path(_).stem:
                    #print(f"Cache found at: {_}")
                    return _

            # Download the image
            response = requests.get(url)
            response.raise_for_status()
            data = response.content

            # Detect format using Pillow
            img = Image.open(BytesIO(data))
            fmt = img.format.lower()
            ext = ".jpg" if fmt == "jpeg" else f".{fmt}"

            # Save to file
            out_path = out_dir / f"{filename_base}{ext}"
            out_path.write_bytes(data)

            return out_path

        if "ytimg.com" in thumbnail_url:
            parsed = urlparse(thumbnail_url)
            cleaned_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
            try:
                return _dl(cleaned_url)
            except Exception as e:
                print(f"Error downloading thumbnail: {e}")
                return

        else:
            try:
                return _dl(thumbnail_url)
            except Exception as e:
                print(f"Error downloading thumbnail: {e}")
                return


    def yt_search_query(self, query, max_results):
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,  # only metadata (no downloads)
            "skip_download": True,
            "noplaylist": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_str = f"ytsearch{max_results}:{query}"
            info = ydl.extract_info(search_str, download=False)
            entries = info.get("entries", [])



            return entries
        

    def stream_audio(self, url, name=""):
        CHUNK = 8192  # 8KB
        self.STREAM_THREAD_STOP.clear()  # Clear any previous stop signal
        self.STREAM_START = True
        self.STREAM_PAUSE = False
        self.STREAM_STOP = False

        # -------------------------------
        # STEP 1: yt-dlp -> raw audio stream
        # -------------------------------
        yt = subprocess.Popen(
            [
                "yt-dlp",
                "-f", "bestaudio",
                "-no-warnings",
                "--no-playlist",
                "--retries", "99",
                "--retry-sleep", "5",
                "--socket-timeout", "30",
                "--skip-unavailable-fragments",
                "-o", "-",
                url
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # -------------------------------
        # STEP 2: ffmpeg -> decode PCM
        # -------------------------------
        ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",

                # stability flags
                "-fflags", "+nobuffer+discardcorrupt", # reduce latency and skip bad frames
                "-probesize", "32", # reduce initial buffering
                "-analyzeduration", "0", # disable stream analysis to start faster

                "-i", "pipe:0",

                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ac", "2",
                "-ar", "44100",
                "pipe:1"
            ],
            stdin=yt.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )

        # IMPORTANT: close yt stdout in parent
        yt.stdout.close()

        # -------------------------------
        # STEP 3: PyAudio playback
        # -------------------------------
        p = pyaudio.PyAudio()

        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=44100,
            output=True
        )

        print(f"Streaming {name if name else url} started...")

        try:
            while True and not self.STREAM_THREAD_STOP.is_set():
                data = ffmpeg.stdout.read(CHUNK)

                #print(f"Read {len(data)} bytes from ffmpeg stream...")  # Debug: check if data is being read

                #Check for pause signal
                if self.STREAM_PAUSE:
                    print("Streaming paused. Waiting to resume...")
                    while self.STREAM_PAUSE and not self.STREAM_THREAD_STOP.is_set():
                        time.sleep(0.1)
                    print("Resuming streaming...")

                # Check for stream stop signal
                if self.STREAM_STOP:
                    print("Streaming stopped.")
                    break

                # proper EOF detection
                if not data:
                    if ffmpeg.poll() is not None:
                        break
                    continue

                stream.write(data)

        except KeyboardInterrupt:
            print("Stopping...")

        finally:
            self.STREAM_START = False
            self.STREAM_PAUSE = False
            self.STREAM_STOP = False

            stream.stop_stream()
            stream.close()
            p.terminate()

            ffmpeg.kill()
            yt.kill()

            print("Stream ended.")
            print("Clean exit.")


class Dl_Gui(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Initialize YTDL class
        self.YTDL = YTDL()
        threading.Thread(target=self.YTDL.download_worker, daemon=True).start()
        
        # Window configuration
        self.title("YouTube Downloader Pro")
        x, y = self.winfo_screenwidth() - 620, self.winfo_screenheight() - 750
        self.geometry(f"600x{x-100}+{x}+{y}")
        self.overrideredirect(True) # Hide close and minimize buttons
        #self.attributes('-topmost', True)
        #self.attributes('-toolwindow', True) # Removes taskbar icon
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Close button
        self.close_button = ctk.CTkButton(
            self,
            text="X",
            width=20,
            height=15,
            fg_color="transparent",
            hover_color="#ff4d4d",
            font=ctk.CTkFont(size=14, weight="normal"),
            command=self.destroy
        )
        # Place at absolute top-right
        self.close_button.place(relx=1.0, x=-8, y=8, anchor="ne")
        self.after_idle(self.close_button.tkraise)

#------------------------------------------------------------------------------------------------------
        # Tabs
        self.grid_columnconfigure(index=0, weight=1)
        self.grid_rowconfigure(index=0, weight=1)

        self.tabs = ctk.CTkTabview(self, anchor="s")
        self.tabs.grid(row=0, column=0, sticky="nsew")

        self.home_tab = self.tabs.add("Home")
        self.downloads_tab = self.tabs.add("Downloads")

#--------------------------------------------------------------------------------------------------
        # HOME TAB
        self.home_tab.grid_columnconfigure(0, weight=1)
        self.home_tab.grid_rowconfigure(0, weight=1)

        # Header
        home_frame = ctk.CTkFrame(self.home_tab)
        home_frame.grid(row=0, column=0, sticky="nsew")

        home_frame.grid_columnconfigure(index=0, weight=1)
        home_frame.grid_rowconfigure(index=0, weight=0) #_/
        home_frame.grid_rowconfigure(index=1, weight=0) #_/
        home_frame.grid_rowconfigure(index=2, weight=1) #_/

        header = ctk.CTkLabel(home_frame, text="Shaz-DL", font=ctk.CTkFont(size=24, weight="bold"), anchor="w")
        header.grid(row=0, column=0, sticky="w", pady=(5, 5))

        # URL Input
        url_frame = ctk.CTkFrame(home_frame)
        url_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 5))

        url_frame.grid_columnconfigure(index=0, weight=10)
        url_frame.grid_columnconfigure(index=1, weight=1)
        url_frame.grid_rowconfigure(index=0, weight=0)
        url_frame.grid_rowconfigure(index=1, weight=1)

        url_label = ctk.CTkLabel(url_frame, text="URL:", font=ctk.CTkFont(size=14, weight="bold"))
        url_label.grid(row=0, column=0, sticky="w", padx=5)

        search_results_count_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        search_results_count_frame.grid(row=0, column=1, sticky="w", padx=5)

        search_results_count_label = ctk.CTkLabel(search_results_count_frame, width=100, text="Search Results:")
        search_results_count_label.grid(row=0, column=0, sticky="n", padx=5)

        def _on_search_results_count_change(value):
            try:
                self.YTDL.search_results_count = int(value)
                print(f"Search results count set to: {self.YTDL.search_results_count}")
            except ValueError:
                print(f"Invalid search results count: {value}")

        search_results_count_dropdown = ctk.CTkOptionMenu(search_results_count_frame, fg_color="gray20", button_color="gray20", values=["10", "20", "30", "50", "70", "100"], width=50, command=_on_search_results_count_change)
        search_results_count_dropdown.set("50")  # Set default value
        search_results_count_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=(0, 5))

        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="Search or insert URL...", height=35)
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.url_entry.focus_set()

        self.search_btn = ctk.CTkButton(url_frame, text="Search", font=ctk.CTkFont(size=14, weight="bold"),
                                         width=100, command=self._on_search)
        self.search_btn.grid(row=1, column=1, pady=(0, 5))

        def _enter_search(event):
            self.search_btn.invoke()

        self.url_entry.bind("<Return>", _enter_search)

        # Search Results frame
        self.search_results_frame = ctk.CTkScrollableFrame(home_frame)
        self.search_results_frame.grid(row=2, column=0, sticky="nsew", pady=(5, 5))
        
        self.search_results_frame.grid_columnconfigure(index=0, weight=1)
        self.search_results_frame.grid_columnconfigure(index=1, weight=1)


#--------------------------------------------------------------------------------------------
        # DOWNLOADS TAB
        self.downloads_tab.grid_columnconfigure(0, weight=1)
        self.downloads_tab.grid_rowconfigure(0, weight=1)

        # Header
        downloads_frame = ctk.CTkFrame(self.downloads_tab)
        downloads_frame.grid(row=0, column=0, sticky="nsew")

        downloads_frame.grid_columnconfigure(index=0, weight=1)
        downloads_frame.grid_columnconfigure(index=1, weight=1)
        downloads_frame.grid_columnconfigure(index=2, weight=1)
        downloads_frame.grid_columnconfigure(index=3, weight=1)
        downloads_frame.grid_columnconfigure(index=4, weight=1)
        downloads_frame.grid_rowconfigure(index=3, weight=1) #_/


        header = ctk.CTkLabel(downloads_frame, text="Shaz-DL", font=ctk.CTkFont(size=24, weight="bold"), anchor="w")
        header.grid(row=0, column=0, columnspan=3, sticky="w", pady=(5, 5))

        dl_queue_header = ctk.CTkLabel(downloads_frame, text="Download Queue", font=ctk.CTkFont(size=18, weight="bold"), anchor="w")
        dl_queue_header.grid(row=1, column=0, columnspan=4, sticky='w', padx=30, pady=(5, 5))

        self.running_label =  ctk.CTkLabel(downloads_frame, text="Running", cursor="hand2", font=ctk.CTkFont(size=12, weight="bold", underline=True))
        self.running_label.grid(row=2, column=0)
        self.running_label.bind("<Button-1>", lambda event: self._on_dl_state_label_click(event, "running"))

        self.in_queue_label =  ctk.CTkLabel(downloads_frame, text="In Queue", cursor="hand2", font=ctk.CTkFont(size=12, weight="bold", underline=True))
        self.in_queue_label.grid(row=2, column=1)
        self.in_queue_label.bind("<Button-1>", lambda event: self._on_dl_state_label_click(event, "in_queue"))

        self.finished_label =  ctk.CTkLabel(downloads_frame, text="Finished", cursor="hand2", font=ctk.CTkFont(size=12, weight="bold", underline=True))
        self.finished_label.grid(row=2, column=2)
        self.finished_label.bind("<Button-1>", lambda event: self._on_dl_state_label_click(event, "finished"))

        self.cancelled_label =  ctk.CTkLabel(downloads_frame, text="Cancelled", cursor="hand2", font=ctk.CTkFont(size=12, weight="bold", underline=True))
        self.cancelled_label.grid(row=2, column=3)
        self.cancelled_label.bind("<Button-1>", lambda event: self._on_dl_state_label_click(event, "cancelled"))

        self.errored_label =  ctk.CTkLabel(downloads_frame, text="Error", cursor="hand2", font=ctk.CTkFont(size=12, weight="bold", underline=True))
        self.errored_label.grid(row=2, column=4)
        self.errored_label.bind("<Button-1>", lambda event: self._on_dl_state_label_click(event, "error"))

        self.dl_data_frame = ctk.CTkScrollableFrame(downloads_frame)
        self.dl_data_frame.grid(row=3, column=0, columnspan=5, padx=5, pady=(5, 0), sticky="nsew")


    def _on_dl_state_label_click(self, event, state):
        #print(f"Clicked on label: {state}")
        label_data = {}
        if state == "running":
            label_data = self.YTDL.running_downloads
        elif state == "in_queue":
            label_data = self.YTDL.in_queue_downloads
        elif state == "finished":
            label_data = self.YTDL.finished_downloads
        elif state == "cancelled":
            label_data = self.YTDL.cancelled_downloads
        elif state == "error":
            label_data = self.YTDL.errored_downloads

        print(f"Found {len(label_data)} items with status '{state}'")

        self.after(0, lambda: self.populate_dl_frame(self.dl_data_frame, label_data))

    def _enqueue_download(self, link, out_type, card, entry_info):
        if not link:
            print("No link provided for download task")
            return

        self.YTDL.OUT_TYPE = out_type
        self.YTDL.add_dl_task(link, card)
        dl_template = {link : {
            "title": entry_info.get("title", ""),
            "link": link,
            "link_id": entry_info.get("id", ""),
            "dl_opts": self.YTDL.get_dl_options(),
            "download_status": "in_queue",
            "download_type": out_type,
            "destination_path": "",
            "filesize": 0,
        }}
        self.YTDL.manage_history()["add_history_entry"]({link: dl_template[link]})

    def create_dl_card(self, parent, link_info):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="green")
        card.grid_columnconfigure(0, weight=1)

        # Canvas fills card
        canvas = tk.Canvas(
            card,
            highlightthickness=0,
            width=280,
            height=180,
            bg="#FAA8C3"
        )
        canvas.pack(fill="both", expand=True)

        # --- Text (Canvas) ---
        title = link_info.get("title", "Title Not Found")
        if len(title) > 55:
            title = title[:55] + "..."
        uploader = link_info.get("uploader", "Uploader Not Found")

        card.shadow_title_id = canvas.create_text(11, 9, anchor="nw",text=title, width=250, fill="black",
                                            font=("Segoe UI", 10, "bold"))
        card.title_id = canvas.create_text(10, 8, anchor="nw",text=title, width=250, fill="white",
                                        font=("Segoe UI", 10, "bold"))

        card.shadow_channell = canvas.create_text(11, 46, anchor="nw", text=uploader,
                                        fill="#ffffff", font=("Segoe UI", 11))
        card.channell = canvas.create_text(10, 45, anchor="nw", text=uploader,
                                        fill="#bbbbbb", font=("Segoe UI", 11))

        card.status_id = canvas.create_text(
            10, 100,
            anchor="nw",
            text="Waiting",
            fill="#aaaaaa",
            font=("Segoe UI", 11)
        )

        card.canvas = canvas
        card.set_status = lambda text: canvas.itemconfigure(card.status_id, text=text)

        # --- Progress bar (CTk) ---
        card.progressbar = ctk.CTkProgressBar(card)
        card.progressbar.set(0)
        canvas.create_window(
            10, 120,
            anchor="nw",
            width=160,
            window=card.progressbar
        )

        return card

    def populate_dl_frame(self, parent, label_data):
        # Clear old results
        for child in parent.winfo_children():
            child.destroy()

        if label_data:
            for i, item_info in enumerate(label_data.values()):
                card = self.create_dl_card(parent, item_info)
                row = i // 3
                col = i % 3
                card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")






    def _on_search(self):
        #self.search_btn.configure(state="disabled")
        text = self.url_entry.get().strip()
        if text:
            print("Searching: " + text)
            self.create_search_results(text)
            threading.Thread(target=self.create_search_results, args=(text,), daemon=True).start()


    def create_search_results(self, text):
        results = self.YTDL.yt_search_query(text, self.YTDL.search_results_count)
        self.after(0, lambda: self.populate_results(results))


    def create_result_card(self, parent, entry):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        # Canvas fills card
        canvas = tk.Canvas(
            card,
            highlightthickness=0,
            width=280,
            height=180,
            bg="#FAA8C3"
        )
        canvas.pack(fill="both", expand=True)

        # --- Text (Canvas) ---
        title = entry.get("title", "")
        if len(title) > 55:
            title = title[:55] + "..."
        uploader = entry.get("uploader", "")

        card.shadow_title_id = canvas.create_text(11, 9, anchor="nw",text=title, width=250, fill="black",
                                            font=("Segoe UI", 10, "bold"))
        card.title_id = canvas.create_text(10, 8, anchor="nw",text=title, width=250, fill="white",
                                        font=("Segoe UI", 10, "bold"))

        card.shadow_channell = canvas.create_text(11, 46, anchor="nw", text=uploader,
                                        fill="#ffffff", font=("Segoe UI", 11))
        card.channell = canvas.create_text(10, 45, anchor="nw", text=uploader,
                                        fill="#bbbbbb", font=("Segoe UI", 11))
        
        duration_str = entry.get("duration_string") or entry.get("duration") or ""
        duration_str = time.strftime("%H:%M:%S", time.gmtime(float(duration_str))) if duration_str else duration_str
        
        card.shadow_duration_id = canvas.create_text(11, 71, anchor="nw", text=duration_str,
                                        fill="#ffffff", font=("Segoe UI", 11))
        card.duration = canvas.create_text(10, 70, anchor="nw", text=duration_str,
                                        fill="#bbbbbb", font=("Segoe UI", 11))
        
        card.status_id = canvas.create_text(
            10, 100,
            anchor="nw",
            text="Waiting",
            fill="#aaaaaa",
            font=("Segoe UI", 11)
        )

        card.canvas = canvas
        card.set_status = lambda text: canvas.itemconfigure(card.status_id, text=text)

        # --- Progress bar (CTk) ---
        card.progressbar = ctk.CTkProgressBar(card)
        card.progressbar.set(0)
        canvas.create_window(
            10, 120,
            anchor="nw",
            width=160,
            window=card.progressbar
        )

        # --- Buttons ---
        video_link = entry.get("webpage_url") or entry.get("url") or entry.get("id") or entry.get("webpage_url")

        def on_preview():
            if video_link:
                self.YTDL.STREAM_THREAD_STOP.set()  # Signal any existing stream to stop
                time.sleep(0.5)  # Give it a moment to stop
                threading.Thread(target=self.YTDL.stream_audio, args=(video_link, entry.get("title", ""),), daemon=True).start()

        btn_preview = ctk.CTkButton(card, text="Preview", command=lambda: on_preview())
        canvas.create_window(10, 140, anchor="nw", width=70, window=btn_preview)

        btn_audio = ctk.CTkButton(card, text="Audio", command=lambda l=video_link: self._enqueue_download(l, "audio", card, entry))
        canvas.create_window(160, 140, anchor="nw", width=50, window=btn_audio)

        btn_video = ctk.CTkButton(card, text="Video", command=lambda l=video_link: self._enqueue_download(l, "video", card, entry))
        canvas.create_window(220, 140, anchor="nw", width=50, window=btn_video)

        # --- Rounded rectangle border ---
        def draw_rounded_rect_lines(canvas, x1, y1, x2, y2, r=10, outline="white", width=2):
            # Corners
            canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style="arc", outline=outline, width=width)
            canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style="arc", outline=outline, width=width)
            canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style="arc", outline=outline, width=width)
            canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style="arc", outline=outline, width=width)
            # Lines
            canvas.create_line(x1+r, y1, x2-r, y1, fill=outline, width=width)
            canvas.create_line(x2, y1+r, x2, y2-r, fill=outline, width=width)
            canvas.create_line(x2-r, y2, x1+r, y2, fill=outline, width=width)
            canvas.create_line(x1, y2-r, x1, y1+r, fill=outline, width=width)

        #draw_rounded_rect_lines(canvas, 0, 0, 274, 180, r=6, outline="white", width=6)

        # --- Threaded thumbnail loader ---
        def load_thumbnail():
            # Download image (blocking, in background thread)
            thumbnail_path = self.YTDL.download_thumbnail(entry.get("thumbnails")[0].get("url"))
            if not thumbnail_path:
                return

            pil_img = Image.open(thumbnail_path).resize((300, 180))
            tk_img = ImageTk.PhotoImage(pil_img)

            # Update canvas in main thread
            def update_canvas():
                if not card.winfo_exists() or not canvas.winfo_exists():
                    return
                try:
                    card.thumbnail = canvas.create_image(0, 0, anchor="nw", image=tk_img)
                    card.thumb_img = tk_img  # keep reference
                    canvas.lower(card.thumbnail)
                except tk.TclError:
                    pass

            try:
                canvas.after(0, update_canvas)
            except tk.TclError:
                pass

        threading.Thread(target=load_thumbnail, daemon=True).start()


        # --- Hooks ---
        def set_progress(percent):
            try:
                value = percent
                if isinstance(value, str):
                    value = value.strip().strip('%')
                    value = float(value)/100.0
                else:
                    value = float(value)
                    if value > 1.0:
                        value = value/100.0
                value = max(0.0, min(1.0, value))
            except Exception:
                value = 0.0
            card.progressbar.set(value)

        card.update_progress = set_progress
        card.mark_finished = lambda: canvas.itemconfigure(card.status_id, text="Finished")

        return card


    def populate_results(self, results):
        # Clear old results
        for child in self.search_results_frame.winfo_children():
            child.destroy()

        for i, entry in enumerate(results):
            row = i // 2
            col = i % 2

            card = self.create_result_card(self.search_results_frame, entry)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")









app = Dl_Gui()
app.mainloop()