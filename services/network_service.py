import sys
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal


class NetworkService(QObject):
    statusChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    # =========================
    # PUBLIC API
    # =========================
    def get_status(self) -> dict:
        if sys.platform.startswith("win"):
            return self._status_windows()
        else:
            return self._status_linux()

    def connect_wifi(self, ssid: str, password: str | None) -> bool:
        if sys.platform.startswith("win"):
            return self._connect_windows(ssid, password)
        else:
            return self._connect_linux(ssid, password)

    # =========================
    # WINDOWS IMPLEMENTATION
    # =========================
    def _status_windows(self):
        try:
            out = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                encoding="utf-8",
                errors="ignore",
            )
            ssid = None
            for line in out.splitlines():
                if "SSID" in line and ":" in line:
                    ssid = line.split(":")[1].strip()
            return {
                "connected": bool(ssid),
                "ssid": ssid,
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _connect_windows(self, ssid, password):
        try:
            profile = f"""
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""
            path = "wifi-profile.xml"
            with open(path, "w", encoding="utf-8") as f:
                f.write(profile)

            subprocess.check_call(
                ["netsh", "wlan", "add", "profile", f"filename={path}"]
            )
            subprocess.check_call(
                ["netsh", "wlan", "connect", f"name={ssid}"]
            )

            self.statusChanged.emit(self.get_status())
            return True
        except Exception as e:
            print("[WIFI ERROR]", e)
            return False

    # =========================
    # LINUX / PI IMPLEMENTATION
    # =========================
    def _status_linux(self):
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                encoding="utf-8",
            )
            for line in out.splitlines():
                if line.startswith("yes:"):
                    return {
                        "connected": True,
                        "ssid": line.split(":", 1)[1],
                    }
            return {"connected": False}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _connect_linux(self, ssid, password):
        try:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd += ["password", password]
            subprocess.check_call(cmd)
            self.statusChanged.emit(self.get_status())
            return True
        except Exception as e:
            print("[WIFI ERROR]", e)
            return False
