📋 Overview
YouTube Downloader Pro is a full-featured desktop application built with Python that makes downloading YouTube videos, playlists, and entire channels incredibly easy. With support for multiple quality options, batch downloads, audio extraction, and advanced features like SponsorBlock integration and aria2c acceleration, it's the complete solution for offline video management.

✨ Features
🎯 Core Functionality
Single Video Download - Download individual videos with one click (automatically filters out playlists)
Playlist Support - Download entire playlists or channels with selective video picking
Batch Downloads - Queue multiple URLs and download them sequentially
YouTube Search - Search YouTube directly from the app with rich video cards and thumbnails
Download Queue - Build a queue of videos and process them later
🎨 Quality & Format Options
Video Quality Selection - From 144p to 4K (2160p)
Multiple Video Formats - MP4, MKV, WebM, AVI, MOV, FLV
Audio Extraction - MP3, M4A, WAV, FLAC, AAC, OGG, Opus
Custom Bitrate - Choose audio quality (96-320 kbps)
Format Merging - Automatic best quality video+audio merging via FFmpeg
⚡ Performance Optimization
aria2c Integration - Up to 16 concurrent connections for ultra-fast downloads
Fragment Downloads - Configurable concurrent fragment downloads (1-32)
Buffer Tuning - Adjustable download buffer size
Speed Limiting - Optional bandwidth throttling
🛠️ Advanced Features
SponsorBlock Integration - Automatically remove sponsor segments
Subtitle Support - Download and embed subtitles (auto-generated or manual)
Thumbnail Embedding - Embed video thumbnails in audio files
Cookie Support - Access age-restricted/private videos via browser cookies
Geo-Bypass - Access region-locked content
Proxy Support - SOCKS5/HTTP proxy configuration
Clipboard Monitor - Auto-detect YouTube URLs from clipboard
📊 UI & UX
Modern Interface - Clean, intuitive design with CustomTkinter
Dark/Light Theme - Toggle between themes
Real-time Progress - Live speed, ETA, and percentage tracking
Video Previews - Thumbnail loading with metadata (views, duration, channel)
Download History - Track all downloads with search and export
Detailed Logging - Console-style log with timestamps
🚀 Installation
Prerequisites
Python 3.8+ (3.10+ recommended)
FFmpeg (required for format conversion)
Quick Install
1️⃣ Clone the Repository
Bash

git clone https://github.com/yourusername/youtube-downloader-pro.git
cd youtube-downloader-pro
2️⃣ Install Dependencies
Bash

pip install -r requirements.txt
requirements.txt:

text

customtkinter>=5.2.0
yt-dlp>=2023.10.13
Pillow>=10.0.0
3️⃣ Install FFmpeg
Windows (via Chocolatey):

Bash

choco install ffmpeg
macOS (via Homebrew):

Bash

brew install ffmpeg
Linux (Ubuntu/Debian):

Bash

sudo apt update
sudo apt install ffmpeg
4️⃣ (Optional) Install aria2c for Faster Downloads
Windows:

Bash

choco install aria2
macOS:

Bash

brew install aria2
Linux:

Bash

sudo apt install aria2
🎮 Usage
Basic Usage
Launch the Application
Bash

python youtube_downloader.py
Download a Single Video

Paste a YouTube URL in the input field
Click "Fetch Info" to preview video details
Select quality and format options
Click "Download Now"
Download a Playlist

Navigate to the Playlist tab
Paste playlist/channel URL
Click "Fetch" to load videos
Select which videos to download
Click "Download Playlist"
Batch Download

Go to Batch Download tab
Paste multiple URLs (one per line)
Configure quality settings
Click "Start Batch"
Search YouTube

Open Search YouTube tab
Enter search query
Browse results with thumbnails
Click "Download" or "Queue" on any result
Advanced Configuration
Open Settings to configure:

Download Path - Where files are saved
Filename Template - Customize output naming (supports %(title)s, %(channel)s, etc.)
Default Formats - Set preferred video/audio formats
Speed Optimization - Enable aria2c, adjust fragments/buffer
Network - Configure proxy, geo-bypass
Cookies - Enable browser cookie import for restricted videos
Post-Processing - Auto-embed thumbnails, subtitles, SponsorBlock
📸 Screenshots
Main Download Interface
text

┌─────────────────────────────────────────────────┐
│  📥  Single Video Download                      │
│  ───────────────────────────────────────────    │
│  🔗 Video URL: [paste URL here...] [Fetch Info] │
│                                                  │
│  📺 Video Information                            │
│  ┌─────────┐  Title: Amazing Video              │
│  │         │  Channel: Cool Creator              │
│  │ PREVIEW │  Duration: 10:35                    │
│  │  IMAGE  │  Views: 1.2M                        │
│  └─────────┘  Quality: 1080p • 45.3 MB          │
│                                                  │
│  ⚙️  Download Options                            │
│  Type: [Video] [Audio Only]                     │
│  Quality: [Best Quality ▼]  Format: [mp4 ▼]    │
│                                                  │
│  📊 Progress: ████████████████░░░░ 75%          │
│  Speed: 5.2 MB/s  •  ETA: 00:08  •  34/45 MB   │
│                                                  │
│  [⬇️ Download Now] [➕ Queue] [⛔ Cancel]        │
└─────────────────────────────────────────────────┘
Search Results
text

┌─────────────────────────────────────────────────┐
│  🔍  Search YouTube                              │
│  [Search Query...................] [🔍 Search]  │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ [THUMBNAIL]  Amazing Tutorial Video      │   │
│  │   10:35      👤 Tech Channel • 1.2M views│   │
│  │              Learn amazing skills in...  │   │
│  │              [⬇️ Download] [➕ Queue]     │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  [More results...]                               │
└─────────────────────────────────────────────────┘
🔧 Configuration Files
ytdl_config.json
Stores all settings (auto-created on first run):

JSON

{
  "download_path": "C:/Users/YourName/Downloads/YouTubeDownloader",
  "theme": "dark",
  "default_video_quality": "Best Quality",
  "concurrent_fragments": 8,
  "use_aria2c": true,
  "embed_thumbnail": true
}
ytdl_history.json
Tracks download history (last 500 items):

JSON

[
  {
    "title": "Amazing Video",
    "url": "https://youtube.com/watch?v=...",
    "timestamp": "2024-01-15T14:30:00",
    "format": "mp4",
    "size": 45678912
  }
]
❓ FAQ
Q: Why is my download slow?
A: Enable aria2c in Settings → Speed Optimization. Increase concurrent fragments to 16-32.

Q: "Sign in to confirm your age" error?
A: Enable Cookies in Settings and select your browser (Chrome/Firefox/Edge).

Q: Can I download age-restricted videos?
A: Yes, enable cookie import from your browser in Settings.

Q: How do I download only audio?
A: Select "Audio Only" in the Type dropdown and choose your preferred format (MP3/M4A/etc).

Q: Can I download entire channels?
A: Yes! Use the Playlist tab and paste the channel URL.

Q: The app won't start on Linux
A: Install Tkinter: sudo apt install python3-tk

Q: How to update yt-dlp?
A: Run pip install --upgrade yt-dlp

🛡️ Troubleshooting
Common Issues
FFmpeg not found:

text

Error: ffmpeg not found
Solution: Install FFmpeg and add to PATH
yt-dlp extraction error:

text

Solution: Update yt-dlp with: pip install --upgrade yt-dlp
HTTP 429 (Too many requests):

text

Solution: Enable proxy or wait a few minutes
Age-restricted video:

text

Solution: Settings → Cookies → Select your browser
🤝 Contributing
Contributions are welcome! Here's how:

Fork the repository
Create a feature branch (git checkout -b feature/AmazingFeature)
Commit changes (git commit -m 'Add AmazingFeature')
Push to branch (git push origin feature/AmazingFeature)
Open a Pull Request
📜 License
This project is licensed under the MIT License - see the LICENSE file for details.

⚠️ Disclaimer
This tool is for personal use only. Respect YouTube's Terms of Service and copyright laws. Do not distribute copyrighted content without permission.

🙏 Acknowledgments
yt-dlp - The powerful YouTube downloader backend
CustomTkinter - Modern UI framework
FFmpeg - Multimedia processing
aria2 - Fast download manager
📞 Support
Issues: GitHub Issues
Discussions: GitHub Discussions
Email: your.email@example.com
<div align="center">
Made with ❤️ by [Your Name]

⭐ Star this repo if you find it useful!

</div>
📝 Changelog
v3.0 (Latest)
✅ Fixed single-mode playlist bug (noplaylist=True)
⚡ Added aria2c support for 10x faster downloads
🎨 Redesigned search UI with YouTube-style cards
🖼️ Async thumbnail loading
📊 Enhanced progress tracking
🔧 Improved error handling
🍪 Browser cookie support for restricted videos
v2.0
Added playlist support
Batch download feature
Search functionality
Download queue
v1.0
Initial release
Basic video download
Audio extraction
Quality selection
🗺️ Roadmap
 Multi-threaded concurrent downloads
 Live stream recording
 Built-in video player preview
 Auto-subtitle translation
 Download scheduler
 Cloud storage integration (Google Drive, Dropbox)
 Mobile app version
 Browser extension
