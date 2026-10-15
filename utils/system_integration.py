import sys
import os
import ctypes
from utils.logger import logger

def create_linux_desktop_entry():
    if not sys.platform.startswith("linux"):
        return
    try:
        home = os.path.expanduser("~")
        desktop_dir = os.path.join(home, ".local", "share", "applications")
        os.makedirs(desktop_dir, exist_ok=True)
        desktop_file = os.path.join(desktop_dir, "AHS-MediaDL.desktop")
        
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.abspath(os.path.join(app_dir, "assets", "icon.ico"))
        script_path = os.path.abspath(sys.argv[0])
        
        content = f"""[Desktop Entry]
Type=Application
Name=AHS-MediaDL
Comment=AHS Media Downloader
Exec={sys.executable} "{script_path}" %U
Icon={icon_path}
Terminal=false
Categories=Utility;
StartupWMClass=AHS-MediaDL
MimeType=x-scheme-handler/ahs-mediadl;
"""
        with open(desktop_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        os.chmod(desktop_file, 0o755)
    except Exception as e:
        logger.error(f"Failed to create desktop entry: {e}")

def register_protocol_handler():
    if sys.platform != 'win32':
        return
    try:
        import winreg
        executable = sys.executable
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_py_path = os.path.join(app_dir, "main.py")
        base_exec = os.path.basename(executable).lower()
        is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
        if is_python:
            command = f'"{executable}" "{main_py_path}" "%1"'
        else:
            command = f'"{executable}" "%1"'
        key_path = r"Software\Classes\dl"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "URL:dl Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, command)
    except Exception as e:
        logger.error(f"Failed to register protocol handler: {e}")

def register_start_menu_shortcut():
    if sys.platform != 'win32':
        return
    try:
        import subprocess
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(app_dir, 'assets', 'icon.ico')
        shortcut_path = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'AHS-MediaDL.lnk')
        if os.path.exists(shortcut_path):
            return
        target = sys.executable
        base_exec = os.path.basename(target).lower()
        is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
        if is_python:
            pythonw = target.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                target = pythonw
            main_py = os.path.join(app_dir, "main.py")
            arguments = f'"{main_py}"'
        else:
            arguments = ""
        
        ps_cmd = (
            f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut_path}'); "
            f"$s.TargetPath = '{target}'; "
            f"$s.Arguments = '{arguments}'; "
            f"$s.WorkingDirectory = '{app_dir}'; "
            f"$s.IconLocation = '{icon_path},0'; "
            f"$s.Save(); "
            f"$c = @' \n"
            f"using System; \n"
            f"using System.Runtime.InteropServices; \n"
            f"namespace ShellUtils {{ \n"
            f"    [ComImport, Guid(\"886D8EE6-8580-47A5-9C4A-44B473189C21\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] \n"
            f"    public interface IPropertyStore {{ int GetCount(out uint c); int GetAt(uint i, out IntPtr k); int GetValue(IntPtr k, out IntPtr v); int SetValue(ref PROPERTYKEY k, ref PROPVARIANT v); int Commit(); }} \n"
            f"    [StructLayout(LayoutKind.Sequential)] public struct PROPERTYKEY {{ public Guid fmtid; public uint pid; }} \n"
            f"    [StructLayout(LayoutKind.Explicit)] public struct PROPVARIANT {{ [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr pwszVal; }} \n"
            f"    public class ShortcutAppID {{ \n"
            f"        [DllImport(\"shell32.dll\", CharSet = CharSet.Unicode, SetLastError = true)] private static extern int SHGetPropertyStoreFromParsingName([MarshalAs(UnmanagedType.LPWStr)] string p, IntPtr b, uint f, ref Guid r, out IPropertyStore s); \n"
            f"        public static void SetID(string path, string id) {{ \n"
            f"            try {{ IPropertyStore s; Guid g = new Guid(\"886D8EE6-8580-47A5-9C4A-44B473189C21\"); if (SHGetPropertyStoreFromParsingName(path, IntPtr.Zero, 2, ref g, out s) == 0 && s != null) {{ PROPERTYKEY k = new PROPERTYKEY(); k.fmtid = new Guid(\"9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3\"); k.pid = 5; PROPVARIANT v = new PROPVARIANT(); v.vt = 31; v.pwszVal = Marshal.StringToCoTaskMemUni(id); s.SetValue(ref k, ref v); s.Commit(); Marshal.FreeCoTaskMem(v.pwszVal); }} }} catch {{}} \n"
            f"        }} \n"
            f"    }} \n"
            f"}} \n"
            f"'@ \n"
            f"Add-Type -TypeDefinition $c; [ShellUtils.ShortcutAppID]::SetID('{shortcut_path}', 'AHS-MediaDL')"
        )
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd], creationflags=0x08000000, startupinfo=startupinfo)
        else:
            subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd])
    except Exception as e:
        logger.error(f"Failed to register start menu shortcut: {e}")

def set_app_user_model_id(app_id):
    if sys.platform == 'win32':
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            import winreg
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.abspath(os.path.join(app_dir, 'assets', 'icon.ico'))
            key_path = f"Software\\Classes\\AppUserModelId\\{app_id}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "AHS-MediaDL")
                winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, icon_path)
                winreg.SetValueEx(key, "IconBackgroundColor", 0, winreg.REG_SZ, "00000000")
        except Exception as e:
            logger.error(f"Failed to set AppUserModelID: {e}")
