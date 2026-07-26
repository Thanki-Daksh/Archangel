import os
import sys
from pathlib import Path

def ensure_user_path_registered() -> bool:
    """Ensure the virtual environment's Scripts directory is in Windows User PATH."""
    if os.name != "nt":
        return False
    try:
        import winreg
        import ctypes

        scripts_dir = str(Path(sys.executable).parent.resolve())
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""

            paths = [p.strip() for p in current_path.split(";") if p.strip()]
            if not any(p.lower() == scripts_dir.lower() for p in paths):
                new_path = f"{current_path};{scripts_dir}" if current_path else scripts_dir
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                ctypes.windll.user32.SendMessageTimeoutW(
                    0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
                )
                return True
    except Exception:
        pass
    return False
