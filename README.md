# 🎬 YouTube Downloader Pro

A full-featured desktop YouTube downloader built with Python.

It supports video downloads, playlists, channels, search, batch processing, download acceleration, SponsorBlock integration, and a modern dark UI powered by CustomTkinter.

---

# 📋 Table of Contents

- Overview
- Features
- Installation
- Usage
- Configuration
- Code Architecture
- Troubleshooting
- License
- Disclaimer
- Acknowledgments

---

# 📖 Overview

**YouTube Downloader Pro** is a modern desktop application that enables downloading YouTube videos, playlists, and channels with advanced customization and acceleration options.

## 🧩 Tech Stack

| Component | Technology |
|------------|------------|
| GUI Framework | CustomTkinter |
| Download Engine | yt-dlp |
| Image Processing | Pillow |
| Media Processing | FFmpeg |
| Accelerated Downloads | aria2c (optional) |

---

# 🚀 Features

## ✅ Core Functionality

- Single Video Download (even from playlist URLs)
- Playlist Support (selective video picking)
- Batch Downloads
- Built-in YouTube Search with thumbnails
- Download Queue System
- Download History Tracking

---

## 🎞 Quality & Format Options

### Video Quality
- 144p
- 240p
- 360p
- 480p
- 720p
- 1080p
- 1440p (2K)
- 2160p (4K)

### Video Formats
- MP4
- MKV
- WebM
- AVI
- MOV
- FLV

### Audio Formats
- MP3
- M4A
- WAV
- FLAC
- AAC
- OGG
- Opus

### Audio Bitrate
- 96 kbps
- 128 kbps
- 192 kbps
- 256 kbps
- 320 kbps

---

## ⚡ Performance Features

- aria2c integration (16 connections)
- Configurable concurrent fragment downloads (1–32)
- Adjustable buffer size
- Optional speed limiting

---

## 🔥 Advanced Features

- SponsorBlock integration
- Subtitle downloading & embedding
- Thumbnail embedding in audio files
- Browser cookie support (for restricted videos)
- Proxy support (SOCKS5 / HTTP)
- Geo-bypass
- Clipboard auto-detection

---

# 🛠 Installation

## 📌 Prerequisites

- Python 3.8+
- FFmpeg (required)
- aria2c (optional but recommended)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/youtube-downloader-pro.git
cd youtube-downloader-pro
```

---

## Step 2: Create Virtual Environment (Recommended)

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

If no requirements file:

```bash
pip install customtkinter yt-dlp Pillow
```

---

## Step 4: Install FFmpeg

### Windows (Chocolatey)
```bash
choco install ffmpeg
```

### macOS
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

---

## Step 5: Install aria2c (Optional)

### Windows
```bash
choco install aria2
```

### macOS
```bash
brew install aria2
```

### Linux
```bash
sudo apt install aria2
```

---

## Step 6: Run the Application

```bash
python youtube_downloader.py
```

---

# ▶ Usage

1. Launch the app.
2. Paste a YouTube video or playlist URL.
3. Click **Fetch Info**.
4. Select quality & format.
5. Click **Download Now**.
6. Monitor progress, speed, ETA.

---

# ⚙ Configuration

Configuration file: `ytdl_config.json`

Example:

```json
{
    "download_path": "~/Downloads/YouTubeDownloader",
    "theme": "dark",
    "default_video_quality": "Best Quality",
    "default_audio_format": "mp3",
    "use_aria2c": false,
    "concurrent_fragments": 8,
    "proxy": "",
    "geo_bypass": true
}
```

---

# 🏗 Code Architecture

## Project Structure

```
youtube-downloader-pro/
├── youtube_downloader.py
├── ytdl_config.json
├── ytdl_history.json
├── requirements.txt
├── README.md
└── LICENSE
```

The app is built around a main `App` class using CustomTkinter.

Core components:
- Base download options builder
- Real-time progress hook
- Download thread manager
- Async thumbnail loader
- YouTube search engine
- Custom yt-dlp logger
- JSON config manager

---

# 🧯 Troubleshooting

## FFmpeg Not Found

```bash
ffmpeg -version
```

If not installed, reinstall and add to PATH.

---

## yt-dlp Errors

```bash
pip install --upgrade yt-dlp
```

---

## Age Restricted Videos

Enable cookies in configuration:

```json
{
    "use_cookies": true,
    "cookies_browser": "chrome"
}
```

---

## Slow Downloads

Enable aria2c:

```json
{
    "use_aria2c": true,
    "concurrent_fragments": 16
}
```

---

# 📜 License

This project is licensed under the MIT License.

---

# ⚠ Disclaimer

This tool is intended for personal use only.

Respect YouTube’s Terms of Service and copyright laws.  
Do not distribute copyrighted content without permission.

---

# 🙏 Acknowledgments

- yt-dlp
- CustomTkinter
- FFmpeg
- aria2
- Pillow

---

Made with ❤️ using Python
