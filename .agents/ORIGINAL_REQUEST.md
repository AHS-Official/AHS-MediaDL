# Original User Request

## 2026-08-20T08:21:11Z

This is a single self-contained fix and refactor; keep it small and focused.

This is a focused refactor and bug-fix task for the lightweight version of AHS-MediaDL (a PyQt6 and yt-dlp media downloader). Clean up dead code, fix runtime crashes, and ensure solid video/audio downloading across platforms.

Working directory: /mnt/08DE716FDE715642/projects/AHS-MediaDL/AHS-MediaDL 0.2
Integrity mode: development

## Requirements

### R1. Core Downloader & Workers Fixes
- Ensure download directories are created automatically if missing (`os.makedirs(save_dir, exist_ok=True)` in `core/downloader.py`).
- Ensure WebP thumbnails from YouTube/other sites are converted to JPG using `FFmpegThumbnailsConvertor` before embedding via `EmbedThumbnail` in audio/video downloads in `core/downloader.py`.
- Update `ThumbnailWorker` in `core/workers.py` to accept and fetch from direct `thumbnail` URLs extracted by yt-dlp (with fallback to YouTube URL format), supporting non-YouTube sites (Facebook, TikTok, Twitter/X, Instagram, SoundCloud, Vimeo, etc.).
- Clean up unused `custom_metadata` artifacts and unused functions in `core/workers.py` and `core/downloader.py`.

### R2. Home Tab & Queue Tab UI/Logic Fixes
- Fix `calc_size` in `gui/tabs/tab_home.py` to safely handle `duration_sec = None` (live streams or missing duration) without raising `TypeError`.
- Fix quality string formatting so playlist mode does not display unformatted `{}` (e.g. in `QUAL_4K`), and single video mode does not duplicate resolution strings.
- Fix playlist item queue insertion so that items in playlists are enqueued in sequential order (1, 2, 3...) rather than reversed order.
- Remove redundant hidden `type_combo` handling in `gui/tabs/tab_home.py` and streamline `quality_combo`.
- Pass direct thumbnail URLs to `ThumbnailWorker` from `info['thumbnail']` or `entry['thumbnail']`.

### R3. Helpers & Strings Cleanup
- Remove the duplicated `resource_path` definition in `utils/helpers.py`.
- Remove the duplicated `SmartTitleLabel` class and centralize it.
- Fix system language detection in `utils/strings.py` to properly detect Arabic systems when language is set to `"system"`.
- Clean up unused string constants in `utils/strings.py`.

## Acceptance Criteria

### Reliability & Error Handling
- [ ] Running `python3 -m py_compile main.py core/*.py gui/*.py gui/tabs/*.py utils/*.py` completes with zero syntax/compilation errors.
- [ ] No `TypeError` crash occurs when processing live streams or media with `duration = None`.
- [ ] Downloads cleanly create missing target directories without throwing `FileNotFoundError` or `No such file or directory`.
- [ ] WebP thumbnails are converted to JPG and embedded without FFmpeg/AtomicParsley errors.

### UI & Queue Behavior
- [ ] Playlist quality dropdown shows clean labels without empty `{}`.
- [ ] Playlist entries are added to the download queue in ascending order (1, 2, 3...).
- [ ] Single video format dropdown shows clean labels without duplicate resolution tags.
- [ ] Thumbnails load successfully for both YouTube links and non-YouTube links (e.g. TikTok, Vimeo, SoundCloud).

### Code Cleanliness
- [ ] No duplicate function or class definitions across `utils/helpers.py`, `gui/tabs/tab_home.py`, and `gui/widgets.py`.
- [ ] No dead references to unused metadata editor variables.
