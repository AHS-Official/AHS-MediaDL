# AHS-MediaDL
**A professional open-source desktop application for downloading high-quality videos and audio.**

## 📖 About the Project
**AHS-MediaDL** is a smart and fast tool designed to make downloading media (video and audio) from the internet easy. The application features a modern, user-friendly interface and relies on powerful background engines to ensure the highest possible quality (up to 4K for video and 320 kbps for audio) with automatic metadata embedding. 

Recently rebuilt with a modular architecture to support advanced batch processing and playlist handling, making it lighter and faster than ever.

## ✨ Key Features
* 🎬 **Comprehensive Quality Support:** Download videos in all available resolutions (from data-efficient 144p to 4K Ultra HD).
* 🎵 **Professional Audio Extraction:** Convert videos to high-definition audio files in multiple formats (MP3, M4A) with quality options suitable for mobile devices, cars, and speakers.
* 📑 **Advanced Playlist Support (NEW):** Automatically detect playlists, fetch thumbnails for each item, and allow users to select specific videos. Includes auto-folder creation and sequential numbering for saved files.
* 📥 **Multiple Downloads Queue:** A dedicated download management tab allows you to add multiple links simultaneously with full control (pause, resume, cancel, and auto-clean).
* 🖼️ **Metadata & Cover Art Embedding:** Automatically add thumbnails and original video titles to MP3 and MP4 files, with an intelligent fallback for WebP covers.
* ⚡ **Live Download Tracking:** A smart progress bar displays download speed, downloaded file size versus total size, and estimated time of arrival.
* 🧠 **Smart Memory Management (NEW):** Utilizes dynamic QThread cleanup and object destruction to ensure zero RAM bloat during heavy multi-file downloads.
* 🖥️ **Modern and Responsive GUI:** A sleek, user-friendly, and ad-free interface that seamlessly adapts to system font settings and screen zoom.

## 🛠️ Technologies Used
* **Programming Language:** Python
* **GUI Framework:** PyQt6 (with QStackedWidget for seamless view routing)
* **Primary Download Engine:** yt-dlp
* **Media Processing (Merge/Extract):** FFmpeg
