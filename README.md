# YouTube Downloader GUI

A modern Windows GUI application for downloading YouTube videos, similar to ytdlnis. Built with Python, CustomTkinter, and yt-dlp.

## Features

✨ **Modern Dark UI** - Clean, modern interface with CustomTkinter
📹 **Multiple Quality Presets** - Best Quality, 1080p, 720p, 480p, Audio Only
🎵 **Audio Extraction** - Download as MP3 or M4A
📋 **Playlist Support** - Download entire playlists or single videos
📊 **Real-time Progress** - Live progress bar with speed and ETA
📝 **Download Log** - Track all downloads with detailed logging
🎯 **Subtitle Support** - Download and embed subtitles
🖼️ **Thumbnail Embedding** - Embed video thumbnails
📁 **Custom Save Location** - Choose where to save downloads

## Installation

### Prerequisites

1. **Python 3.8 or higher** - Download from [python.org](https://www.python.org/downloads/)
2. **FFmpeg** - Required for audio conversion and thumbnail embedding

#### Installing FFmpeg on Windows:

**Option 1: Using Chocolatey (Recommended)**
```bash
choco install ffmpeg
```

**Option 2: Manual Installation**
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract the archive
3. Add the `bin` folder to your system PATH

### Setup

1. **Clone or download this repository**

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

Alternatively, install manually:
```bash
pip install customtkinter yt-dlp pillow
```

3. **Run the application:**
```bash
python ytdl_gui.py
```

## Usage

1. **Enter URL**: Paste a YouTube video or playlist URL
2. **Select Quality**: Choose from the preset dropdown menu
3. **Configure Options**:
   - ✓ Download entire playlist
   - ✓ Download subtitles
   - ✓ Embed thumbnail
4. **Choose Save Location**: Click "Browse" to select download folder
5. **Click Download**: Watch the progress in real-time

## Quality Presets

- **Best Quality**: Highest available video + audio quality
- **1080p**: Full HD video
- **720p**: HD video
- **480p**: SD video
- **Audio Only (MP3)**: Extract audio as MP3 (192kbps)
- **Audio Only (M4A)**: Extract audio in M4A format

## Creating an Executable (Optional)

To create a standalone `.exe` file that doesn't require Python:

1. **Install PyInstaller:**
```bash
pip install pyinstaller
```

2. **Create the executable:**
```bash
pyinstaller --onefile --windowed --name "YouTube Downloader" ytdl_gui.py
```

3. **Find your executable** in the `dist` folder

**Note**: The executable will still require FFmpeg to be installed on the system for full functionality.

## Troubleshooting

### "No module named 'customtkinter'"
- Run: `pip install customtkinter`

### "FFmpeg not found" or audio conversion fails
- Install FFmpeg and ensure it's in your system PATH
- Restart your terminal/command prompt after installation

### Downloads are slow
- This depends on your internet connection and YouTube's servers
- Try a different time or check your network speed

### "Unable to extract video data"
- The URL might be invalid or the video might be private/removed
- Update yt-dlp: `pip install --upgrade yt-dlp`

## Advanced Customization

### Adding Custom Presets

Edit the `_load_presets()` method in `ytdl_gui.py`:

```python
def _load_presets(self):
    return {
        "Best Quality": DownloadPreset("Best Quality", "bestvideo+bestaudio/best"),
        "4K": DownloadPreset("4K", "bestvideo[height<=2160]+bestaudio/best[height<=2160]"),
        # Add your custom preset here
    }
```

### Changing Theme

In `__init__()`, modify:
```python
ctk.set_appearance_mode("dark")  # "light", "dark", or "system"
ctk.set_default_color_theme("blue")  # "blue", "green", or "dark-blue"
```

## Supported Sites

This app supports all sites that yt-dlp supports, including:
- YouTube
- Vimeo
- Dailymotion
- Twitter/X
- Reddit
- And 1000+ more sites

See the full list: [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## License

This project is provided as-is for educational purposes. Please respect copyright laws and terms of service of the platforms you download from.

## Credits

- **yt-dlp**: The powerful download engine
- **CustomTkinter**: Modern UI framework
- Built with ❤️ for the community

## Disclaimer

This tool is for personal use only. Downloading copyrighted content without permission may violate YouTube's Terms of Service and copyright laws. Use responsibly.
