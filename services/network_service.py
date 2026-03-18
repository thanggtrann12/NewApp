import sys
import os
import subprocess
import tempfile
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
            ip = self._get_ip_windows()
            return {
                "connected": bool(ssid),
                "ssid": ssid or "-",
                "ip": ip,
                "signal": "-",
            }
        except Exception as e:
            return {"connected": False, "ssid": "-", "ip": "-", "signal": "-", "error": str(e)}

    def _get_ip_windows(self):
        try:
            out = subprocess.check_output(
                ["ipconfig"],
                encoding="utf-8",
                errors="ignore",
            )
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("IPv4") and ":" in line:
                    return line.split(":", 1)[1].strip()
            return "-"
        except Exception:
            return "-"

    def _connect_windows(self, ssid, password):
        path = ""
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
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".xml",
                delete=False,
            ) as f:
                f.write(profile)
                path = f.name

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
        finally:
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass

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
                    ssid = line.split(":", 1)[1]
                    ip, signal = self._get_ip_signal_linux()
                    return {
                        "connected": True,
                        "ssid": ssid,
                        "ip": ip,
                        "signal": signal,
                    }
            ip, signal = self._get_ip_signal_linux()
            return {
                "connected": False,
                "ssid": "-",
                "ip": ip,
                "signal": signal,
            }
        except Exception as e:
            return {"connected": False, "ssid": "-", "ip": "-", "signal": "-", "error": str(e)}

    def _get_ip_signal_linux(self):
        ip = "-"
        signal = "-"
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "IP4.ADDRESS", "dev", "show"],
                encoding="utf-8",
                errors="ignore",
            )
            for line in out.splitlines():
                if ":" in line:
                    ip = line.split(":")[1].strip().split("/")[0]
                    break
        except Exception:
            pass
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "SIGNAL", "dev", "wifi"],
                encoding="utf-8",
                errors="ignore",
            )
            for line in out.splitlines():
                if line.strip().isdigit():
                    signal = line.strip() + "%"
                    break
        except Exception:
            pass
        return ip, signal

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
