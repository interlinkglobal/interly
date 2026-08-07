"""Local capabilities Interly may request, but never run without approval."""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from computer_agent.browser import BROWSER
from computer_agent.dev_workflows import RepositoryWorkflow
from computer_agent.files import (
    compare_files,
    create_text_file,
    edit_text_file,
    manage_path,
    read_text_file,
    search_files,
)
from computer_agent.system import installed_applications, power_action, system_metrics
from computer_agent.web import download_public_file, read_webpage, research_web, search_web


@dataclass(frozen=True)
class LocalOnlyResult:
    """Keep sensitive output in the terminal and send only a status to the model."""

    model_status: str
    terminal_output: str

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Read the current date, time, and timezone from this computer.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": (
                "Open one application returned by find_applications. Never invent an ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {
                        "type": "string",
                        "description": "Exact registered ID returned by find_applications.",
                    },
                    "application_name": {
                        "type": "string",
                        "description": "Exact display name returned by find_applications.",
                    },
                },
                "required": ["application_id", "application_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_executable_command",
            "description": (
                "Open an explicitly requested Windows executable command such as chrome or "
                "chrome.exe. Accepts one command token only; no paths, arguments, or shell syntax."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command_name": {
                        "type": "string",
                        "description": "Exact executable token stated by the user.",
                    }
                },
                "required": ["command_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_applications",
            "description": (
                "Search applications registered with Windows. Always use this before "
                "open_application, even for applications opened earlier."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Application name requested by the user.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "logout_windows",
            "description": "Sign the current user out of Windows. Unsaved work may be lost.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_read_command",
            "description": (
                "Run one approved read-only Windows information command. Use processes to "
                "answer how many tasks or processes are running."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": [
                            "processes",
                            "systeminfo",
                            "ipconfig",
                            "wifi",
                            "users",
                            "identity",
                            "hostname",
                            "network_adapters",
                            "routes",
                            "disks",
                        ],
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_processes",
            "description": (
                "Search running Windows processes by name or window title. Always use this "
                "before close_or_kill_process."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_or_kill_process",
            "description": (
                "Close or forcibly kill one exact process returned by find_processes. Use "
                "close normally; use kill only when explicitly requested or unresponsive."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["close", "kill"]},
                    "process_id": {"type": "integer", "minimum": 1},
                    "process_name": {"type": "string"},
                },
                "required": ["action", "process_id", "process_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the public web directly without opening a browser.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Read and extract text from one public HTTP or HTTPS webpage.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "download_public_file",
            "description": (
                "Download one direct public file URL to an exact local destination. "
                "Use for exposed MP4, image, archive, document, or other file links; not webpages."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "destination": {
                        "type": "string",
                        "description": "Exact destination path including filename and extension.",
                    },
                },
                "required": ["url", "destination"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "windows_power_action",
            "description": "Lock, sleep, restart, or shut down Windows.",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["lock", "sleep", "restart", "shutdown"]}},
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_system_metrics",
            "description": "Read CPU, memory, disk, network, GPU, temperature, and battery metrics.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_installed_applications",
            "description": "List installed applications and registry-reported estimated sizes.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_web",
            "description": "Run deduplicated multi-source web research with source-quality scoring.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_url",
            "description": "Open a public URL in Interly's isolated Playwright browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read_page",
            "description": "Read rendered text from the active isolated-browser tab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["visible_text"],
                        "description": "Use visible_text to read the rendered page body.",
                    }
                },
                "required": ["mode"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_tabs",
            "description": "List, switch, or close isolated-browser tabs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "switch", "close"]},
                    "index": {"type": "integer", "minimum": 0},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_scroll",
            "description": "Scroll the active isolated-browser tab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"]},
                    "amount": {"type": "integer", "minimum": 100, "maximum": 5000},
                },
                "required": ["direction", "amount"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Navigate the active isolated-browser tab backward or forward.",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["back", "forward"]}},
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_controls",
            "description": "List visible interactive controls with stable numeric IDs.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click_control",
            "description": "Click one control previously returned by browser_inspect_controls.",
            "parameters": {
                "type": "object",
                "properties": {"control_id": {"type": "integer", "minimum": 0}, "control_description": {"type": "string"}},
                "required": ["control_id", "control_description"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type_text",
            "description": "Type user-approved text into one inspected browser field.",
            "parameters": {
                "type": "object",
                "properties": {"control_id": {"type": "integer", "minimum": 0}, "control_description": {"type": "string"}, "text": {"type": "string", "maxLength": 5000}},
                "required": ["control_id", "control_description", "text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Save a PNG screenshot of the active isolated browser tab.",
            "parameters": {"type": "object", "properties": {"destination": {"type": "string"}}, "required": ["destination"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search a folder recursively by filename, extension, and optional text content.",
            "parameters": {"type": "object", "properties": {"root": {"type": "string"}, "query": {"type": "string"}, "extension": {"type": "string"}, "content": {"type": "string"}, "modified_after": {"type": "string", "description": "Optional ISO date/time lower bound."}, "modified_before": {"type": "string", "description": "Optional ISO date/time upper bound."}}, "required": ["root", "query"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Read one approved text or source-code file up to 1 MB.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_text_file",
            "description": "Create a new UTF-8 text file without overwriting an existing file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_text_file",
            "description": "Replace one exact passage in an existing text file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_path",
            "description": "Create a folder, or copy, move, or rename an exact file or folder without overwriting.",
            "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["mkdir", "copy", "move", "rename"]}, "source": {"type": "string"}, "destination": {"type": "string"}}, "required": ["action", "source", "destination"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_repository",
            "description": "Inspect a repository directory and list its files.",
            "parameters": {"type": "object", "properties": {"root": {"type": "string"}}, "required": ["root"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_repository_command",
            "description": "Run a bounded command inside a repository directory.",
            "parameters": {"type": "object", "properties": {"root": {"type": "string"}, "command": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "integer", "minimum": 1}}, "required": ["root", "command"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_files",
            "description": "Compare two approved text files and return a unified diff.",
            "parameters": {"type": "object", "properties": {"left": {"type": "string"}, "right": {"type": "string"}}, "required": ["left", "right"], "additionalProperties": False},
        },
    },
]

READ_COMMANDS: dict[str, tuple[str, list[str]]] = {
    "processes": ("tasklist /FO CSV /NH", ["tasklist.exe", "/FO", "CSV", "/NH"]),
    "systeminfo": ("systeminfo", ["systeminfo.exe"]),
    "ipconfig": ("ipconfig /all", ["ipconfig.exe", "/all"]),
    "wifi": ("netsh wlan show all", ["netsh.exe", "wlan", "show", "all"]),
    "users": ("net user", ["net.exe", "user"]),
    "identity": ("whoami", ["whoami.exe"]),
    "hostname": ("hostname", ["hostname.exe"]),
    "network_adapters": (
        "netsh interface show interface",
        ["netsh.exe", "interface", "show", "interface"],
    ),
    "routes": ("route print", ["route.exe", "print"]),
    "disks": (
        "PowerShell Get-Volume",
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-Volume | Select-Object DriveLetter,FileSystemLabel,FileSystem,SizeRemaining,Size",
        ],
    ),
}

PROTECTED_PROCESSES = {
    "csrss",
    "lsass",
    "services",
    "smss",
    "system",
    "wininit",
    "winlogon",
}


def get_current_time() -> str:
    """Return the local clock in a format the model can interpret."""
    now = datetime.now().astimezone()
    return (
        f"Local datetime: {now.isoformat(timespec='seconds')}\n"
        f"Local timezone name: {now.tzname()}\n"
                "Use this timezone name exactly; do not infer a region from the UTC offset."
    )


def get_registered_applications() -> list[dict[str, str]]:
    """Read the Windows Start application catalog using a fixed command."""
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    try:
        raw_apps = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(raw_apps, dict):
        raw_apps = [raw_apps]

    apps = [
        {"name": str(app["Name"]), "application_id": str(app["AppID"])}
        for app in raw_apps
        if app.get("Name") and app.get("AppID")
    ]
    apps.append({"name": "Codex", "application_id": "codex:"})
    return apps


def find_applications(query: str) -> str:
    """Return registered applications whose names resemble the user's query."""
    words = {word for word in query.casefold().split() if word not in {"open", "launch", "app"}}
    matches: list[tuple[int, dict[str, str]]] = []
    for app in get_registered_applications():
        name = app["name"].casefold()
        score = 100 if query.casefold() in name else sum(word in name for word in words) * 10
        if score:
            matches.append((score, app))

    matches.sort(key=lambda item: (-item[0], item[1]["name"]))
    results = [app for _score, app in matches[:10]]
    if not results:
        return f'No registered applications matched "{query}".'
    return json.dumps(results, indent=2)


def resolve_executable_command(command_name: str) -> list[str]:
    """Resolve one plain executable token through PATH and Windows App Paths."""
    token = command_name.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*(?:\.exe)?", token):
        return []
    executable = token if token.casefold().endswith(".exe") else f"{token}.exe"
    candidates: list[str] = []

    try:
        completed = subprocess.run(
            ["where.exe", executable],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode == 0:
            candidates.extend(line.strip() for line in completed.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        import winreg

        key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable}"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    candidates.append(str(winreg.QueryValue(key, None)))
            except OSError:
                continue
    except ImportError:
        pass

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = candidate.strip().strip('"')
        if not cleaned.casefold().endswith(".exe") or cleaned.casefold() in seen:
            continue
        seen.add(cleaned.casefold())
        unique.append(cleaned)
    return unique


def open_executable_command(command_name: str) -> str:
    """Resolve and launch one explicit executable command without invoking a shell."""
    candidates = resolve_executable_command(command_name)
    if not candidates:
        return f'Windows could not resolve executable command "{command_name}"; nothing was opened.'
    if len(candidates) > 1:
        return (
            f'Executable command "{command_name}" matched multiple paths; nothing was opened:\n'
            + "\n".join(candidates)
        )
    subprocess.Popen([candidates[0]])
    return f"Opened executable: {candidates[0]}"


def open_application(application_id: str, application_name: str) -> str:
    """Launch an exact entry from the current Windows application catalog."""
    registered = get_registered_applications()
    valid = any(
        app["application_id"] == application_id and app["name"] == application_name
        for app in registered
    )
    if not valid:
        return "Application ID and name did not match the Windows catalog; nothing was opened."

    if application_id == "codex:":
        os.startfile("codex:")
    else:
        subprocess.Popen(["explorer.exe", rf"shell:AppsFolder\{application_id}"])
    return f"Opened {application_name}."


def get_running_processes() -> list[dict[str, Any]]:
    """Read process identity and visible window titles using a fixed query."""
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-Process | Select-Object Id,ProcessName,MainWindowTitle | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        processes = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    return processes if isinstance(processes, list) else [processes]


def find_processes(query: str) -> str:
    """Return running processes matching a user-provided name."""
    ignored = {"close", "kill", "force", "terminate", "app", "task", "process"}
    words = {word for word in query.casefold().split() if word not in ignored}
    matches: list[dict[str, Any]] = []
    for process in get_running_processes():
        name = str(process.get("ProcessName", ""))
        title = str(process.get("MainWindowTitle", ""))
        searchable = f"{name} {title}".casefold()
        if words and any(word in searchable for word in words):
            matches.append(
                {
                    "process_id": process.get("Id"),
                    "process_name": name,
                    "window_title": title or None,
                }
            )
    if not matches:
        return f'No running process matched "{query}".'
    return json.dumps(matches[:20], indent=2)


def close_or_kill_process(action: str, process_id: int, process_name: str) -> str:
    """End an exact current process unless it is protected by policy."""
    current = next(
        (
            process
            for process in get_running_processes()
            if process.get("Id") == process_id
            and str(process.get("ProcessName", "")).casefold() == process_name.casefold()
        ),
        None,
    )
    if current is None:
        return "PID and process name no longer match a running process; nothing was ended."
    if process_name.casefold().removesuffix(".exe") in PROTECTED_PROCESSES or process_id <= 4:
        return "Interlink blocks ending this critical Windows process."
    if action not in {"close", "kill"}:
        return "Unknown process action; nothing was ended."

    command = ["taskkill.exe", "/PID", str(process_id)]
    if action == "kill":
        command.append("/F")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = (completed.stdout or completed.stderr).strip()
    return f"Exit code: {completed.returncode}\n{output}"


def logout_windows() -> str:
    """Sign out of Windows after the caller has obtained explicit approval."""
    subprocess.Popen(["shutdown.exe", "/l"])
    return "Windows logout started."


def run_read_command(command: str) -> str:
    """Run only a command selected from the immutable read-only allowlist."""
    definition = READ_COMMANDS.get(command)
    if definition is None:
        return f"Read command is not allowed: {command}"

    display_command, arguments = definition
    try:
        completed = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"{display_command} failed: {error}"

    output = (completed.stdout or completed.stderr).strip()
    if command == "processes" and output:
        process_count = len(output.splitlines())
        output = f"Running process count: {process_count}\n\n{output}"
    if len(output) > 40_000:
        output = output[:40_000] + "\n[Output truncated by Interlink]"

    return f"Command: {display_command}\nExit code: {completed.returncode}\n{output}"


def describe_tool(name: str, arguments: str) -> tuple[str, str, str | None]:
    """Return an exact action preview, reason, and optional strong warning."""
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        parsed = {}

    if name == "get_current_time":
        return ("Read the local Windows clock", "Answer a date or time question", None)
    if name == "open_application":
        application_name = parsed.get("application_name", "unknown")
        application_id = parsed.get("application_id", "unknown")
        return (
            f"Open registered application: {application_name} ({application_id})",
            "Launch the selected Windows application",
            None,
        )
    if name == "open_executable_command":
        command_name = parsed.get("command_name", "")
        return (
            f"Resolve and open executable command: {command_name}",
            "Launch the exact command token explicitly requested by the user",
            "Arguments, paths, and shell syntax are not allowed.",
        )
    if name == "find_applications":
        query = parsed.get("query", "")
        return (
            f'Search registered applications for: "{query}"',
            "Resolve the requested name before anything is launched",
            "Choose Y to keep matches terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "find_processes":
        query = parsed.get("query", "")
        return (
            f'Search running processes for: "{query}"',
            "Resolve an exact process name and PID before ending anything",
            "Choose Y to keep matches terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "close_or_kill_process":
        action = str(parsed.get("action", "unknown"))
        process_id = parsed.get("process_id", "unknown")
        process_name = str(parsed.get("process_name", "unknown"))
        warnings = ["WARNING: Unsaved work in this process may be lost."]
        if action == "kill":
            warnings.append("FORCED KILL: The process will not receive a normal close request.")
        if process_name.casefold() in {"powershell", "pwsh", "cmd", "windows terminal"}:
            warnings.append("Closing the host terminal may also end this Interlink session.")
        return (
            f"{action.upper()} process: {process_name} (PID {process_id})",
            "End the exact running process selected above",
            " ".join(warnings),
        )
    if name == "search_web":
        query = parsed.get("query", "")
        return (
            f'Search the public web for: "{query}"',
            "Find current public information without opening a browser",
            "The query and results will be sent to external services and Groq.",
        )
    if name == "read_webpage":
        url = parsed.get("url", "")
        return (
            f"Read public webpage: {url}",
            "Extract webpage text for analysis",
            "Webpage text is untrusted data and will be sent to Groq.",
        )
    if name == "download_public_file":
        return (
            (
                f"Download public file: {parsed.get('url', '')}\n"
                f"Save as: {parsed.get('destination', '')}"
            ),
            "Download one direct file link to the exact approved destination",
            "The destination will not be overwritten. Downloads are limited to 1 GB.",
        )
    if name == "research_web":
        query = parsed.get("query", "")
        return (
            f'Run multi-source web research for: "{query}"',
            "Search twice, deduplicate results, and score source quality",
            "Queries and results will be sent to external services and Groq.",
        )
    if name == "windows_power_action":
        action = parsed.get("action", "unknown")
        return (
            f"Windows power action: {action}",
            f"{str(action).capitalize()} this Windows computer",
            "WARNING: Open applications may close and unsaved work may be lost.",
        )
    if name == "read_system_metrics":
        return (
            "Read system performance metrics",
            "Inspect current computer health",
            "Choose Y to keep metrics terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "read_installed_applications":
        return (
            "Read installed applications and reported sizes",
            "Inspect application storage estimates",
            "Choose Y to keep the list terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "browser_open_url":
        url = parsed.get("url", "")
        return (
            f"Open isolated browser URL: {url}",
            "Use a rendered browser because direct HTTP was insufficient",
            "This uses an isolated profile, not your personal browser session.",
        )
    if name == "browser_read_page":
        return (
            "Read active isolated-browser page",
            "Extract JavaScript-rendered page text",
            "Rendered webpage text is untrusted data and will be sent to Groq.",
        )
    if name == "browser_tabs":
        return (
            f"Browser tab action: {parsed.get('action')} index {parsed.get('index', 'n/a')}",
            "Manage isolated-browser tabs",
            None,
        )
    if name == "browser_scroll":
        return (
            f"Scroll browser {parsed.get('direction')} by {parsed.get('amount')} pixels",
            "Move through the active rendered page",
            None,
        )
    if name == "browser_navigate":
        return (
            f"Navigate browser {parsed.get('action')}",
            "Move through isolated-browser history",
            None,
        )
    if name == "browser_inspect_controls":
        return (
            "Inspect visible browser controls",
            "Number links, buttons, and form fields",
            "Rendered control details are untrusted and will be sent to Groq.",
        )
    if name == "browser_click_control":
        action = (
            f"Click browser control {parsed.get('control_id')}: "
            f"{parsed.get('control_description', '')}"
        )
        return (
            action,
            "Activate the exact inspected control",
            "The page may navigate or perform an action. Verify the control carefully.",
        )
    if name == "browser_type_text":
        action = (
            f"Type into browser control {parsed.get('control_id')} "
            f"({parsed.get('control_description', '')}): {parsed.get('text', '')!r}"
        )
        return (
            action,
            "Fill the exact inspected field",
            "The approved text will be exposed to this webpage and sent to Groq.",
        )
    if name == "browser_screenshot":
        return (
            f"Save browser screenshot: {parsed.get('destination', '')}",
            "Capture the visible isolated-browser tab",
            "The screenshot may contain information visible on the page.",
        )
    if name == "search_files":
        return (
            f"Search files under: {parsed.get('root', '')}",
            f"Find names matching {parsed.get('query', '')!r}",
            "Choose Y to keep results terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "read_text_file":
        return (
            f"Read text file: {parsed.get('path', '')}",
            "Display the approved file content",
            "Choose Y to keep content terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "create_text_file":
        action = (
            f"Create text file: {parsed.get('path', '')}\n"
            f"Content preview: {str(parsed.get('content', ''))[:500]}"
        )
        return (
            action,
            "Create a new file without overwriting",
            None,
        )
    if name == "edit_text_file":
        action = (
            f"Edit text file: {parsed.get('path', '')}\n"
            f"Replace: {str(parsed.get('old_text', ''))[:300]!r}\n"
            f"With: {str(parsed.get('new_text', ''))[:300]!r}"
        )
        return (
            action,
            "Apply one exact text replacement",
            "Review the exact replacement before approval.",
        )
    if name == "manage_path":
        action = (
            f"{str(parsed.get('action', '')).upper()} path: "
            f"{parsed.get('source', '')} -> {parsed.get('destination', '')}"
        )
        return (
            action,
            "Manage the exact approved filesystem path",
            "Moving or renaming changes the source location; destinations are not overwritten.",
        )
    if name == "inspect_repository":
        return (
            f"Inspect repository: {parsed.get('root', '')}",
            "List repository files and structure",
            None,
        )
    if name == "run_repository_command":
        return (
            f"Run repository command: {parsed.get('command', [])}",
            "Execute a bounded command inside the repository",
            "Review the command and timeout before approval.",
        )
    if name == "compare_files":
        return (
            f"Compare files: {parsed.get('left', '')} and {parsed.get('right', '')}",
            "Show their text differences",
            "Choose Y to keep the diff terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "logout_windows":
        return (
            "Run: shutdown.exe /l",
            "Sign the current user out of Windows",
            "WARNING: This closes your Windows session. Unsaved work may be lost.",
        )
    if name == "run_read_command":
        command = str(parsed.get("command", ""))
        definition = READ_COMMANDS.get(command)
        display_command = definition[0] if definition else f"unknown read command: {command}"
        warning = "Choose Y to keep output terminal-only, or A to explicitly allow Groq access."
        return (f"Run read command: {display_command}", "Inspect local system information", warning)
    return (f"Unknown tool: {name}", "No recognized reason", "This action will be denied.")


def execute_tool(name: str, arguments: str = "{}") -> str | LocalOnlyResult:
    """Execute a known tool. Approval must happen before this function is called."""
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "Tool arguments were invalid JSON; nothing was executed."

    if name == "get_current_time":
        return get_current_time()
    if name == "open_application":
        return open_application(
            str(parsed.get("application_id", "")),
            str(parsed.get("application_name", "")),
        )
    if name == "open_executable_command":
        return open_executable_command(str(parsed.get("command_name", "")))
    if name == "find_applications":
        return LocalOnlyResult(
            model_status=(
                "The application search completed and its matches were displayed only in the "
                "user's terminal. Ask the user to type the exact application name and ID they "
                "want to open; do not infer the private matches."
            ),
            terminal_output=find_applications(str(parsed.get("query", ""))),
        )
    if name == "find_processes":
        return LocalOnlyResult(
            model_status=(
                "The process search completed and its matches were displayed only in the "
                "user's terminal. Ask the user to type the exact process name and PID they "
                "want to close or kill; do not infer the private matches."
            ),
            terminal_output=find_processes(str(parsed.get("query", ""))),
        )
    if name == "close_or_kill_process":
        try:
            process_id = int(parsed.get("process_id", 0))
        except (TypeError, ValueError):
            return "Invalid process ID; nothing was ended."
        return close_or_kill_process(
            str(parsed.get("action", "")),
            process_id,
            str(parsed.get("process_name", "")),
        )
    if name == "search_web":
        return search_web(str(parsed.get("query", "")))
    if name == "read_webpage":
        return read_webpage(str(parsed.get("url", "")))
    if name == "download_public_file":
        return download_public_file(
            str(parsed.get("url", "")), str(parsed.get("destination", ""))
        )
    if name == "research_web":
        return research_web(str(parsed.get("query", "")))
    if name == "windows_power_action":
        return power_action(str(parsed.get("action", "")))
    if name == "read_system_metrics":
        return LocalOnlyResult(
            model_status=(
                "The system-metrics read completed. The metrics were displayed only in the "
                "user's terminal and were not provided to you. Do not infer their values."
            ),
            terminal_output=system_metrics(),
        )
    if name == "read_installed_applications":
        return LocalOnlyResult(
            model_status=(
                "The installed-application report completed. The report was displayed only in "
                "the user's terminal and was not provided to you. Do not infer its contents."
            ),
            terminal_output=installed_applications(),
        )
    if name == "browser_open_url":
        return BROWSER.open_url(str(parsed.get("url", "")))
    if name == "browser_read_page":
        return BROWSER.read_page()
    if name == "browser_tabs":
        action = str(parsed.get("action", ""))
        index = int(parsed.get("index", 0))
        if action == "list":
            return BROWSER.list_tabs()
        if action == "switch":
            return BROWSER.switch_tab(index)
        if action == "close":
            return BROWSER.close_tab(index)
        return f"Unknown browser tab action: {action}"
    if name == "browser_scroll":
        return BROWSER.scroll(str(parsed.get("direction", "down")), int(parsed.get("amount", 800)))
    if name == "browser_navigate":
        return BROWSER.navigate(str(parsed.get("action", "")))
    if name == "browser_inspect_controls":
        return BROWSER.inspect_controls()
    if name == "browser_click_control":
        return BROWSER.click_control(int(parsed.get("control_id", -1)))
    if name == "browser_type_text":
        return BROWSER.type_text(
            int(parsed.get("control_id", -1)), str(parsed.get("text", ""))
        )
    if name == "browser_screenshot":
        return BROWSER.screenshot(str(parsed.get("destination", "")))
    if name == "search_files":
        return LocalOnlyResult(
            "The file search completed and its results were displayed only in the terminal.",
            search_files(
                str(parsed.get("root", "")),
                str(parsed.get("query", "")),
                str(parsed.get("extension", "")),
                str(parsed.get("content", "")),
                str(parsed.get("modified_after", "")),
                str(parsed.get("modified_before", "")),
            ),
        )
    if name == "read_text_file":
        return LocalOnlyResult(
            "The approved file was read and its content was displayed only in the terminal.",
            read_text_file(str(parsed.get("path", ""))),
        )
    if name == "create_text_file":
        return create_text_file(
            str(parsed.get("path", "")), str(parsed.get("content", ""))
        )
    if name == "edit_text_file":
        return edit_text_file(
            str(parsed.get("path", "")),
            str(parsed.get("old_text", "")),
            str(parsed.get("new_text", "")),
        )
    if name == "manage_path":
        return manage_path(
            str(parsed.get("action", "")),
            str(parsed.get("source", "")),
            str(parsed.get("destination", "")),
        )
    if name == "inspect_repository":
        workflow = RepositoryWorkflow(str(parsed.get("root", "")))
        return json.dumps(workflow.inspect(), indent=2)
    if name == "run_repository_command":
        payload = parsed
        workflow = RepositoryWorkflow(str(payload.get("root", "")))
        return json.dumps(
            workflow.run_command(list(payload.get("command", [])), timeout=int(payload.get("timeout", 30))),
            indent=2,
        )
    if name == "compare_files":
        return LocalOnlyResult(
            "The file comparison completed and its diff was displayed only in the terminal.",
            compare_files(str(parsed.get("left", "")), str(parsed.get("right", ""))),
        )
    if name == "logout_windows":
        return logout_windows()
    if name == "run_read_command":
        command = str(parsed.get("command", ""))
        return LocalOnlyResult(
            model_status=(
                f"The local read command '{command}' completed. Its sensitive output was shown "
                "only in the user's terminal and was not provided to you. Tell the user the "
                "local-only data is displayed above; do not invent, summarize, or quote it."
            ),
            terminal_output=run_read_command(command),
        )
    return f"Unknown tool: {name}"
