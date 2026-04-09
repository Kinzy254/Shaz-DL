# Panel-dl v4

Panel-dl v4 is a desktop YouTube downloader built with Python, `CustomTkinter`, and `yt-dlp`. It provides a lightweight GUI for searching YouTube, downloading audio or video, and tracking download history.

## Features

- Search YouTube from the app using built-in `yt-dlp` search
- Download audio as MP3 with embedded metadata
- Download video with merged best quality audio and video
- Queue downloads and show live progress updates
- Persist download history to a local JSON file
- Thumbnail caching for search result cards
- Audio streaming support using `yt-dlp`, `ffmpeg`, and `PyAudio`
- Simple, modern UI with separate Home and Downloads tabs

## Requirements

- Python 3.10 or newer
- `ffmpeg` installed and available in `PATH`
- `yt-dlp` installed

Python package dependencies:

- `customtkinter`
- `yt_dlp`
- `pillow`
- `pyaudio`
- `requests`

> Note: `requirements.txt` is currently empty in this repository. Install the dependencies manually or add them to `requirements.txt`.

## Installation

1. Clone or download the repository.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Upgrade pip and install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install customtkinter yt_dlp pillow pyaudio requests
```

4. Install `ffmpeg` separately if it is not already installed.

## Usage

Run the main application file:

```powershell
python "Panel-dl v4.py"
```

Then:

1. Enter a YouTube URL or search keyword in the input box.
2. Use the Search button to retrieve results.
3. Click `Audio` or `Video` on a result card to enqueue a download.
4. Switch to the `Downloads` tab to monitor running, queued, finished, cancelled, and error states.

## Default storage paths

- Download folder: `%USERPROFILE%\Downloads\QByiT`
- App data folder: `%USERPROFILE%\.qbyit`
- History file: `%USERPROFILE%\.qbyit\qbyit_history.json`

## Project files

- `Panel-dl v4.py` — main application script
- `README.md` — project documentation
- `requirements.txt` — dependency list placeholder

## Notes

- The GUI is currently configured as a frameless window with a custom close button.
- Audio streaming uses a background `yt-dlp` and `ffmpeg` pipeline with `PyAudio` playback.
- If downloads fail, check that `yt-dlp`, `ffmpeg`, and the required Python packages are installed correctly.
