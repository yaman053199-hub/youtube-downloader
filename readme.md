📋 Table of Contents
Overview
Features
Installation
Usage
Configuration
Code Architecture
Key Code Components
Troubleshooting
License
Overview
YouTube Downloader Pro is a full-featured desktop application built with Python that enables downloading YouTube videos, playlists, and channels. It features a modern GUI built with CustomTkinter, leverages yt-dlp for reliable downloads, and supports advanced features like aria2c acceleration, SponsorBlock integration, and browser cookie import.

Tech Stack
Component	Technology
GUI Framework	CustomTkinter
Download Engine	yt-dlp
Image Processing	Pillow
Media Processing	FFmpeg
Accelerated Downloads	aria2c (optional)
Features
Core Functionality
Single Video Download - Downloads only one video even from playlist URLs
Playlist Support - Download entire playlists with selective video picking
Batch Downloads - Process multiple URLs sequentially
YouTube Search - Search YouTube directly with thumbnail previews
Download Queue - Build and manage download queue
Quality & Format Options
Video Quality: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p (4K)
Video Formats: MP4, MKV, WebM, AVI, MOV, FLV
Audio Formats: MP3, M4A, WAV, FLAC, AAC, OGG, Opus
Audio Bitrate: 96, 128, 192, 256, 320 kbps
Performance Features
aria2c integration (16 concurrent connections)
Configurable concurrent fragment downloads (1-32)
Adjustable buffer size
Optional speed limiting
Advanced Features
SponsorBlock integration
Subtitle download and embedding
Thumbnail embedding in audio files
Browser cookie support for restricted content
Proxy support (SOCKS5/HTTP)
Geo-bypass capability
Clipboard monitoring for auto-detection
Installation
Prerequisites
Python 3.8 or higher
FFmpeg (required for format conversion)
aria2c (optional, for faster downloads)
Step 1: Clone Repository
Bash

git clone https://github.com/yourusername/youtube-downloader-pro.git
cd youtube-downloader-pro
Step 2: Create Virtual Environment (Recommended)
Bash

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
Step 3: Install Python Dependencies
Bash

pip install -r requirements.txt
requirements.txt:

txt

customtkinter>=5.2.0
yt-dlp>=2023.10.13
Pillow>=10.0.0
Or install manually:

Bash

pip install customtkinter yt-dlp Pillow
Step 4: Install FFmpeg
Windows (Chocolatey):

Bash

choco install ffmpeg
Windows (Manual):

PowerShell

# Download from https://ffmpeg.org/download.html
# Extract and add to PATH
$env:Path += ";C:\ffmpeg\bin"
macOS (Homebrew):

Bash

brew install ffmpeg
Linux (Ubuntu/Debian):

Bash

sudo apt update
sudo apt install ffmpeg
Linux (Fedora):

Bash

sudo dnf install ffmpeg
Step 5: Install aria2c (Optional - Recommended)
Windows:

Bash

choco install aria2
macOS:

Bash

brew install aria2
Linux:

Bash

sudo apt install aria2
Step 6: Run the Application
Bash

python youtube_downloader.py
Usage
Basic Download
Bash

# Start the application
python youtube_downloader.py
Paste a YouTube URL in the input field
Click "Fetch Info" to load video details
Select quality (e.g., "1080p Full HD")
Choose format (e.g., "mp4")
Click "Download Now"
Command Line Quick Test
You can test yt-dlp directly:

Bash

# Test video info extraction
python -c "
import yt_dlp
url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
    info = ydl.extract_info(url, download=False)
    print(f'Title: {info[\"title\"]}')
    print(f'Duration: {info[\"duration\"]}s')
"
Batch Download from File
Create a urls.txt file:

txt

https://www.youtube.com/watch?v=video1
https://www.youtube.com/watch?v=video2
https://www.youtube.com/watch?v=video3
Load it in the Batch Download tab or use programmatically:

Python

with open('urls.txt', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]
Configuration
Default Configuration
The application uses a JSON configuration file (ytdl_config.json):

JSON

{
    "download_path": "~/Downloads/YouTubeDownloader",
    "theme": "dark",
    "color_theme": "blue",
    "default_video_quality": "Best Quality",
    "default_audio_format": "mp3",
    "default_video_format": "mp4",
    "embed_thumbnail": true,
    "embed_subtitles": false,
    "subtitle_lang": "en",
    "speed_limit": 0,
    "proxy": "",
    "filename_template": "%(title)s.%(ext)s",
    "sponsor_block": false,
    "geo_bypass": true,
    "clipboard_monitor": false,
    "cookies_browser": "none",
    "use_cookies": false,
    "concurrent_fragments": 8,
    "use_aria2c": false,
    "buffer_size": 1024
}
Configuration Options Explained
Option	Type	Description
download_path	string	Output directory for downloads
theme	string	UI theme ("dark" or "light")
default_video_quality	string	Default quality selection
concurrent_fragments	int	Number of parallel fragment downloads (1-32)
use_aria2c	bool	Enable aria2c for faster downloads
proxy	string	Proxy URL (e.g., "socks5://127.0.0.1:1080")
cookies_browser	string	Browser for cookie extraction
sponsor_block	bool	Enable SponsorBlock segment removal
Quality Mapping
The application maps quality names to yt-dlp format strings:

Python

QUALITY_MAP = {
    "Best Quality": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
    "2160p (4K)": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best",
    "1440p (2K)": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best",
    "1080p (Full HD)": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
    "720p (HD)": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
    "480p (SD)": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "240p": "bestvideo[height<=240]+bestaudio/best[height<=240]",
    "144p": "bestvideo[height<=144]+bestaudio/best[height<=144]",
    "Worst Quality": "worstvideo+worstaudio/worst",
}
Filename Templates
Available template variables:

Python

# Common templates
"%(title)s.%(ext)s"                    # Video Title.mp4
"%(channel)s - %(title)s.%(ext)s"      # Channel Name - Video Title.mp4
"%(upload_date)s - %(title)s.%(ext)s"  # 20240115 - Video Title.mp4
"%(playlist_title)s/%(title)s.%(ext)s" # Playlist Name/Video Title.mp4
Code Architecture
Project Structure
text

youtube-downloader-pro/
├── youtube_downloader.py   # Main application file
├── ytdl_config.json        # Configuration (auto-generated)
├── ytdl_history.json       # Download history (auto-generated)
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
└── LICENSE                 # License file
Class Overview
Python

class App(ctk.CTk):
    """Main application class inheriting from CustomTkinter CTk"""
    
    def __init__(self):
        # Initialize configuration
        # Build UI components
        # Set up logging
        pass
    
    # UI Building Methods
    def _build_ui(self): ...
    def _build_sidebar(self): ...
    def _page_single(self): ...
    def _page_playlist(self): ...
    def _page_batch(self): ...
    def _page_queue(self): ...
    def _page_search(self): ...
    def _page_history(self): ...
    def _page_settings(self): ...
    
    # Download Methods
    def _fetch_info(self): ...
    def _start_single(self): ...
    def _start_playlist(self): ...
    def _start_batch(self): ...
    def _run_queue(self): ...
    
    # Utility Methods
    def _get_base_opts(self, single=False): ...
    def _progress_hook(self, d): ...
    def log(self, msg): ...
Key Code Components
1. Base Download Options Builder
This method constructs yt-dlp options with all configured settings:

Python

def _get_base_opts(self, single=False):
    """Build base yt-dlp options dict with cookies/proxy/etc."""
    opts = {
        "quiet": False,
        "no_warnings": False,
        "logger": YTLogger(self.log),
        "socket_timeout": 30,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "concurrent_fragment_downloads": self.cfg.get("concurrent_fragments", 8),
        "buffersize": self.cfg.get("buffer_size", 1024) * 1024,
        "http_chunk_size": 10485760,
        "ffmpeg_location": r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    }
    
    # KEY FIX: don't download playlist in single mode
    if single:
        opts["noplaylist"] = True
    
    # SPEED: use aria2c if available and enabled
    if self.cfg.get("use_aria2c") and has_aria2c():
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = {
            "aria2c": [
                "--min-split-size=1M",
                "--max-connection-per-server=16",
                "--max-concurrent-downloads=16",
                "--split=16",
                "--file-allocation=none",
                "--optimize-concurrent-downloads=true",
                "--auto-file-renaming=false",
            ]
        }
    
    # Cookies
    if self.cfg.get("use_cookies") and self.cfg.get("cookies_browser", "none") != "none":
        opts["cookiesfrombrowser"] = (self.cfg["cookies_browser"],)
    
    # Proxy
    if self.cfg.get("proxy"):
        opts["proxy"] = self.cfg["proxy"]
    
    # Speed limit
    if self.cfg.get("speed_limit", 0) > 0:
        opts["ratelimit"] = self.cfg["speed_limit"] * 1024
    
    # Geo
    if self.cfg.get("geo_bypass"):
        opts["geo_bypass"] = True
    
    return opts
2. Progress Hook for Real-time Updates
Python

def _progress_hook(self, d):
    """Called by yt-dlp during download to update UI"""
    if self.cancel_flag:
        raise yt_dlp.utils.DownloadError("Cancelled by user")

    st = d.get("status", "")
    if st == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        done = d.get("downloaded_bytes", 0)
        speed = d.get("speed")
        eta = d.get("eta")

        if total and total > 0:
            frac = min(done / total, 1.0)
            self.after(0, lambda f=frac: self.prog_bar.set(f))
            self.after(0, lambda f=frac: self.prog_pct.configure(text=f"{f * 100:.1f} %"))
        if speed:
            self.after(0, lambda s=speed: self.prog_speed.configure(
                text=f"Speed: {fmt_size(s)}/s"))
        if eta is not None:
            self.after(0, lambda e=eta: self.prog_eta.configure(text=f"ETA: {fmt_dur(e)}"))

        self.after(0, lambda d=done, t=total: self.prog_size.configure(
            text=f"{fmt_size(d)} / {fmt_size(t)}"))

    elif st == "finished":
        self.after(0, lambda: self.prog_bar.set(1))
        self.after(0, lambda: self.prog_pct.configure(text="100 %"))
        self.after(0, lambda: self.prog_stat.configure(text="🔧 Post-processing…"))
3. Video Info Fetching
Python

def _t_fetch(self, url):
    """Background thread for fetching video information"""
    try:
        opts = self._get_base_opts(single=True)  # noplaylist=True
        opts["skip_download"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise Exception("yt-dlp returned None")

        # If still a playlist type, pick first entry
        if info.get("_type") == "playlist":
            entries = list(info.get("entries", []))
            if entries and entries[0]:
                vid_url = entries[0].get("webpage_url") or entries[0].get("url", "")
                if vid_url:
                    with yt_dlp.YoutubeDL(opts) as ydl2:
                        info = ydl2.extract_info(vid_url, download=False)
                else:
                    info = entries[0]
            else:
                raise Exception("Empty playlist / no entries found")

        self.current_info = info
        self.after(0, lambda: self._display_info(info))

    except Exception as e:
        self.log(f"[ERROR] {e}")
        if "Sign in" in str(e):
            self.log("[HINT] Enable cookies in Settings → Cookies")
        self.after(0, lambda: self._fetch_error(str(e)))
4. Download Thread for Single Video
Python

def _t_download(self, url):
    """Background thread for downloading a single video"""
    try:
        out = self.out_e.get().strip() or self.cfg["download_path"]
        os.makedirs(out, exist_ok=True)
        is_audio = self.dl_type.get() == "Audio Only"

        opts = self._get_base_opts(single=True)
        opts["outtmpl"] = os.path.join(out, self.cfg["filename_template"])
        opts["progress_hooks"] = [self._progress_hook]

        if is_audio:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.afmt.get(),
                "preferredquality": self.abr.get(),
            }]
            if self.ck_thumb.get():
                opts["writethumbnail"] = True
                opts["postprocessors"].append({"key": "EmbedThumbnail"})
        else:
            q = QUALITY_MAP.get(self.qual_var.get(), "bestvideo+bestaudio/best")
            opts["format"] = q
            opts["merge_output_format"] = self.vfmt.get()

        # SponsorBlock integration
        if self.ck_sb.get():
            opts.setdefault("postprocessors", []).extend([
                {"key": "SponsorBlock"},
                {"key": "ModifyChapters", "remove_sponsor_segments": ["sponsor"]},
            ])

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if self.cancel_flag:
            self.after(0, self._dl_cancelled)
        else:
            self.after(0, lambda: self._dl_ok(info))

    except Exception as e:
        self.after(0, lambda: self._dl_err(str(e)))
5. Async Thumbnail Loading
Python

# Thumbnail cache and executor
_thumb_cache = {}
_thumb_executor = ThreadPoolExecutor(max_workers=6)

def load_thumbnail(url, size=(168, 94), callback=None):
    """Load thumbnail asynchronously with caching"""
    if not url:
        return
    cache_key = f"{url}_{size}"
    if cache_key in _thumb_cache:
        if callback:
            callback(_thumb_cache[cache_key])
        return

    def _load():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).resize(size, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            _thumb_cache[cache_key] = ctk_img
            if callback:
                callback(ctk_img)
        except Exception:
            pass

    _thumb_executor.submit(_load)
6. YouTube Search Implementation
Python

def _t_search(self, query, mx):
    """Background thread for YouTube search"""
    try:
        opts = self._get_base_opts()
        opts["extract_flat"] = True
        opts["skip_download"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch{mx}:{query}", download=False)

        entries = [e for e in res.get("entries", []) if e]
        self.after(0, lambda: self._render_search(entries))
    except Exception as e:
        self.after(0, lambda: self.srch_stat.configure(text=f"❌ {str(e)[:80]}"))
7. Utility Functions
Python

def fmt_size(b):
    """Format bytes to human-readable size"""
    if not b: return "Unknown"
    for u in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


def fmt_dur(s):
    """Format seconds to HH:MM:SS or MM:SS"""
    if not s: return "—"
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def fmt_views(n):
    """Format view count to human-readable (e.g., 1.2M views)"""
    if n is None: return ""
    if n >= 1_000_000_000: return f"{n / 1_000_000_000:.1f}B views"
    if n >= 1_000_000: return f"{n / 1_000_000:.1f}M views"
    if n >= 1_000: return f"{n / 1_000:.1f}K views"
    return f"{n:,} views"


def has_aria2c():
    """Check if aria2c is installed and available"""
    return shutil.which("aria2c") is not None
8. Custom Logger for yt-dlp
Python

class YTLogger:
    """Custom logger to redirect yt-dlp output to app log"""
    def __init__(self, cb):
        self.cb = cb

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.cb(f"[DBG] {msg}")

    def info(self, msg):
        self.cb(f"[INFO] {msg}")

    def warning(self, msg):
        self.cb(f"[WARN] {msg}")

    def error(self, msg):
        self.cb(f"[ERR] {msg}")
9. Configuration Management
Python

@staticmethod
def _load_json(path, default):
    """Load JSON config with defaults fallback"""
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(default, dict):
            for k, v in default.items():
                data.setdefault(k, v)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return default.copy() if isinstance(default, dict) else list(default)

def _save_json(self, path, data):
    """Save data to JSON file"""
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4, default=str)
    except Exception:
        pass
Troubleshooting
Common Issues
FFmpeg not found:

Bash

# Verify FFmpeg installation
ffmpeg -version

# If not found, install and add to PATH
# Windows: Add C:\ffmpeg\bin to system PATH
# Linux/macOS: Usually auto-added via package manager
yt-dlp extraction errors:

Bash

# Update yt-dlp to latest version
pip install --upgrade yt-dlp

# Check current version
python -c "import yt_dlp; print(yt_dlp.version.__version__)"
Age-restricted videos:

Python

# Enable cookie support in config
{
    "use_cookies": true,
    "cookies_browser": "chrome"  # or "firefox", "edge"
}
Slow downloads:

Python

# Enable aria2c acceleration
{
    "use_aria2c": true,
    "concurrent_fragments": 16
}
Proxy configuration:

Python

# Set proxy in config
{
    "proxy": "socks5://127.0.0.1:1080"
}
# Or HTTP proxy
{
    "proxy": "http://user:pass@proxy.example.com:8080"
}
Debug Mode
Add verbose logging:

Python

# Modify _get_base_opts to enable debug
opts = {
    "quiet": False,
    "verbose": True,  # Add this
    "no_warnings": False,
    ...
}
License
This project is licensed under the MIT License.

text

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
Disclaimer
⚠️ This tool is for personal use only. Respect YouTube's Terms of Service and copyright laws. Do not distribute copyrighted content without permission from the content owner.

Acknowledgments
yt-dlp - YouTube download engine
CustomTkinter - Modern UI framework
FFmpeg - Media processing
aria2 - Download accelerator
Pillow - Image processing

Made with ❤️ using Python