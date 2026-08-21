# Handoff Report — Implementation Round 1

## Summary of Changes

### R1. Core Downloader & Workers Fixes
- **`core/downloader.py`**:
  - Added `os.makedirs(save_dir, exist_ok=True)` in `DownloadThread.run()` before output template construction and yt-dlp invocation.
  - Added `{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}` postprocessor prior to `EmbedThumbnail` so that WebP thumbnails are converted to JPG for audio and video downloads.
  - Removed dead `custom_metadata` parameter from `DownloadThread.__init__` and removed metadata injection logic and unused imports (`json`, `datetime`).
- **`core/workers.py`**:
  - Updated `ThumbnailWorker` to accept `(index, thumb_url=None, video_id=None)`, prioritizing direct URLs (for non-YouTube sites such as Facebook, TikTok, Twitter/X, Instagram, SoundCloud, Vimeo) while falling back to YouTube thumbnail URLs when a video ID is present.
  - Removed unused `apply_metadata()` function and unused imports (`time`, `glob`, `concurrent.futures`).

### R2. Home Tab & Queue Tab UI/Logic Fixes
- **`gui/tabs/tab_home.py`**:
  - Fixed `calc_size()` to safely handle `duration_sec = None` (live streams) or `0` by returning empty string without raising `TypeError`.
  - Fixed video resolution formatting in single video mode (`get_video_desc()`) and playlist quality dropdown options to prevent duplicate resolution strings (e.g. `(1080p) - 1080p`) and unformatted `{}` placeholders.
  - Removed redundant hidden `type_combo` and `type_label` widgets and streamlined `quality_combo` selection logic.
  - Updated thumbnail worker invocation in both single video and playlist modes to pass `thumb_url=entry.get('thumbnail')` / `info.get('thumbnail')` and `video_id`.
  - Removed duplicate `SmartTitleLabel` class and imported it from `gui.widgets`.
  - Removed unused `custom_metadata` references.
- **`gui/tabs/tab_queue.py`**:
  - Fixed `_create_and_insert_queue_item()` to insert items at `max(0, self.queue_layout.count() - 1)` so items maintain sequential ascending order (1, 2, 3...).
  - Removed `custom_metadata` parameter from `_create_and_insert_queue_item()`.
- **`gui/widgets.py`**:
  - Centralized `SmartTitleLabel` supporting `setText()`, `setToolTip()`, and elision.
  - Removed `custom_metadata` parameter and references from `DownloadQueueItem`.

### R3. Helpers & Strings Cleanup
- **`utils/helpers.py`**:
  - Removed duplicate `resource_path` function definition.
- **`utils/strings.py`**:
  - Implemented proper system language detection across `QLocale`, `locale.getdefaultlocale()`, and `LANG`/`LANGUAGE` environment variables to support Arabic systems when configured as `"system"`.
  - Updated `QUAL_*` strings to remove raw `{}` placeholders.
  - Cleaned up unused string constants (`BTN_CHECK_LINK`, `BTN_DOWNLOAD_SUB`, `BTN_START`, `BTN_OPEN_FOLDER`, `BTN_FORCE`, `BTN_SET_DONE`, `LBL_QUALITY`, `LBL_BATCH_DESC`, `CHK_SUB_AVAILABLE`, `CHK_SUBS_BEST_EFFORT`, `CHK_NO_SUBS`, `STATUS_PAUSED_DATA`, `STATUS_COMPLETED`, `STATUS_PAUSED`, `MSG_SAVED`, `MSG_LANG_SELECTED`, `TOOLTIP_STOP`).
- **`gui/settings_page.py`**:
  - Updated `downgrade_check` to use `strings.CHK_SET_DOWNGRADE`.

## Verification Record
- **Compilation Check**: `python3 -m py_compile main.py core/*.py gui/*.py gui/tabs/*.py utils/*.py tests/*.py` passed with 0 errors.
- **Unit Test Suite**: 17 unit tests in `tests/test_refactor.py` covering all criteria and edge cases passed with 0 failures and 0 errors.
