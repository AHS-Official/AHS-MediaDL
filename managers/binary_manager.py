"""
Binary and Dependency Manager for AHS-MediaDL.

Manages discovery, versioning, downloading, extraction, and updates for:
- ffmpeg.exe
- ffprobe.exe
- yt-dlp.exe

Compatible with Python development mode, PyInstaller, and Nuitka standalone.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import json
import zipfile
import time
from typing import Optional, Dict, List, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

from utils.helpers import get_app_root_dir, get_data_dir
from utils.logger import logger

# Official Download Endpoints
YT_DLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
YT_DLP_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

FFMPEG_ESSENTIALS_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_VERSION_URL = "https://www.gyan.dev/ffmpeg/builds/release-version"


class BinaryManager:
    """Manages locating, validating, and updating external binaries."""

    @staticmethod
    def get_preferred_bin_dir() -> str:
        """
        Determines the optimal directory to store downloaded binaries:
        1. Checks <app_root_dir>/bin: If writable, uses it (ideal for portable/standalone apps).
        2. Fallback to <user_data_dir>/bin: Guaranteed writable without admin privileges.
        """
        app_root = get_app_root_dir()
        local_bin = os.path.join(app_root, "bin")

        # Test if local_bin is writable
        try:
            os.makedirs(local_bin, exist_ok=True)
            test_file = os.path.join(local_bin, ".write_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return local_bin
        except Exception:
            pass

        # Fallback to AppData / User Data dir
        appdata_bin = os.path.join(get_data_dir(), "bin")
        os.makedirs(appdata_bin, exist_ok=True)
        return appdata_bin

    @classmethod
    def get_binary_path(cls, binary_name: str) -> Optional[str]:
        """
        Searches for a binary in order of priority:
        1. <app_root>/bin/
        2. <app_root>/
        3. <user_data_dir>/bin/
        4. System PATH via shutil.which()
        """
        app_root = get_app_root_dir()
        appdata_dir = get_data_dir()
        exts = [".exe", ""] if os.name == "nt" else [""]

        search_dirs = [
            os.path.join(app_root, "bin"),
            app_root,
            os.path.join(appdata_dir, "bin"),
            appdata_dir,
        ]

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for ext in exts:
                candidate = os.path.join(s_dir, f"{binary_name}{ext}")
                if os.path.isfile(candidate) and (os.name != "nt" or os.access(candidate, os.X_OK)):
                    return os.path.abspath(candidate)

        # Fallback to System PATH
        system_bin = shutil.which(binary_name)
        if system_bin:
            return os.path.abspath(system_bin)

        # On Windows, query Registry PATH dynamically if not updated in current process env
        if os.name == "nt":
            try:
                import winreg
                reg_paths = []
                try:
                    u_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                    u_path, _ = winreg.QueryValueEx(u_key, "Path")
                    reg_paths.append(u_path)
                except Exception:
                    pass
                try:
                    m_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
                    m_path, _ = winreg.QueryValueEx(m_key, "Path")
                    reg_paths.append(m_path)
                except Exception:
                    pass
                comb = os.pathsep.join(filter(None, [os.environ.get("PATH", "")] + reg_paths))
                reg_bin = shutil.which(binary_name, path=comb)
                if reg_bin:
                    os.environ["PATH"] = comb
                    return os.path.abspath(reg_bin)
            except Exception:
                pass

        return None

    @classmethod
    def is_ffmpeg_available(cls) -> bool:
        """Returns True if both ffmpeg and ffprobe are available."""
        return bool(cls.get_binary_path("ffmpeg") and cls.get_binary_path("ffprobe"))

    @classmethod
    def is_yt_dlp_available(cls) -> bool:
        """Returns True if yt-dlp binary is available in bin or PATH."""
        return bool(cls.get_binary_path("yt-dlp"))

    @classmethod
    def are_all_tools_available(cls) -> bool:
        """Returns True if all required external binaries (ffmpeg, ffprobe, yt-dlp) are present."""
        return cls.is_ffmpeg_available() and cls.is_yt_dlp_available()

    @classmethod
    def get_missing_tools(cls) -> List[str]:
        """Returns a list of missing tool names."""
        missing = []
        if not cls.get_binary_path("ffmpeg"):
            missing.append("ffmpeg")
        if not cls.get_binary_path("ffprobe"):
            missing.append("ffprobe")
        if not cls.get_binary_path("yt-dlp"):
            missing.append("yt-dlp")
        return missing

    @classmethod
    def get_local_version(cls, binary_name: str) -> str:
        """Runs the binary with --version and returns the first line/version token."""
        bin_path = cls.get_binary_path(binary_name)
        if not bin_path or not os.path.exists(bin_path):
            return "Not Installed"
        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            res = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=4, **kwargs)
            out = res.stdout.strip() or res.stderr.strip()
            if out:
                first_line = out.splitlines()[0]
                if binary_name.lower() in ["ffmpeg", "ffprobe"] and "version" in first_line:
                    parts = first_line.split("version")
                    if len(parts) > 1:
                        return parts[1].split()[0]
                return first_line.split()[0] if binary_name == "yt-dlp" else first_line[:30]
        except Exception as e:
            logger.debug(f"Error inspecting version for {binary_name}: {e}")
        return "Unknown"

    @classmethod
    def update_yt_dlp_binary(cls) -> Tuple[bool, str]:
        """
        Runs `yt-dlp -U` or downloads the latest binary.
        Returns (success: bool, new_version_or_message: str).
        """
        bin_path = cls.get_binary_path("yt-dlp")
        if bin_path:
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                proc = subprocess.run(
                    [bin_path, "-U"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=creationflags
                )
                new_ver = cls.get_local_version("yt-dlp")
                if proc.returncode == 0:
                    return (True, new_ver)
                # If error message indicates already up to date
                combined_out = (proc.stdout or "") + (proc.stderr or "")
                if "up to date" in combined_out.lower() or "latest version" in combined_out.lower():
                    return (True, new_ver)
            except Exception as e:
                logger.warning(f"Self-update failed for yt-dlp: {e}")

        # Fallback: direct download
        target_dir = cls.get_preferred_bin_dir()
        os.makedirs(target_dir, exist_ok=True)
        dest_file = os.path.join(target_dir, "yt-dlp.exe" if os.name == "nt" else "yt-dlp")
        try:
            url = DOWNLOAD_URLS["yt-dlp"]
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest_file, "wb") as f:
                shutil.copyfileobj(resp, f)
            if os.name != "nt":
                os.chmod(dest_file, 0o755)
            new_ver = cls.get_local_version("yt-dlp")
            return (True, new_ver)
        except Exception as e:
            return (False, str(e))

    @classmethod
    def get_latest_yt_dlp_version(cls) -> Optional[str]:
        """Fetches latest version tag of yt-dlp from GitHub releases."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(YT_DLP_API_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return data.get("tag_name")
        except Exception as e:
            logger.warning(f"Failed to check latest yt-dlp version: {e}")
            return None

    @classmethod
    def get_latest_ffmpeg_version(cls) -> Optional[str]:
        """Fetches latest version string of Gyan.dev FFmpeg release."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(FFMPEG_VERSION_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read().decode().strip()
        except Exception as e:
            logger.warning(f"Failed to check latest ffmpeg version: {e}")
            return None

    @classmethod
    def import_binaries_from_folder(cls, source_folder: str) -> Tuple[bool, List[str]]:
        """
        Copies any of ffmpeg.exe, ffprobe.exe, yt-dlp.exe found in source_folder
        into the preferred local bin directory.
        """
        if not os.path.exists(source_folder):
            return False, []

        target_bin = cls.get_preferred_bin_dir()
        os.makedirs(target_bin, exist_ok=True)
        copied = []

        for name in ["ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe"]:
            # Check source directly or in a bin subfolder
            src_candidates = [
                os.path.join(source_folder, name),
                os.path.join(source_folder, "bin", name),
            ]
            for src in src_candidates:
                if os.path.isfile(src):
                    dest = os.path.join(target_bin, name)
                    try:
                        shutil.copy2(src, dest)
                        copied.append(name)
                        break
                    except Exception as e:
                        logger.error(f"Failed copying {src} to {dest}: {e}")

        return (len(copied) > 0, copied)


class BinaryDownloaderWorker(QThread):
    """
    Background worker that downloads and installs yt-dlp.exe and/or FFmpeg essentials.
    Emits progress and status updates.
    """
    progress_signal = pyqtSignal(int, str)  # percent (0-100), status text
    step_finished_signal = pyqtSignal(str)  # tool name finished
    finished_signal = pyqtSignal(bool, str) # success, message

    def __init__(self, download_yt_dlp=True, download_ffmpeg=True, parent=None):
        super().__init__(parent)
        self.download_yt_dlp = download_yt_dlp
        self.download_ffmpeg = download_ffmpeg
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        target_bin = BinaryManager.get_preferred_bin_dir()
        os.makedirs(target_bin, exist_ok=True)

        try:
            # 1. Download yt-dlp.exe
            if self.download_yt_dlp:
                if self.is_cancelled:
                    self.finished_signal.emit(False, "Cancelled")
                    return
                self.progress_signal.emit(5, "Downloading yt-dlp.exe...")
                dest_file = os.path.join(target_bin, "yt-dlp.exe")
                temp_file = dest_file + ".download"
                self._download_file(YT_DLP_DOWNLOAD_URL, temp_file, weight=30, base_pct=5)
                if os.path.exists(temp_file):
                    if os.path.exists(dest_file):
                        try:
                            os.remove(dest_file)
                        except Exception:
                            pass
                    shutil.move(temp_file, dest_file)
                self.step_finished_signal.emit("yt-dlp")

            # 2. Download FFmpeg Essentials Zip
            if self.download_ffmpeg:
                if self.is_cancelled:
                    self.finished_signal.emit(False, "Cancelled")
                    return
                self.progress_signal.emit(35, "Downloading FFmpeg package...")
                zip_temp = os.path.join(target_bin, "ffmpeg_temp.zip")
                self._download_file(FFMPEG_ESSENTIALS_ZIP_URL, zip_temp, weight=55, base_pct=35)
                
                # 3. Extract ffmpeg.exe and ffprobe.exe
                self.progress_signal.emit(92, "Extracting FFmpeg & FFprobe...")
                self._extract_ffmpeg_zip(zip_temp, target_bin)
                
                # Clean up zip
                try:
                    if os.path.exists(zip_temp):
                        os.remove(zip_temp)
                except Exception:
                    pass
                self.step_finished_signal.emit("ffmpeg")

            self.progress_signal.emit(100, "Setup complete!")
            self.finished_signal.emit(True, "All tools installed successfully!")
        except Exception as e:
            logger.error(f"Binary setup error: {e}")
            self.finished_signal.emit(False, str(e))

    def _download_file(self, url: str, target_path: str, weight: int, base_pct: int):
        """Downloads a URL with progress reporting."""
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            block_size = 64 * 1024  # 64 KB
            start_time = time.time()
            with open(target_path, "wb") as f:
                while True:
                    if self.is_cancelled:
                        raise Exception("DOWNLOAD_CANCELLED")
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        file_ratio = downloaded / total_size
                        current_pct = int(base_pct + file_ratio * weight)
                        elapsed = time.time() - start_time
                        speed_mb = (downloaded / (1024 * 1024)) / (elapsed if elapsed > 0 else 1)
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        status_str = f"Downloading... {mb_down:.1f}MB / {mb_total:.1f}MB ({speed_mb:.1f} MB/s)"
                        self.progress_signal.emit(min(95, current_pct), status_str)

    def _extract_ffmpeg_zip(self, zip_path: str, target_dir: str):
        """Extracts only ffmpeg.exe and ffprobe.exe from the downloaded archive."""
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                base_name = os.path.basename(member).lower()
                if base_name in ["ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"]:
                    target_dest = os.path.join(target_dir, base_name)
                    if os.path.exists(target_dest):
                        try:
                            os.remove(target_dest)
                        except Exception:
                            pass
                    with zf.open(member) as source, open(target_dest, "wb") as target:
                        shutil.copyfileobj(source, target)
