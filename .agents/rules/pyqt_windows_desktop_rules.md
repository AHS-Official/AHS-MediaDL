---
description: Critical guidelines for PyQt desktop applications on Windows regarding process lifecycle, system tray backgrounding, memory trimming, and subprocess flags.
globs: ["**/*.py"]
---

# PyQt Windows Desktop Application Guidelines

### 1. Subprocess Spawning on Windows (`SW_HIDE` Invariant)
- **Never** pass `startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW` when spawning a GUI application unless `startupinfo.wShowWindow` is explicitly set to a visible mode (`SW_SHOWNORMAL = 1` or `SW_SHOW = 5`).
- The default value of `startupinfo.wShowWindow` in Python is `0` (`SW_HIDE`). Spawning a GUI application with `STARTF_USESHOWWINDOW` without setting `wShowWindow` will instruct Windows to permanently hide all windows created by the child process, leaving invisible processes running in Task Manager.
- For running `.py` scripts silently, prefer `pythonw.exe` without injecting `CREATE_NO_WINDOW` (`0x08000000`) or `SW_HIDE` into GUI child processes.

### 2. "Run in Background" / System Tray Minimization
- When an application supports running in the background upon window close:
  - Do **NOT** terminate the main process and spawn a secondary listener script. This discards running downloads/tasks, fragments process state, and creates race conditions with tray icons.
  - Set `app.setQuitOnLastWindowClosed(False)` on `QApplication`.
  - In `closeEvent(event)`:
    ```python
    if run_in_background and not getattr(self, 'bypass_close_event', False):
        event.ignore()
        self.hide()
        trim_working_set_memory()
        return
    ```
  - Restore instantly using `self.showNormal()`, `self.activateWindow()`, and `self.raise_()`.

### 3. Windows Working Set Memory Optimization
- When hiding to the system tray, reclaim physical RAM from ~100+ MB down to ~4-10 MB using Windows Working Set trimming:
  ```python
  def trim_memory():
      if sys.platform == 'win32':
          try:
              import ctypes
              from ctypes import wintypes
              kernel32 = ctypes.windll.kernel32
              kernel32.GetCurrentProcess.restype = ctypes.c_void_p
              psapi = ctypes.windll.psapi
              psapi.EmptyWorkingSet.argtypes = [ctypes.c_void_p]
              psapi.EmptyWorkingSet.restype = wintypes.BOOL
              psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
          except Exception:
              pass
  ```

### 4. 64-Bit Ctypes Handle Safety
- Always declare `.argtypes` and `.restype` on `ctypes` functions when dealing with `HWND`, `HANDLE`, or pointer-sized integers on 64-bit Windows to prevent 32-bit truncation crashes.
