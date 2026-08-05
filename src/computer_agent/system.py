"""Guarded Windows power actions and richer read-only system reports."""

import json
import subprocess
from typing import Any

import psutil


def system_metrics() -> str:
    """Return a best-effort snapshot of CPU, memory, disk, network, battery, and temperatures."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    network = psutil.net_io_counters()
    battery = psutil.sensors_battery()
    try:
        temperatures: Any = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        temperatures = {}
    report: dict[str, Any] = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "cpu_logical_count": psutil.cpu_count(),
        "memory": {
            "percent": memory.percent,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "total_bytes": memory.total,
        },
        "system_disk": {
            "percent": disk.percent,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "total_bytes": disk.total,
        },
        "network_since_boot": {
            "bytes_sent": network.bytes_sent,
            "bytes_received": network.bytes_recv,
        },
        "battery": (
            {
                "percent": battery.percent,
                "plugged_in": battery.power_plugged,
                "seconds_left": battery.secsleft,
            }
            if battery
            else "No battery reported",
        ),
        "temperatures": temperatures or "Not reported by Windows hardware interfaces",
    }
    gpu = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    report["gpu"] = gpu.stdout.strip() or "Not reported"
    return json.dumps(report, indent=2, default=str)


def installed_applications() -> str:
    """Return installed applications and registry-reported sizes without scanning user files."""
    script = (
        "$paths=@('HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*');"
        "Get-ItemProperty $paths -ErrorAction SilentlyContinue | "
        "Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher,EstimatedSize | "
        "Sort-Object EstimatedSize -Descending | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=30,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return f"Installed-application query failed: {completed.stderr.strip()}"
    try:
        apps = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return "Windows returned invalid installed-application data."
    if isinstance(apps, dict):
        apps = [apps]
    normalized = [
        {
            "name": app.get("DisplayName"),
            "version": app.get("DisplayVersion"),
            "publisher": app.get("Publisher"),
            "estimated_size_mb": (
                round(app["EstimatedSize"] / 1024, 1) if app.get("EstimatedSize") else "Not reported"
            ),
        }
        for app in apps[:100]
    ]
    return json.dumps(normalized, indent=2)


def power_action(action: str) -> str:
    """Execute one explicitly selected Windows session or power action."""
    commands = {
        "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
        "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "restart": ["shutdown.exe", "/r", "/t", "0"],
        "shutdown": ["shutdown.exe", "/s", "/t", "0"],
    }
    command = commands.get(action)
    if command is None:
        return f"Unknown power action: {action}"
    subprocess.Popen(command)
    return f"Windows {action} started."
