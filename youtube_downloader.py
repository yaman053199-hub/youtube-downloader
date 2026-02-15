#!/usr/bin/env python3
"""
YouTube Downloader Pro v3.0
Fixed: single-mode playlist bug, slow downloads, plain search UI
"""

import customtkinter as ctk
import yt_dlp
import threading
import os
import sys
import json
import shutil
import traceback
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
from PIL import Image
import urllib.request
import io
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
APP_NAME = "YouTube Downloader Pro"
APP_VERSION = "3.0"
CONFIG_FILE = "ytdl_config.json"
HISTORY_FILE = "ytdl_history.json"

DEFAULT_CONFIG = {
    "download_path": str(Path.home() / "Downloads" / "YouTubeDownloader"),
    "theme": "dark",
    "color_theme": "blue",
    "default_video_quality": "Best Quality",
    "default_audio_format": "mp3",
    "default_video_format": "mp4",
    "embed_thumbnail": True,
    "embed_subtitles": False,
    "subtitle_lang": "en",
    "speed_limit": 0,
    "proxy": "",
    "filename_template": "%(title)s.%(ext)s",
    "sponsor_block": False,
    "geo_bypass": True,
    "clipboard_monitor": False,
    "cookies_browser": "none",
    "use_cookies": False,
    "concurrent_fragments": 8,
    "use_aria2c": False,
    "buffer_size": 1024,
}

VIDEO_QUALITIES = [
    "Best Quality", "2160p (4K)", "1440p (2K)", "1080p (Full HD)",
    "720p (HD)", "480p (SD)", "360p", "240p", "144p", "Worst Quality",
]

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

AUDIO_FORMATS = ["mp3", "m4a", "wav", "flac", "aac", "ogg", "opus"]
VIDEO_FORMATS = ["mp4", "mkv", "webm", "avi", "mov", "flv"]
BROWSER_LIST = ["none", "chrome", "firefox", "edge", "safari", "opera", "brave", "chromium"]


def fmt_size(b):
    if not b: return "Unknown"
    for u in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


def fmt_dur(s):
    if not s: return "—"
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def fmt_views(n):
    if n is None: return ""
    if n >= 1_000_000_000: return f"{n / 1_000_000_000:.1f}B views"
    if n >= 1_000_000: return f"{n / 1_000_000:.1f}M views"
    if n >= 1_000: return f"{n / 1_000:.1f}K views"
    return f"{n:,} views"


def fmt_num(n):
    if n is None: return "Unknown"
    return f"{n:,}"


def has_aria2c():
    return shutil.which("aria2c") is not None


class YTLogger:
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


# thumbnail cache
_thumb_cache = {}
_thumb_executor = ThreadPoolExecutor(max_workers=6)


def load_thumbnail(url, size=(168, 94), callback=None):
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


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.cfg = self._load_json(CONFIG_FILE, DEFAULT_CONFIG)
        self.history = self._load_json(HISTORY_FILE, [])

        ctk.set_appearance_mode(self.cfg.get("theme", "dark"))
        ctk.set_default_color_theme(self.cfg.get("color_theme", "blue"))

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1300x900")
        self.minsize(1100, 750)

        self.download_queue = []
        self.queue_widgets = []
        self.dl_counter = 0
        self.current_info = {}
        self.last_clip = ""
        self.is_downloading = False
        self.cancel_flag = False

        self._build_ui()

        if self.cfg.get("clipboard_monitor"):
            self._poll_clipboard()

        os.makedirs(self.cfg["download_path"], exist_ok=True)

        aria = "✅ aria2c found" if has_aria2c() else "❌ aria2c not found (optional)"
        self.log(f"[INFO] {APP_NAME} v{APP_VERSION} started")
        self.log(f"[INFO] yt-dlp version: {yt_dlp.version.__version__}")
        self.log(f"[INFO] {aria}")
        self.log(f"[INFO] Download path: {self.cfg['download_path']}")

    @staticmethod
    def _load_json(path, default):
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
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=4, default=str)
        except Exception:
            pass

    def _save_cfg(self):
        self._save_json(CONFIG_FILE, self.cfg)

    def _save_hist(self):
        self._save_json(HISTORY_FILE, self.history[-500:])

    def log(self, msg):
        def _do():
            if hasattr(self, "log_box"):
                self.log_box.configure(state="normal")
                ts = datetime.now().strftime("%H:%M:%S")
                self.log_box.insert("end", f"[{ts}] {msg}\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        try:
            self.after(0, _do)
        except Exception:
            print(msg)

    # ══════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()

        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self.pages = {}
        self._page_single()
        self._page_playlist()
        self._page_batch()
        self._page_queue()
        self._page_search()
        self._page_history()
        self._page_settings()
        self._show("single")

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=245, corner_radius=0, fg_color=("gray90", "gray13"))
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_rowconfigure(10, weight=1)
        sb.grid_propagate(False)

        tf = ctk.CTkFrame(sb, fg_color="transparent")
        tf.grid(row=0, column=0, padx=20, pady=(25, 5), sticky="ew")
        ctk.CTkLabel(tf, text="▶  YT Downloader",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(tf, text=f"v{APP_VERSION}  •  Pro Edition",
                     font=ctk.CTkFont(size=11),
                     text_color=("gray50", "gray60")).pack(anchor="w")

        ctk.CTkFrame(sb, height=2, fg_color=("gray70", "gray30")).grid(
            row=1, column=0, padx=20, pady=10, sticky="ew")

        nav = [
            ("📥  Single Download", "single", 2),
            ("📋  Playlist", "playlist", 3),
            ("📦  Batch Download", "batch", 4),
            ("⏳  Queue", "queue", 5),
            ("🔍  Search YouTube", "search", 6),
            ("📜  History", "history", 7),
            ("⚙️  Settings", "settings", 8),
        ]
        self.nav_btns = {}
        for txt, key, r in nav:
            b = ctk.CTkButton(sb, text=txt, font=ctk.CTkFont(size=14),
                              height=44, anchor="w", corner_radius=8,
                              fg_color="transparent",
                              text_color=("gray10", "gray90"),
                              hover_color=("gray75", "gray25"),
                              command=lambda k=key: self._show(k))
            b.grid(row=r, column=0, padx=12, pady=2, sticky="ew")
            self.nav_btns[key] = b

        tf2 = ctk.CTkFrame(sb, fg_color="transparent")
        tf2.grid(row=11, column=0, padx=20, pady=(10, 5), sticky="ew")
        ctk.CTkLabel(tf2, text="Theme:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.theme_sw = ctk.CTkSwitch(tf2, text="Dark", command=self._toggle_theme, width=40)
        self.theme_sw.pack(side="right")
        if self.cfg["theme"] == "dark":
            self.theme_sw.select()

        self.status_lbl = ctk.CTkLabel(sb, text="✅ Ready",
                                        font=ctk.CTkFont(size=11),
                                        text_color=("gray50", "gray60"))
        self.status_lbl.grid(row=12, column=0, padx=20, pady=(0, 15), sticky="ew")

    def _show(self, name):
        for k, b in self.nav_btns.items():
            b.configure(
                fg_color=("gray75", "gray25") if k == name else "transparent",
                font=ctk.CTkFont(size=14, weight="bold" if k == name else "normal"))
        for p in self.pages.values():
            p.grid_forget()
        self.pages[name].grid(row=0, column=0, sticky="nsew")

    def _toggle_theme(self):
        m = "dark" if self.theme_sw.get() else "light"
        ctk.set_appearance_mode(m)
        self.cfg["theme"] = m
        self._save_cfg()

    # ══════════════════════════════════════
    #  BASE OPTIONS  (speed + cookies)
    # ══════════════════════════════════════
    
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
        
        return opts  # ← THIS IS INSIDE THE METHOD

    # ══════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════

    def _paste_to(self, entry):
        try:
            txt = self.clipboard_get().strip()
            if txt:
                entry.delete(0, "end")
                entry.insert(0, txt)
        except Exception:
            pass

    def _browse_out(self):
        d = filedialog.askdirectory()
        if d:
            self.out_e.delete(0, "end")
            self.out_e.insert(0, d)

    def _browse_s_path(self):
        d = filedialog.askdirectory()
        if d:
            self.s_path.delete(0, "end")
            self.s_path.insert(0, d)

    def _open_folder(self):
        d = self.out_e.get() or self.cfg["download_path"]
        os.makedirs(d, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(d)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        except Exception:
            pass

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _on_type_change(self, val):
        is_audio = val == "Audio Only"
        st = "disabled" if is_audio else "normal"
        self.qual_menu.configure(state=st)
        self.vfmt_menu.configure(state=st)

    def _cancel_download(self):
        self.cancel_flag = True
        self.log("[INFO] ⛔ Cancel requested")
        self.prog_stat.configure(text="⛔ Cancelling…")

    def _add_hist(self, info):
        if not info:
            return
        self.history.append({
            "title": info.get("title", "Unknown"),
            "url": info.get("webpage_url") or info.get("original_url", ""),
            "timestamp": datetime.now().isoformat(),
            "format": info.get("ext", "?"),
            "size": info.get("filesize") or info.get("filesize_approx"),
            "duration": info.get("duration"),
            "status": "completed",
        })
        self._save_hist()
        self._refresh_hist()

    # ══════════════════════════════════════
    #  PAGE: SINGLE DOWNLOAD
    # ══════════════════════════════════════

    def _page_single(self):
        p = ctk.CTkScrollableFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["single"] = p
        p.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(p, text="📥  Single Video Download",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 2), sticky="w")
        ctk.CTkLabel(p, text="Downloads only ONE video even from playlist URLs",
                     font=ctk.CTkFont(size=13), text_color=("gray50", "gray60")).grid(
            row=1, column=0, padx=30, pady=(0, 10), sticky="w")

        # URL bar
        uf = ctk.CTkFrame(p)
        uf.grid(row=2, column=0, padx=25, pady=8, sticky="ew")
        uf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(uf, text="🔗  Video URL",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        bar = ctk.CTkFrame(uf, fg_color="transparent")
        bar.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.url_e = ctk.CTkEntry(bar, placeholder_text="https://www.youtube.com/watch?v=...",
                                   height=44, font=ctk.CTkFont(size=13))
        self.url_e.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.url_e.bind("<Return>", lambda _: self._fetch_info())

        ctk.CTkButton(bar, text="📋 Paste", width=85, height=44,
                       command=lambda: self._paste_to(self.url_e)).grid(row=0, column=1, padx=2)
        ctk.CTkButton(bar, text="🗑️", width=44, height=44,
                       fg_color=("gray65", "gray30"),
                       command=lambda: self.url_e.delete(0, "end")).grid(row=0, column=2, padx=2)
        self.fetch_btn = ctk.CTkButton(bar, text="ℹ️  Fetch Info", width=130, height=44,
                                        fg_color="#27ae60", hover_color="#2ecc71",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        command=self._fetch_info)
        self.fetch_btn.grid(row=0, column=3, padx=(5, 0))

        # Info card
        ic = ctk.CTkFrame(p)
        ic.grid(row=3, column=0, padx=25, pady=8, sticky="ew")
        ic.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ic, text="📺  Video Information",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")

        self.thumb_lbl = ctk.CTkLabel(ic, text="No video loaded\n\nPaste URL →\nFetch Info",
                                       width=320, height=180,
                                       fg_color=("gray82", "gray20"), corner_radius=10)
        self.thumb_lbl.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nw")

        det = ctk.CTkFrame(ic, fg_color="transparent")
        det.grid(row=1, column=1, padx=(5, 15), pady=(0, 15), sticky="nsew")
        det.grid_columnconfigure(1, weight=1)

        self.info_labels = {}
        for i, (lab, key) in enumerate([
            ("Title:", "title"), ("Channel:", "channel"),
            ("Duration:", "duration"), ("Views:", "views"),
            ("Likes:", "likes"), ("Upload Date:", "upload_date"),
            ("Resolution:", "resolution"), ("File Size:", "filesize"),
        ]):
            ctk.CTkLabel(det, text=lab, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=("gray40", "gray55")).grid(
                row=i, column=0, sticky="w", padx=(5, 10), pady=3)
            lbl = ctk.CTkLabel(det, text="—", font=ctk.CTkFont(size=12),
                               wraplength=380, anchor="w", justify="left")
            lbl.grid(row=i, column=1, sticky="w", padx=5, pady=3)
            self.info_labels[key] = lbl

        # Options
        of = ctk.CTkFrame(p)
        of.grid(row=4, column=0, padx=25, pady=8, sticky="ew")
        of.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(of, text="⚙️  Download Options",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=15, pady=(12, 8), sticky="w")

        ctk.CTkLabel(of, text="Type:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.dl_type = ctk.CTkSegmentedButton(of, values=["Video", "Audio Only"],
                                               command=self._on_type_change)
        self.dl_type.grid(row=1, column=1, columnspan=3, padx=15, pady=5, sticky="ew")
        self.dl_type.set("Video")

        ctk.CTkLabel(of, text="Quality:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.qual_var = ctk.StringVar(value=self.cfg["default_video_quality"])
        self.qual_menu = ctk.CTkOptionMenu(of, variable=self.qual_var, values=VIDEO_QUALITIES)
        self.qual_menu.grid(row=2, column=1, padx=15, pady=5, sticky="ew")

        ctk.CTkLabel(of, text="Video Fmt:").grid(row=2, column=2, padx=15, pady=5, sticky="w")
        self.vfmt = ctk.StringVar(value=self.cfg["default_video_format"])
        self.vfmt_menu = ctk.CTkOptionMenu(of, variable=self.vfmt, values=VIDEO_FORMATS)
        self.vfmt_menu.grid(row=2, column=3, padx=15, pady=5, sticky="ew")

        ctk.CTkLabel(of, text="Audio Fmt:").grid(row=3, column=0, padx=15, pady=5, sticky="w")
        self.afmt = ctk.StringVar(value=self.cfg["default_audio_format"])
        self.afmt_menu = ctk.CTkOptionMenu(of, variable=self.afmt, values=AUDIO_FORMATS)
        self.afmt_menu.grid(row=3, column=1, padx=15, pady=5, sticky="ew")

        ctk.CTkLabel(of, text="Bitrate:").grid(row=3, column=2, padx=15, pady=5, sticky="w")
        self.abr = ctk.StringVar(value="192")
        ctk.CTkOptionMenu(of, variable=self.abr,
                           values=["320", "256", "192", "128", "96"]).grid(
            row=3, column=3, padx=15, pady=5, sticky="ew")

        ck = ctk.CTkFrame(of, fg_color="transparent")
        ck.grid(row=4, column=0, columnspan=4, padx=15, pady=(8, 12), sticky="ew")
        self.ck_thumb = ctk.BooleanVar(value=self.cfg["embed_thumbnail"])
        self.ck_esub = ctk.BooleanVar(value=self.cfg["embed_subtitles"])
        self.ck_sthumb = ctk.BooleanVar(value=False)
        self.ck_dsub = ctk.BooleanVar(value=False)
        self.ck_sb = ctk.BooleanVar(value=self.cfg["sponsor_block"])
        for txt, var in [("Embed Thumb", self.ck_thumb), ("Embed Subs", self.ck_esub),
                         ("Save Thumb", self.ck_sthumb), ("Download Subs", self.ck_dsub),
                         ("SponsorBlock", self.ck_sb)]:
            ctk.CTkCheckBox(ck, text=txt, variable=var).pack(side="left", padx=8)

        # Output
        od = ctk.CTkFrame(p)
        od.grid(row=5, column=0, padx=25, pady=8, sticky="ew")
        od.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(od, text="📁", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=(15, 5), pady=12)
        self.out_e = ctk.CTkEntry(od, height=38)
        self.out_e.grid(row=0, column=1, padx=5, pady=12, sticky="ew")
        self.out_e.insert(0, self.cfg["download_path"])
        ctk.CTkButton(od, text="Browse", width=80, height=38,
                       command=self._browse_out).grid(row=0, column=2, padx=(5, 15), pady=12)

        # Progress
        pf = ctk.CTkFrame(p)
        pf.grid(row=6, column=0, padx=25, pady=8, sticky="ew")
        pf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pf, text="📊  Progress",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        self.prog_bar = ctk.CTkProgressBar(pf, height=22, corner_radius=8)
        self.prog_bar.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.prog_bar.set(0)

        pi = ctk.CTkFrame(pf, fg_color="transparent")
        pi.grid(row=2, column=0, padx=15, pady=(0, 3), sticky="ew")
        pi.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.prog_pct = ctk.CTkLabel(pi, text="0 %", font=ctk.CTkFont(size=12, weight="bold"))
        self.prog_speed = ctk.CTkLabel(pi, text="Speed: —")
        self.prog_eta = ctk.CTkLabel(pi, text="ETA: —")
        self.prog_size = ctk.CTkLabel(pi, text="Size: —")
        self.prog_pct.grid(row=0, column=0, sticky="w")
        self.prog_speed.grid(row=0, column=1)
        self.prog_eta.grid(row=0, column=2)
        self.prog_size.grid(row=0, column=3, sticky="e")

        self.prog_stat = ctk.CTkLabel(pf, text="Ready — paste a URL and click Fetch Info",
                                       font=ctk.CTkFont(size=12),
                                       text_color=("gray50", "gray60"))
        self.prog_stat.grid(row=3, column=0, padx=15, pady=(0, 12), sticky="w")

        # Buttons
        bf = ctk.CTkFrame(p, fg_color="transparent")
        bf.grid(row=7, column=0, padx=25, pady=(5, 5), sticky="ew")

        self.dl_btn = ctk.CTkButton(bf, text="⬇️  Download Now", height=50, width=200,
                                     font=ctk.CTkFont(size=15, weight="bold"),
                                     fg_color="#e74c3c", hover_color="#c0392b",
                                     command=self._start_single)
        self.dl_btn.pack(side="left", padx=5)
        ctk.CTkButton(bf, text="➕ Queue", height=50, width=120,
                       fg_color=("gray55", "gray30"),
                       command=self._enqueue_single).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="⛔ Cancel", height=50, width=100,
                       fg_color="#e67e22", hover_color="#d35400",
                       command=self._cancel_download).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="📂 Open", height=50, width=100,
                       fg_color=("gray55", "gray30"),
                       command=self._open_folder).pack(side="right", padx=5)

        # Log
        lf = ctk.CTkFrame(p)
        lf.grid(row=8, column=0, padx=25, pady=(8, 20), sticky="ew")
        lf.grid_columnconfigure(0, weight=1)
        hdr = ctk.CTkFrame(lf, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="ew")
        ctk.CTkLabel(hdr, text="📋 Log", font=ctk.CTkFont(size=14, weight="bold")).pack(
            side="left")
        ctk.CTkButton(hdr, text="Clear", width=60, height=28,
                       fg_color=("gray65", "gray30"),
                       command=self._clear_log).pack(side="right")
        self.log_box = ctk.CTkTextbox(lf, height=140,
                                       font=ctk.CTkFont(family="Consolas", size=11),
                                       state="disabled")
        self.log_box.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="ew")

    # ══════════════════════════════════════
    #  PAGE: PLAYLIST
    # ══════════════════════════════════════

    def _page_playlist(self):
        p = ctk.CTkScrollableFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["playlist"] = p
        p.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(p, text="📋  Playlist Download",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 2), sticky="w")
        ctk.CTkLabel(p, text="Download entire playlists or channels",
                     font=ctk.CTkFont(size=13), text_color=("gray50", "gray60")).grid(
            row=1, column=0, padx=30, pady=(0, 10), sticky="w")

        uf = ctk.CTkFrame(p)
        uf.grid(row=2, column=0, padx=25, pady=8, sticky="ew")
        uf.grid_columnconfigure(0, weight=1)
        bar = ctk.CTkFrame(uf, fg_color="transparent")
        bar.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.pl_url = ctk.CTkEntry(bar, placeholder_text="Paste playlist / channel URL…",
                                    height=44, font=ctk.CTkFont(size=13))
        self.pl_url.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.pl_url.bind("<Return>", lambda _: self._fetch_playlist())
        ctk.CTkButton(bar, text="📋", width=44, height=44,
                       command=lambda: self._paste_to(self.pl_url)).grid(row=0, column=1, padx=2)
        self.pl_fetch_btn = ctk.CTkButton(bar, text="🔍 Fetch", width=120, height=44,
                                           fg_color="#27ae60", hover_color="#2ecc71",
                                           command=self._fetch_playlist)
        self.pl_fetch_btn.grid(row=0, column=2, padx=2)

        self.pl_info_lbl = ctk.CTkLabel(p, text="No playlist loaded",
                                         text_color=("gray50", "gray60"))
        self.pl_info_lbl.grid(row=3, column=0, padx=30, pady=5, sticky="w")

        lf = ctk.CTkFrame(p)
        lf.grid(row=4, column=0, padx=25, pady=8, sticky="ew")
        lf.grid_columnconfigure(0, weight=1)

        sb = ctk.CTkFrame(lf, fg_color="transparent")
        sb.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="ew")
        ctk.CTkLabel(sb, text="📋 Videos",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(sb, text="✅ All", width=80, height=30,
                       command=self._pl_sel_all).pack(side="right", padx=5)
        ctk.CTkButton(sb, text="❌ None", width=80, height=30,
                       command=self._pl_desel_all).pack(side="right", padx=5)

        self.pl_scroll = ctk.CTkScrollableFrame(lf, height=250)
        self.pl_scroll.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="ew")
        self.pl_scroll.grid_columnconfigure(0, weight=1)
        self.pl_cbs = []
        self.pl_entries = []

        of = ctk.CTkFrame(p)
        of.grid(row=5, column=0, padx=25, pady=8, sticky="ew")
        of.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(of, text="Quality:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.pl_q = ctk.StringVar(value="Best Quality")
        ctk.CTkOptionMenu(of, variable=self.pl_q, values=VIDEO_QUALITIES).grid(
            row=0, column=1, padx=15, pady=10, sticky="ew")
        ctk.CTkLabel(of, text="Format:").grid(row=0, column=2, padx=15, pady=10, sticky="w")
        self.pl_f = ctk.StringVar(value="mp4")
        ctk.CTkOptionMenu(of, variable=self.pl_f,
                           values=VIDEO_FORMATS + AUDIO_FORMATS).grid(
            row=0, column=3, padx=15, pady=10, sticky="ew")

        self.pl_prog = ctk.CTkProgressBar(p, height=20)
        self.pl_prog.grid(row=6, column=0, padx=25, pady=5, sticky="ew")
        self.pl_prog.set(0)
        self.pl_stat = ctk.CTkLabel(p, text="Ready", text_color=("gray50", "gray60"))
        self.pl_stat.grid(row=7, column=0, padx=30, pady=5, sticky="w")

        ctk.CTkButton(p, text="⬇️  Download Playlist", height=50, width=220,
                       font=ctk.CTkFont(size=15, weight="bold"),
                       fg_color="#e74c3c", hover_color="#c0392b",
                       command=self._start_playlist).grid(
            row=8, column=0, padx=25, pady=(10, 25), sticky="w")

    # ══════════════════════════════════════
    #  PAGE: BATCH
    # ══════════════════════════════════════

    def _page_batch(self):
        p = ctk.CTkScrollableFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["batch"] = p
        p.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(p, text="📦  Batch Download",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 2), sticky="w")
        ctk.CTkLabel(p, text="One URL per line",
                     font=ctk.CTkFont(size=13), text_color=("gray50", "gray60")).grid(
            row=1, column=0, padx=30, pady=(0, 10), sticky="w")

        uf = ctk.CTkFrame(p)
        uf.grid(row=2, column=0, padx=25, pady=8, sticky="ew")
        uf.grid_columnconfigure(0, weight=1)
        self.batch_txt = ctk.CTkTextbox(uf, height=200, font=ctk.CTkFont(size=12))
        self.batch_txt.grid(row=0, column=0, padx=15, pady=15, sticky="ew")

        br = ctk.CTkFrame(uf, fg_color="transparent")
        br.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="ew")
        ctk.CTkButton(br, text="📋 Paste", width=100, height=34,
                       command=lambda: self.batch_txt.insert("end",
                                                              self.clipboard_get() + "\n")).pack(
            side="left", padx=5)
        ctk.CTkButton(br, text="📂 Load", width=100, height=34,
                       command=self._load_batch_file).pack(side="left", padx=5)
        ctk.CTkButton(br, text="🗑️ Clear", width=80, height=34,
                       fg_color=("gray55", "gray30"),
                       command=lambda: self.batch_txt.delete("1.0", "end")).pack(
            side="left", padx=5)

        of = ctk.CTkFrame(p)
        of.grid(row=3, column=0, padx=25, pady=8, sticky="ew")
        of.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(of, text="Quality:").grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.ba_q = ctk.StringVar(value="Best Quality")
        ctk.CTkOptionMenu(of, variable=self.ba_q, values=VIDEO_QUALITIES).grid(
            row=0, column=1, padx=15, pady=10, sticky="ew")
        ctk.CTkLabel(of, text="Format:").grid(row=0, column=2, padx=15, pady=10, sticky="w")
        self.ba_f = ctk.StringVar(value="mp4")
        ctk.CTkOptionMenu(of, variable=self.ba_f,
                           values=VIDEO_FORMATS + AUDIO_FORMATS).grid(
            row=0, column=3, padx=15, pady=10, sticky="ew")

        self.ba_prog = ctk.CTkProgressBar(p, height=20)
        self.ba_prog.grid(row=4, column=0, padx=25, pady=5, sticky="ew")
        self.ba_prog.set(0)
        self.ba_stat = ctk.CTkLabel(p, text="Ready", text_color=("gray50", "gray60"))
        self.ba_stat.grid(row=5, column=0, padx=30, pady=5, sticky="w")

        self.ba_log = ctk.CTkTextbox(p, height=180, font=ctk.CTkFont(family="Consolas", size=11))
        self.ba_log.grid(row=6, column=0, padx=25, pady=8, sticky="ew")

        ctk.CTkButton(p, text="⬇️  Start Batch", height=50, width=200,
                       font=ctk.CTkFont(size=15, weight="bold"),
                       fg_color="#e74c3c", hover_color="#c0392b",
                       command=self._start_batch).grid(
            row=7, column=0, padx=25, pady=(10, 25), sticky="w")

    def _load_batch_file(self):
        f = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if f:
            with open(f) as fh:
                self.batch_txt.insert("end", fh.read())

    # ══════════════════════════════════════
    #  PAGE: QUEUE
    # ══════════════════════════════════════

    def _page_queue(self):
        p = ctk.CTkFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["queue"] = p
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(p, text="⏳  Download Queue",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 10), sticky="w")

        cf = ctk.CTkFrame(p, fg_color="transparent")
        cf.grid(row=1, column=0, padx=25, pady=8, sticky="ew")
        ctk.CTkButton(cf, text="▶ Start", width=110, height=38,
                       fg_color="#27ae60", hover_color="#2ecc71",
                       command=self._run_queue).pack(side="left", padx=5)
        ctk.CTkButton(cf, text="🗑️ Clear", width=100, height=38,
                       fg_color=("gray55", "gray30"),
                       command=self._clear_queue).pack(side="left", padx=5)
        self.q_cnt = ctk.CTkLabel(cf, text="0 items", font=ctk.CTkFont(size=13))
        self.q_cnt.pack(side="right", padx=15)

        self.q_scroll = ctk.CTkScrollableFrame(p)
        self.q_scroll.grid(row=2, column=0, padx=25, pady=10, sticky="nsew")
        self.q_scroll.grid_columnconfigure(0, weight=1)

    # ══════════════════════════════════════
    #  PAGE: SEARCH  (YouTube-style cards)
    # ══════════════════════════════════════

    def _page_search(self):
        p = ctk.CTkFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["search"] = p
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(p, text="🔍  Search YouTube",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 10), sticky="w")

        # Search bar
        sf = ctk.CTkFrame(p, fg_color=("gray88", "gray17"), corner_radius=12)
        sf.grid(row=1, column=0, padx=25, pady=(0, 8), sticky="ew")
        sf.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(sf, fg_color="transparent")
        bar.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.srch_e = ctk.CTkEntry(bar, placeholder_text="Search YouTube videos…",
                                    height=48, font=ctk.CTkFont(size=14),
                                    corner_radius=10)
        self.srch_e.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.srch_e.bind("<Return>", lambda _: self._do_search())

        ctk.CTkLabel(bar, text="Max:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=1, padx=(5, 3))
        self.srch_max = ctk.CTkEntry(bar, width=55, height=48, corner_radius=10)
        self.srch_max.grid(row=0, column=2, padx=(0, 8))
        self.srch_max.insert(0, "15")

        self.srch_btn = ctk.CTkButton(bar, text="🔍 Search", width=120, height=48,
                                       fg_color="#e74c3c", hover_color="#c0392b",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       corner_radius=10,
                                       command=self._do_search)
        self.srch_btn.grid(row=0, column=3)

        self.srch_stat = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=12),
                                       text_color=("gray50", "gray60"))
        self.srch_stat.grid(row=2, column=0, padx=30, pady=(2, 5), sticky="w")

        # Results scroll
        self.srch_scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.srch_scroll.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="nsew")
        self.srch_scroll.grid_columnconfigure(0, weight=1)

    # ══════════════════════════════════════
    #  PAGE: HISTORY
    # ══════════════════════════════════════

    def _page_history(self):
        p = ctk.CTkFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["history"] = p
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(p, text="📜  Download History",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 10), sticky="w")

        hc = ctk.CTkFrame(p, fg_color="transparent")
        hc.grid(row=1, column=0, padx=25, pady=8, sticky="ew")
        self.hist_search = ctk.CTkEntry(hc, placeholder_text="🔍 Filter…",
                                         height=36, width=300)
        self.hist_search.pack(side="left")
        self.hist_search.bind("<KeyRelease>", lambda _: self._filter_hist())
        ctk.CTkButton(hc, text="🗑️ Clear", width=90, height=36,
                       fg_color=("gray55", "gray30"),
                       command=self._clear_hist).pack(side="right", padx=5)
        ctk.CTkButton(hc, text="📤 Export", width=90, height=36,
                       command=self._export_hist).pack(side="right", padx=5)
        self.hist_cnt = ctk.CTkLabel(hc, text=f"{len(self.history)} items")
        self.hist_cnt.pack(side="right", padx=15)

        self.hist_scroll = ctk.CTkScrollableFrame(p)
        self.hist_scroll.grid(row=2, column=0, padx=25, pady=8, sticky="nsew")
        self.hist_scroll.grid_columnconfigure(0, weight=1)
        self._refresh_hist()

    # ══════════════════════════════════════
    #  PAGE: SETTINGS
    # ══════════════════════════════════════

    def _page_settings(self):
        p = ctk.CTkScrollableFrame(self.main, corner_radius=0, fg_color="transparent")
        self.pages["settings"] = p
        p.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(p, text="⚙️  Settings",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=30, pady=(25, 15), sticky="w")
        r = 1

        # General
        gf = ctk.CTkFrame(p)
        gf.grid(row=r, column=0, padx=25, pady=8, sticky="ew"); r += 1
        gf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(gf, text="📁 General",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")

        ctk.CTkLabel(gf, text="Download Path:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        pf = ctk.CTkFrame(gf, fg_color="transparent")
        pf.grid(row=1, column=1, padx=15, pady=5, sticky="ew")
        pf.grid_columnconfigure(0, weight=1)
        self.s_path = ctk.CTkEntry(pf, height=36)
        self.s_path.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.s_path.insert(0, self.cfg["download_path"])
        ctk.CTkButton(pf, text="…", width=40, height=36,
                       command=self._browse_s_path).grid(row=0, column=1)

        ctk.CTkLabel(gf, text="Filename:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.s_tpl = ctk.CTkEntry(gf, height=36)
        self.s_tpl.grid(row=2, column=1, padx=15, pady=5, sticky="ew")
        self.s_tpl.insert(0, self.cfg["filename_template"])

        ctk.CTkLabel(gf, text="  %(title)s %(id)s %(channel)s %(ext)s",
                     font=ctk.CTkFont(size=10), text_color=("gray50", "gray60")).grid(
            row=3, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="w")

        # Defaults
        df = ctk.CTkFrame(p)
        df.grid(row=r, column=0, padx=25, pady=8, sticky="ew"); r += 1
        df.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(df, text="🎬 Defaults",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=15, pady=(12, 8), sticky="w")
        ctk.CTkLabel(df, text="Video:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.s_vfmt = ctk.CTkOptionMenu(df, values=VIDEO_FORMATS)
        self.s_vfmt.grid(row=1, column=1, padx=15, pady=5, sticky="ew")
        self.s_vfmt.set(self.cfg["default_video_format"])
        ctk.CTkLabel(df, text="Audio:").grid(row=1, column=2, padx=15, pady=5, sticky="w")
        self.s_afmt = ctk.CTkOptionMenu(df, values=AUDIO_FORMATS)
        self.s_afmt.grid(row=1, column=3, padx=15, pady=5, sticky="ew")
        self.s_afmt.set(self.cfg["default_audio_format"])
        ctk.CTkLabel(df, text="Quality:").grid(row=2, column=0, padx=15, pady=(5, 12), sticky="w")
        self.s_qual = ctk.CTkOptionMenu(df, values=VIDEO_QUALITIES)
        self.s_qual.grid(row=2, column=1, padx=15, pady=(5, 12), sticky="ew")
        self.s_qual.set(self.cfg["default_video_quality"])

        # ⚡ Speed
        spf = ctk.CTkFrame(p)
        spf.grid(row=r, column=0, padx=25, pady=8, sticky="ew"); r += 1
        spf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(spf, text="⚡ Speed Optimization",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")

        ctk.CTkLabel(spf, text="Concurrent Fragments:").grid(
            row=1, column=0, padx=15, pady=5, sticky="w")
        cf2 = ctk.CTkFrame(spf, fg_color="transparent")
        cf2.grid(row=1, column=1, padx=15, pady=5, sticky="w")
        self.s_frag = ctk.CTkSlider(cf2, from_=1, to=32, number_of_steps=31, width=250)
        self.s_frag.pack(side="left")
        self.s_frag.set(self.cfg.get("concurrent_fragments", 8))
        self.s_frag_lbl = ctk.CTkLabel(cf2, text=str(self.cfg.get("concurrent_fragments", 8)),
                                        font=ctk.CTkFont(size=13, weight="bold"))
        self.s_frag_lbl.pack(side="left", padx=10)
        self.s_frag.configure(
            command=lambda v: self.s_frag_lbl.configure(text=str(int(v))))

        self.s_aria2c = ctk.BooleanVar(value=self.cfg.get("use_aria2c", False))
        aria_text = "Use aria2c (16 connections — MUCH faster)"
        if not has_aria2c():
            aria_text += "  ⚠️ NOT INSTALLED"
        ctk.CTkCheckBox(spf, text=aria_text, variable=self.s_aria2c).grid(
            row=2, column=0, columnspan=2, padx=15, pady=3, sticky="w")

        ctk.CTkLabel(spf, text="Buffer Size (KB):").grid(
            row=3, column=0, padx=15, pady=5, sticky="w")
        self.s_buf = ctk.CTkEntry(spf, width=100, height=36)
        self.s_buf.grid(row=3, column=1, padx=15, pady=5, sticky="w")
        self.s_buf.insert(0, str(self.cfg.get("buffer_size", 1024)))

        ctk.CTkLabel(spf, text="Speed Limit (KB/s, 0=∞):").grid(
            row=4, column=0, padx=15, pady=(5, 12), sticky="w")
        self.s_speed = ctk.CTkEntry(spf, width=100, height=36)
        self.s_speed.grid(row=4, column=1, padx=15, pady=(5, 12), sticky="w")
        self.s_speed.insert(0, str(self.cfg.get("speed_limit", 0)))

        # Network
        nf = ctk.CTkFrame(p)
        nf.grid(row=r, column=0, padx=25, pady=8, sticky="ew"); r += 1
        nf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(nf, text="🌐 Network",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")
        ctk.CTkLabel(nf, text="Proxy:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.s_proxy = ctk.CTkEntry(nf, height=36, placeholder_text="socks5://127.0.0.1:1080")
        self.s_proxy.grid(row=1, column=1, padx=15, pady=5, sticky="ew")
        self.s_proxy.insert(0, self.cfg.get("proxy", ""))
        self.s_geo = ctk.BooleanVar(value=self.cfg["geo_bypass"])
        ctk.CTkCheckBox(nf, text="Geo Bypass", variable=self.s_geo).grid(
            row=2, column=0, columnspan=2, padx=15, pady=(5, 12), sticky="w")

        # Cookies
        cf = ctk.CTkFrame(p)
        cf.grid(row=r, column=0, padx=25, pady=8, sticky="ew"); r += 1
        cf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cf, text="🍪 Cookies",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")
        self.s_use_cookies = ctk.BooleanVar(value=self.cfg.get("use_cookies", False))
        ctk.CTkCheckBox(cf, text="Use browser cookies", variable=self.s_use_cookies).grid(
            row=1, column=0, padx=15, pady=5, sticky="w")
        ctk.CTkLabel(cf, text="Browser:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.s_cookies_browser = ctk.CTkOptionMenu(cf, values=BROWSER_LIST, width=160)
        self.s_cookies_browser.grid(row=2, column=1, padx=15, pady=(5, 12), sticky="w")
        self.s_cookies_browser.set(self.cfg.get("cookies_browser", "none"))

        # Post-processing
        ppf = ctk.CTkFrame(p)
        ppf.grid(row=r, column=0, padx=25, pady=8, sticky="ew"); r += 1
        ctk.CTkLabel(ppf, text="🔧 Post-Processing",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")
        self.s_ethumb = ctk.BooleanVar(value=self.cfg["embed_thumbnail"])
        self.s_esub = ctk.BooleanVar(value=self.cfg["embed_subtitles"])
        self.s_sb = ctk.BooleanVar(value=self.cfg["sponsor_block"])
        self.s_clip = ctk.BooleanVar(value=self.cfg["clipboard_monitor"])
        for i, (txt, var) in enumerate([
            ("Embed thumbnail in audio", self.s_ethumb),
            ("Embed subtitles in video", self.s_esub),
            ("SponsorBlock (remove sponsors)", self.s_sb),
            ("Monitor clipboard for URLs", self.s_clip),
        ], 1):
            ctk.CTkCheckBox(ppf, text=txt, variable=var).grid(
                row=i, column=0, columnspan=2, padx=15, pady=3, sticky="w")
        ctk.CTkLabel(ppf, text="Subtitle Lang:").grid(
            row=5, column=0, padx=15, pady=(8, 12), sticky="w")
        self.s_slang = ctk.CTkEntry(ppf, width=80, height=36)
        self.s_slang.grid(row=5, column=1, padx=15, pady=(8, 12), sticky="w")
        self.s_slang.insert(0, self.cfg["subtitle_lang"])

        ctk.CTkButton(p, text="💾  Save Settings", height=50, width=180,
                       font=ctk.CTkFont(size=15, weight="bold"),
                       fg_color="#27ae60", hover_color="#2ecc71",
                       command=self._save_settings).grid(
            row=r, column=0, padx=25, pady=(15, 30), sticky="w")

    # ══════════════════════════════════════
    #  FETCH INFO  (noplaylist=True)
    # ══════════════════════════════════════

    def _fetch_info(self):
        url = self.url_e.get().strip()
        if not url:
            messagebox.showwarning("Input", "Paste a URL first!")
            return

        self.log(f"[INFO] Fetching: {url}")
        self.prog_stat.configure(text="⏳ Fetching video info…")
        self.status_lbl.configure(text="⏳ Fetching…")
        self.fetch_btn.configure(state="disabled", text="⏳ Fetching…")

        threading.Thread(target=self._t_fetch, args=(url,), daemon=True).start()

    def _t_fetch(self, url):
        try:
            opts = self._get_base_opts(single=True)  # ← noplaylist=True
            opts["skip_download"] = True

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise Exception("yt-dlp returned None")

            # If still a playlist type, pick first entry
            if info.get("_type") == "playlist":
                entries = list(info.get("entries", []))
                if entries and entries[0]:
                    # Re-fetch full info for the single video
                    vid_url = entries[0].get("webpage_url") or entries[0].get("url", "")
                    if vid_url:
                        with yt_dlp.YoutubeDL(opts) as ydl2:
                            info = ydl2.extract_info(vid_url, download=False)
                    else:
                        info = entries[0]
                else:
                    raise Exception("Empty playlist / no entries found")

            self.current_info = info
            self.log(f"[INFO] ✅ {info.get('title', '?')}")
            self.after(0, lambda: self._display_info(info))

        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.log(traceback.format_exc())
            if "Sign in" in str(e):
                self.log("[HINT] Enable cookies in Settings → Cookies")
            self.after(0, lambda: self._fetch_error(str(e)))

    def _display_info(self, info):
        self.fetch_btn.configure(state="normal", text="ℹ️  Fetch Info")
        self.status_lbl.configure(text="✅ Ready")
        self.prog_stat.configure(text="✅ Video info loaded — ready to download!")

        self.info_labels["title"].configure(text=info.get("title", "Unknown"))
        self.info_labels["channel"].configure(
            text=info.get("channel") or info.get("uploader") or "?")
        self.info_labels["duration"].configure(text=fmt_dur(info.get("duration")))
        self.info_labels["views"].configure(text=fmt_num(info.get("view_count")))
        self.info_labels["likes"].configure(text=fmt_num(info.get("like_count")))

        ud = info.get("upload_date", "")
        if ud:
            try:
                ud = datetime.strptime(ud, "%Y%m%d").strftime("%B %d, %Y")
            except Exception:
                pass
        self.info_labels["upload_date"].configure(text=ud or "?")

        w, h = info.get("width"), info.get("height")
        self.info_labels["resolution"].configure(
            text=f"{w}×{h}" if w and h else info.get("resolution", "?"))

        fs = info.get("filesize") or info.get("filesize_approx")
        self.info_labels["filesize"].configure(text=fmt_size(fs))

        thumb = info.get("thumbnail")
        if thumb:
            def set_thumb(img):
                self.after(0, lambda: self.thumb_lbl.configure(image=img, text=""))
            load_thumbnail(thumb, (320, 180), set_thumb)
        else:
            self.thumb_lbl.configure(text="No thumbnail", image=None if hasattr(ctk.CTkLabel, 'image') else "")

    def _fetch_error(self, msg):
        self.fetch_btn.configure(state="normal", text="ℹ️  Fetch Info")
        self.status_lbl.configure(text="❌ Error")
        self.prog_stat.configure(text=f"❌ {msg[:100]}")
        hint = ""
        if "Sign in" in msg:
            hint = "\n\n💡 Enable cookies: Settings → Cookies"
        messagebox.showerror("Fetch Error", f"{msg[:300]}{hint}")

    # ══════════════════════════════════════
    #  SINGLE DOWNLOAD  (noplaylist=True + fast)
    # ══════════════════════════════════════

    def _start_single(self):
        url = self.url_e.get().strip()
        if not url:
            messagebox.showwarning("Input", "Enter a URL!")
            return
        if self.is_downloading:
            messagebox.showinfo("Busy", "Download in progress.")
            return

        self.is_downloading = True
        self.cancel_flag = False
        self.dl_btn.configure(state="disabled", text="⏳ Downloading…")
        self.prog_bar.set(0)
        self.prog_pct.configure(text="0 %")
        self.prog_speed.configure(text="Speed: —")
        self.prog_eta.configure(text="ETA: —")
        self.prog_size.configure(text="Size: —")
        self.prog_stat.configure(text="⏳ Starting…")
        self.status_lbl.configure(text="⬇️ Downloading")

        self.log(f"[INFO] ⬇️ Starting: {url}")
        threading.Thread(target=self._t_download, args=(url,), daemon=True).start()

    def _t_download(self, url):
        try:
            out = self.out_e.get().strip() or self.cfg["download_path"]
            os.makedirs(out, exist_ok=True)
            is_audio = self.dl_type.get() == "Audio Only"

            # ── KEY: single=True → noplaylist=True ──
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
                if self.ck_esub.get():
                    opts.setdefault("postprocessors", []).append(
                        {"key": "FFmpegEmbedSubtitle"})
                    opts["writesubtitles"] = True
                    opts["subtitleslangs"] = [self.cfg["subtitle_lang"]]

            if self.ck_dsub.get():
                opts["writesubtitles"] = True
                opts["writeautomaticsub"] = True
                opts["subtitleslangs"] = [self.cfg["subtitle_lang"]]
            if self.ck_sthumb.get():
                opts["writethumbnail"] = True
            if self.ck_sb.get():
                opts.setdefault("postprocessors", []).extend([
                    {"key": "SponsorBlock"},
                    {"key": "ModifyChapters", "remove_sponsor_segments": ["sponsor"]},
                ])

            self.log(f"[INFO] Format: {opts.get('format')}")
            if opts.get("external_downloader"):
                self.log("[INFO] ⚡ Using aria2c for fast download!")

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if self.cancel_flag:
                self.after(0, self._dl_cancelled)
            else:
                self.after(0, lambda: self._dl_ok(info))

        except Exception as e:
            if "cancelled" in str(e).lower():
                self.after(0, self._dl_cancelled)
            else:
                self.log(f"[ERROR] {e}")
                self.log(traceback.format_exc())
                self.after(0, lambda: self._dl_err(str(e)))

    def _progress_hook(self, d):
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
            self.after(0, lambda: self.prog_stat.configure(text="⬇️ Downloading…"))

        elif st == "finished":
            self.after(0, lambda: self.prog_bar.set(1))
            self.after(0, lambda: self.prog_pct.configure(text="100 %"))
            self.after(0, lambda: self.prog_stat.configure(text="🔧 Post-processing…"))

    def _dl_ok(self, info):
        self.is_downloading = False
        self.prog_bar.set(1)
        self.prog_pct.configure(text="100 %")
        self.prog_speed.configure(text="Done ✅")
        self.prog_eta.configure(text="")
        self.prog_stat.configure(text="✅ Download complete!")
        self.dl_btn.configure(state="normal", text="⬇️  Download Now")
        self.status_lbl.configure(text="✅ Complete")
        if info:
            self._add_hist(info)
        self.log("[INFO] ✅ Complete!")
        messagebox.showinfo("Done", "Download completed! 🎉")

    def _dl_err(self, msg):
        self.is_downloading = False
        self.prog_stat.configure(text=f"❌ {msg[:100]}")
        self.dl_btn.configure(state="normal", text="⬇️  Download Now")
        self.status_lbl.configure(text="❌ Error")
        hint = ""
        if "ffmpeg" in msg.lower():
            hint = "\n\n💡 Install FFmpeg"
        elif "Sign in" in msg:
            hint = "\n\n💡 Enable cookies in Settings"
        messagebox.showerror("Error", f"{msg[:400]}{hint}")

    def _dl_cancelled(self):
        self.is_downloading = False
        self.prog_stat.configure(text="⛔ Cancelled")
        self.dl_btn.configure(state="normal", text="⬇️  Download Now")
        self.status_lbl.configure(text="⛔ Cancelled")

    # ══════════════════════════════════════
    #  PLAYLIST
    # ══════════════════════════════════════

    def _fetch_playlist(self):
        url = self.pl_url.get().strip()
        if not url:
            return
        self.pl_fetch_btn.configure(state="disabled", text="⏳…")
        self.pl_stat.configure(text="⏳ Fetching…")
        threading.Thread(target=self._t_pl_fetch, args=(url,), daemon=True).start()

    def _t_pl_fetch(self, url):
        try:
            opts = self._get_base_opts()
            opts["extract_flat"] = "in_playlist"
            opts["skip_download"] = True

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            entries = list(info.get("entries", []))
            self.pl_entries = entries
            self.after(0, lambda: self._show_pl(info, entries))
        except Exception as e:
            self.after(0, lambda: self.pl_fetch_btn.configure(state="normal", text="🔍 Fetch"))
            self.after(0, lambda: self.pl_stat.configure(text=f"❌ {str(e)[:80]}"))
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _show_pl(self, info, entries):
        self.pl_fetch_btn.configure(state="normal", text="🔍 Fetch")
        self.pl_info_lbl.configure(text=f"📋 {info.get('title', 'Playlist')} • {len(entries)} videos")

        for w in self.pl_scroll.winfo_children():
            w.destroy()
        self.pl_cbs.clear()

        for i, e in enumerate(entries):
            if not e: continue
            var = ctk.BooleanVar(value=True)
            self.pl_cbs.append(var)
            f = ctk.CTkFrame(self.pl_scroll, fg_color="transparent")
            f.grid(row=i, column=0, sticky="ew", padx=5, pady=1)
            f.grid_columnconfigure(1, weight=1)
            ctk.CTkCheckBox(f, text="", variable=var, width=28).grid(row=0, column=0, padx=5)
            ctk.CTkLabel(f, text=f"{i + 1}. {(e.get('title') or '?')[:65]}",
                         font=ctk.CTkFont(size=12), anchor="w").grid(
                row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(f, text=fmt_dur(e.get("duration")),
                         font=ctk.CTkFont(size=11), text_color=("gray50", "gray60"),
                         width=65).grid(row=0, column=2, padx=5)

        self.pl_stat.configure(text=f"✅ {len(entries)} videos loaded")

    def _pl_sel_all(self):
        for v in self.pl_cbs: v.set(True)

    def _pl_desel_all(self):
        for v in self.pl_cbs: v.set(False)

    def _start_playlist(self):
        url = self.pl_url.get().strip()
        if not url: return
        self.pl_stat.configure(text="⏳ Downloading…")
        threading.Thread(target=self._t_pl_dl, args=(url,), daemon=True).start()

    def _t_pl_dl(self, url):
        try:
            out = self.out_e.get().strip() if hasattr(self, "out_e") else self.cfg["download_path"]
            os.makedirs(out, exist_ok=True)
            q = QUALITY_MAP.get(self.pl_q.get(), "bestvideo+bestaudio/best")
            fmt = self.pl_f.get()
            sel = [i + 1 for i, v in enumerate(self.pl_cbs) if v.get()]

            if self.pl_cbs and not sel:
                self.after(0, lambda: messagebox.showwarning("Playlist", "No videos selected!"))
                return

            def hook(d):
                if d.get("status") == "downloading":
                    t = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                    dn = d.get("downloaded_bytes", 0)
                    if t:
                        self.after(0, lambda f=dn / t: self.pl_prog.set(min(f, 1.0)))

            opts = self._get_base_opts()
            opts["outtmpl"] = os.path.join(out, "%(playlist_title)s", "%(title)s.%(ext)s")
            opts["progress_hooks"] = [hook]

            if fmt in AUDIO_FORMATS:
                opts["format"] = "bestaudio/best"
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": fmt,
                    "preferredquality": "192",
                }]
            else:
                opts["format"] = q
                opts["merge_output_format"] = fmt

            if sel:
                opts["playlist_items"] = ",".join(map(str, sel))

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            self.after(0, lambda: self.pl_prog.set(1))
            self.after(0, lambda: self.pl_stat.configure(text="✅ Complete!"))
            self.after(0, lambda: messagebox.showinfo("Done", "Playlist finished! 🎉"))
        except Exception as e:
            self.after(0, lambda: self.pl_stat.configure(text=f"❌ {str(e)[:80]}"))
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    # ══════════════════════════════════════
    #  BATCH
    # ══════════════════════════════════════

    def _start_batch(self):
        txt = self.batch_txt.get("1.0", "end").strip()
        urls = [u.strip() for u in txt.splitlines() if u.strip() and not u.startswith("#")]
        if not urls:
            messagebox.showwarning("Input", "Add URLs!")
            return
        threading.Thread(target=self._t_batch, args=(urls,), daemon=True).start()

    def _t_batch(self, urls):
        total, ok, fail = len(urls), 0, 0
        out = self.out_e.get().strip() if hasattr(self, "out_e") else self.cfg["download_path"]
        os.makedirs(out, exist_ok=True)
        q = QUALITY_MAP.get(self.ba_q.get(), "bestvideo+bestaudio/best")
        fmt = self.ba_f.get()

        for idx, url in enumerate(urls):
            self.after(0, lambda i=idx: self.ba_stat.configure(
                text=f"⏳ {i + 1}/{total}…"))
            self.after(0, lambda i=idx: self.ba_prog.set(i / total))
            try:
                opts = self._get_base_opts(single=True)
                opts["outtmpl"] = os.path.join(out, "%(title)s.%(ext)s")
                if fmt in AUDIO_FORMATS:
                    opts["format"] = "bestaudio/best"
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": fmt, "preferredquality": "192"}]
                else:
                    opts["format"] = q
                    opts["merge_output_format"] = fmt

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    t = info.get("title", url) if info else url
                self.after(0, lambda t=t: self.ba_log.insert("end", f"✅ {t}\n"))
                self.after(0, lambda: self.ba_log.see("end"))
                if info: self.after(0, lambda i=info: self._add_hist(i))
                ok += 1
            except Exception as e:
                fail += 1
                self.after(0, lambda u=url, e=str(e): self.ba_log.insert(
                    "end", f"❌ {u}: {e[:80]}\n"))
                self.after(0, lambda: self.ba_log.see("end"))

        self.after(0, lambda: self.ba_prog.set(1))
        self.after(0, lambda: self.ba_stat.configure(text=f"✅ {ok} ok, {fail} failed / {total}"))
        self.after(0, lambda: messagebox.showinfo("Batch", f"✅ {ok} done\n❌ {fail} failed"))

    # ══════════════════════════════════════
    #  QUEUE
    # ══════════════════════════════════════

    def _enqueue_single(self):
        url = self.url_e.get().strip()
        if not url: return
        self.dl_counter += 1
        item = {
            "id": self.dl_counter, "url": url,
            "title": self.current_info.get("title", f"Video #{self.dl_counter}"),
            "qual": self.qual_var.get(),
            "fmt": self.afmt.get() if self.dl_type.get() == "Audio Only" else self.vfmt.get(),
            "type": self.dl_type.get(),
        }
        self.download_queue.append(item)
        self._add_q_widget(item)
        self.q_cnt.configure(text=f"{len(self.download_queue)} items")

    def _add_q_widget(self, item):
        f = ctk.CTkFrame(self.q_scroll)
        f.grid(row=len(self.queue_widgets), column=0, sticky="ew", padx=5, pady=3)
        f.grid_columnconfigure(1, weight=1)
        sl = ctk.CTkLabel(f, text="⏳", width=30, font=ctk.CTkFont(size=16))
        sl.grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkLabel(f, text=item["title"][:50], font=ctk.CTkFont(size=13),
                     anchor="w").grid(row=0, column=1, padx=5, pady=10, sticky="w")
        ctk.CTkLabel(f, text=f'{item["qual"]} • {item["fmt"]}',
                     font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).grid(
            row=0, column=2, padx=10)
        ctk.CTkButton(f, text="✕", width=34, height=34, fg_color=("gray60", "gray30"),
                       command=lambda: self._rm_q(f, item)).grid(row=0, column=3, padx=10)
        self.queue_widgets.append((f, sl, item))

    def _rm_q(self, frame, item):
        if item in self.download_queue: self.download_queue.remove(item)
        frame.destroy()
        self.q_cnt.configure(text=f"{len(self.download_queue)} items")

    def _clear_queue(self):
        self.download_queue.clear()
        for w in self.q_scroll.winfo_children(): w.destroy()
        self.queue_widgets.clear()
        self.q_cnt.configure(text="0 items")

    def _run_queue(self):
        if not self.download_queue:
            messagebox.showinfo("Queue", "Empty!")
            return
        threading.Thread(target=self._t_queue, daemon=True).start()

    def _t_queue(self):
        while self.download_queue:
            item = self.download_queue[0]
            for f, sl, it in self.queue_widgets:
                if it["id"] == item["id"]:
                    self.after(0, lambda s=sl: s.configure(text="⬇️")); break

            try:
                out = self.cfg["download_path"]
                os.makedirs(out, exist_ok=True)
                opts = self._get_base_opts(single=True)
                opts["outtmpl"] = os.path.join(out, "%(title)s.%(ext)s")
                q = QUALITY_MAP.get(item["qual"], "bestvideo+bestaudio/best")
                fmt = item["fmt"]
                if item["type"] == "Audio Only" or fmt in AUDIO_FORMATS:
                    opts["format"] = "bestaudio/best"
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": fmt if fmt in AUDIO_FORMATS else "mp3",
                        "preferredquality": "192"}]
                else:
                    opts["format"] = q
                    opts["merge_output_format"] = fmt

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(item["url"], download=True)
                    if info: self.after(0, lambda i=info: self._add_hist(i))

                for f, sl, it in self.queue_widgets:
                    if it["id"] == item["id"]:
                        self.after(0, lambda s=sl: s.configure(text="✅")); break
            except Exception:
                for f, sl, it in self.queue_widgets:
                    if it["id"] == item["id"]:
                        self.after(0, lambda s=sl: s.configure(text="❌")); break

            self.download_queue.pop(0)
            self.after(0, lambda: self.q_cnt.configure(
                text=f"{len(self.download_queue)} items"))

        self.after(0, lambda: messagebox.showinfo("Queue", "All done! 🎉"))

    # ══════════════════════════════════════
    #  SEARCH  (YouTube-style with thumbnails)
    # ══════════════════════════════════════

    def _do_search(self):
        query = self.srch_e.get().strip()
        if not query: return
        try:
            mx = int(self.srch_max.get())
        except ValueError:
            mx = 15

        self.srch_btn.configure(state="disabled", text="⏳…")
        self.srch_stat.configure(text=f"🔍 Searching: {query}…")
        for w in self.srch_scroll.winfo_children(): w.destroy()
        threading.Thread(target=self._t_search, args=(query, mx), daemon=True).start()

    def _t_search(self, query, mx):
        try:
            opts = self._get_base_opts()
            opts["extract_flat"] = True
            opts["skip_download"] = True

            with yt_dlp.YoutubeDL(opts) as ydl:
                res = ydl.extract_info(f"ytsearch{mx}:{query}", download=False)

            entries = [e for e in res.get("entries", []) if e]
            self.after(0, lambda: self._render_search(entries))
        except Exception as e:
            self.after(0, lambda: self.srch_btn.configure(state="normal", text="🔍 Search"))
            self.after(0, lambda: self.srch_stat.configure(text=f"❌ {str(e)[:80]}"))

    def _render_search(self, entries):
        self.srch_btn.configure(state="normal", text="🔍 Search")
        self.srch_stat.configure(text=f"✅ {len(entries)} results found")

        for w in self.srch_scroll.winfo_children():
            w.destroy()

        for i, e in enumerate(entries):
            card = ctk.CTkFrame(self.srch_scroll, corner_radius=12,
                                fg_color=("gray88", "gray17"),
                                border_width=1,
                                border_color=("gray78", "gray25"))
            card.grid(row=i, column=0, sticky="ew", padx=8, pady=6)
            card.grid_columnconfigure(1, weight=1)

            # ── Thumbnail placeholder ──
            thumb_frame = ctk.CTkFrame(card, width=168, height=94,
                                        fg_color=("gray75", "gray25"),
                                        corner_radius=8)
            thumb_frame.grid(row=0, column=0, padx=12, pady=12, rowspan=3, sticky="nw")
            thumb_frame.grid_propagate(False)

            thumb_inner = ctk.CTkLabel(thumb_frame, text="⏳",
                                        font=ctk.CTkFont(size=20))
            thumb_inner.place(relx=0.5, rely=0.5, anchor="center")

            # Duration badge
            dur = e.get("duration")
            dur_text = fmt_dur(dur) if dur else ""

            # Load thumbnail async
            thumb_url = e.get("thumbnail") or ""
            if not thumb_url:
                vid_id = e.get("id", "")
                if vid_id:
                    thumb_url = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"

            if thumb_url:
                def set_thumb(img, lbl=thumb_inner, dt=dur_text, frame=thumb_frame):
                    def _apply():
                        lbl.configure(image=img, text="")
                        lbl.place(relx=0.5, rely=0.5, anchor="center")
                        if dt:
                            badge = ctk.CTkLabel(
                                frame, text=f" {dt} ",
                                font=ctk.CTkFont(size=10, weight="bold"),
                                fg_color=("gray20", "gray10"),
                                text_color="white",
                                corner_radius=4, height=20)
                            badge.place(relx=0.95, rely=0.92, anchor="se")
                    self.after(0, _apply)

                load_thumbnail(thumb_url, (168, 94), set_thumb)
            elif dur_text:
                badge = ctk.CTkLabel(thumb_frame, text=f" {dur_text} ",
                                      font=ctk.CTkFont(size=10, weight="bold"),
                                      fg_color="gray20", text_color="white",
                                      corner_radius=4, height=20)
                badge.place(relx=0.95, rely=0.92, anchor="se")

            # ── Title ──
            title = e.get("title") or e.get("id", "Unknown")
            ctk.CTkLabel(card, text=title[:80],
                         font=ctk.CTkFont(size=14, weight="bold"),
                         anchor="w", wraplength=500, justify="left").grid(
                row=0, column=1, padx=(5, 10), pady=(14, 0), sticky="nw")

            # ── Channel + views ──
            ch = e.get("channel") or e.get("uploader") or ""
            views = fmt_views(e.get("view_count"))
            meta_parts = [x for x in [ch, views] if x]
            meta_text = "  •  ".join(meta_parts)

            meta_frame = ctk.CTkFrame(card, fg_color="transparent")
            meta_frame.grid(row=1, column=1, padx=(5, 10), pady=(2, 0), sticky="nw")

            # Channel icon placeholder
            ctk.CTkLabel(meta_frame, text="👤",
                         font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(meta_frame, text=meta_text,
                         font=ctk.CTkFont(size=12),
                         text_color=("gray45", "gray55"),
                         anchor="w").pack(side="left")

            # ── Description snippet (if available) ──
            desc = e.get("description") or ""
            if desc:
                desc_short = desc[:120].replace("\n", " ")
                if len(desc) > 120:
                    desc_short += "…"
                ctk.CTkLabel(card, text=desc_short,
                             font=ctk.CTkFont(size=11),
                             text_color=("gray50", "gray55"),
                             anchor="w", wraplength=500, justify="left").grid(
                    row=2, column=1, padx=(5, 10), pady=(2, 0), sticky="nw")

            # ── Buttons ──
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=3, column=1, padx=(5, 10), pady=(6, 12), sticky="sw")

            vid_url = e.get("url") or e.get("webpage_url") or e.get("id", "")

            ctk.CTkButton(btn_frame, text="⬇️ Download", width=120, height=36,
                           fg_color="#e74c3c", hover_color="#c0392b",
                           font=ctk.CTkFont(size=12, weight="bold"),
                           corner_radius=8,
                           command=lambda u=vid_url: self._search_dl(u)).pack(
                side="left", padx=(0, 8))

            ctk.CTkButton(btn_frame, text="➕ Queue", width=90, height=36,
                           fg_color=("gray60", "gray30"),
                           hover_color=("gray50", "gray40"),
                           corner_radius=8,
                           command=lambda u=vid_url, t=title: self._search_queue(u, t)).pack(
                side="left", padx=(0, 8))

            ctk.CTkButton(btn_frame, text="📋 Copy URL", width=100, height=36,
                           fg_color=("gray60", "gray30"),
                           hover_color=("gray50", "gray40"),
                           corner_radius=8,
                           command=lambda u=vid_url: self._copy_url(u)).pack(
                side="left")

    def _copy_url(self, url):
        full = url if url.startswith("http") else f"https://www.youtube.com/watch?v={url}"
        self.clipboard_clear()
        self.clipboard_append(full)

    def _search_dl(self, url):
        full = url if url.startswith("http") else f"https://www.youtube.com/watch?v={url}"
        self.url_e.delete(0, "end")
        self.url_e.insert(0, full)
        self._show("single")
        self._fetch_info()

    def _search_queue(self, url, title):
        full = url if url.startswith("http") else f"https://www.youtube.com/watch?v={url}"
        self.dl_counter += 1
        item = {"id": self.dl_counter, "url": full, "title": title,
                "qual": "Best Quality", "fmt": "mp4", "type": "Video"}
        self.download_queue.append(item)
        self._add_q_widget(item)
        self.q_cnt.configure(text=f"{len(self.download_queue)} items")

    # ══════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════

    def _refresh_hist(self):
        if not hasattr(self, "hist_scroll"): return
        for w in self.hist_scroll.winfo_children(): w.destroy()
        for i, e in enumerate(reversed(self.history[-200:])):
            f = ctk.CTkFrame(self.hist_scroll)
            f.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            f.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(f, text="✅", width=28).grid(row=0, column=0, padx=8, pady=8)
            ctk.CTkLabel(f, text=e.get("title", "?")[:50],
                         font=ctk.CTkFont(size=12), anchor="w").grid(
                row=0, column=1, padx=5, pady=8, sticky="w")
            try:
                dt = datetime.fromisoformat(e["timestamp"]).strftime("%m/%d %H:%M")
            except Exception:
                dt = "?"
            ctk.CTkLabel(f, text=dt, font=ctk.CTkFont(size=11),
                         text_color=("gray50", "gray60")).grid(row=0, column=2, padx=8)
            ctk.CTkLabel(f, text=f'{e.get("format", "?")} • {fmt_size(e.get("size"))}',
                         font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).grid(
                row=0, column=3, padx=8)
            url = e.get("url", "")
            if url:
                ctk.CTkButton(f, text="🔄", width=34, height=28,
                               fg_color=("gray55", "gray30"),
                               command=lambda u=url: (
                                   self.url_e.delete(0, "end"),
                                   self.url_e.insert(0, u),
                                   self._show("single")
                               )).grid(row=0, column=4, padx=(0, 8))

        if hasattr(self, "hist_cnt"):
            self.hist_cnt.configure(text=f"{len(self.history)} items")

    def _filter_hist(self):
        q = self.hist_search.get().lower()
        for w in self.hist_scroll.winfo_children(): w.destroy()
        filtered = [e for e in self.history if q in e.get("title", "").lower()]
        for i, e in enumerate(reversed(filtered[-200:])):
            f = ctk.CTkFrame(self.hist_scroll)
            f.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            f.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(f, text="✅", width=28).grid(row=0, column=0, padx=8, pady=8)
            ctk.CTkLabel(f, text=e.get("title", "?")[:50],
                         font=ctk.CTkFont(size=12), anchor="w").grid(
                row=0, column=1, padx=5, pady=8, sticky="w")

    def _clear_hist(self):
        if messagebox.askyesno("History", "Clear all?"):
            self.history.clear()
            self._save_hist()
            self._refresh_hist()

    def _export_hist(self):
        f = filedialog.asksaveasfilename(defaultextension=".json",
                                          filetypes=[("JSON", "*.json"), ("CSV", "*.csv")])
        if not f: return
        if f.endswith(".csv"):
            import csv
            with open(f, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=["title", "url", "timestamp", "format", "size"])
                w.writeheader()
                w.writerows(self.history)
        else:
            self._save_json(f, self.history)
        messagebox.showinfo("Export", f"Saved to {f}")

    # ══════════════════════════════════════
    #  SAVE SETTINGS
    # ══════════════════════════════════════

    def _save_settings(self):
        self.cfg["download_path"] = self.s_path.get().strip()
        self.cfg["filename_template"] = self.s_tpl.get().strip() or "%(title)s.%(ext)s"
        self.cfg["default_video_format"] = self.s_vfmt.get()
        self.cfg["default_audio_format"] = self.s_afmt.get()
        self.cfg["default_video_quality"] = self.s_qual.get()
        self.cfg["concurrent_fragments"] = int(self.s_frag.get())
        self.cfg["use_aria2c"] = self.s_aria2c.get()
        try:
            self.cfg["buffer_size"] = int(self.s_buf.get())
        except ValueError:
            self.cfg["buffer_size"] = 1024
        try:
            self.cfg["speed_limit"] = int(self.s_speed.get())
        except ValueError:
            self.cfg["speed_limit"] = 0
        self.cfg["proxy"] = self.s_proxy.get().strip()
        self.cfg["geo_bypass"] = self.s_geo.get()
        self.cfg["use_cookies"] = self.s_use_cookies.get()
        self.cfg["cookies_browser"] = self.s_cookies_browser.get()
        self.cfg["embed_thumbnail"] = self.s_ethumb.get()
        self.cfg["embed_subtitles"] = self.s_esub.get()
        self.cfg["sponsor_block"] = self.s_sb.get()
        self.cfg["clipboard_monitor"] = self.s_clip.get()
        self.cfg["subtitle_lang"] = self.s_slang.get().strip() or "en"

        self._save_cfg()
        os.makedirs(self.cfg["download_path"], exist_ok=True)
        self.out_e.delete(0, "end")
        self.out_e.insert(0, self.cfg["download_path"])
        self.vfmt.set(self.cfg["default_video_format"])
        self.afmt.set(self.cfg["default_audio_format"])

        if self.cfg["clipboard_monitor"]:
            self._poll_clipboard()

        self.log("[INFO] ✅ Settings saved")
        messagebox.showinfo("Settings", "Saved ✔")

    # ══════════════════════════════════════
    #  CLIPBOARD
    # ══════════════════════════════════════

    def _poll_clipboard(self):
        if not self.cfg.get("clipboard_monitor"): return
        try:
            cur = self.clipboard_get().strip()
            if cur and cur != self.last_clip:
                self.last_clip = cur
                if any(p in cur for p in [
                    "youtube.com/watch", "youtu.be/",
                    "youtube.com/shorts", "youtube.com/playlist"
                ]):
                    self.url_e.delete(0, "end")
                    self.url_e.insert(0, cur)
                    self.status_lbl.configure(text="📋 URL detected!")
        except Exception:
            pass
        self.after(1500, self._poll_clipboard)


if __name__ == "__main__":
    app = App()
    app.mainloop()