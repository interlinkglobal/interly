# Interly

Interly is an experimental, permission-aware Windows computer agent powered by Groq. It can
reason about a request, propose a local or web action, show exactly what it wants to do, and
wait for approval before executing it.

Development follows the checked 100-item plan in [ROADMAP.md](ROADMAP.md).

## Install on Windows

The primary installation path is Windows Package Manager. On a new Windows computer, open
Command Prompt and run:

```cmd
winget install --id InterlinkGlobal.Interly --exact
```

Then launch Interly from any Command Prompt:

```cmd
interly
```

The WinGet package contains a standalone Windows executable and does not require Python, pipx,
Git, Node.js, or npm on the user's computer.

### Development and fallback installer

For branch testing, development installations, or recovery when WinGet is unavailable, open
Command Prompt or PowerShell and run:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/interlinkglobal/Interly/agent/next-ten-roadmap/install.ps1' | iex"
```

This fallback installer detects suitable Python and Git installations, installs either when necessary,
installs and configures pipx, installs Interly, verifies the command, and launches it. Node.js is
not required. It remains separate from the standalone WinGet distribution.

On first launch, Interly asks for a [Groq API key](https://console.groq.com/keys). Input is
hidden, validated before saving, and stored under the current Windows user's application-data
directory. Type `groq` at any Interly `You:` prompt to securely validate and replace the saved
key without restarting the session.

Upgrade later with:

```text
update
```

Run `update` at any Interly `You:` prompt. Standalone installations try WinGet first and fall
back to a SHA-256-verified GitHub Release installer while catalogue publication is pending.
Development installations upgrade through pipx. Restart Interly after a successful update.

## Current capabilities

- Groq-powered terminal conversation with in-session memory
- Persistent local memory for approved facts and preferences
- Memory inspection, export, and clear controls from the chat loop
- Reusable named workflows and workflow listing support
- Repository inspection and bounded repository command execution
- Beta make-memory command for saving simple text snippets to a local interly-memory.txt file
- Approval before every local action
- Open applications registered with Windows or explicit executable commands resolved by Windows
- Discover, close, or forcibly terminate exact processes by PID
- Read-only system commands for processes, system information, networking, users, routes,
  adapters, Wi-Fi, and disks
- Permission-gated Windows logout
- Direct public-web search and webpage text extraction
- Deduplicated multi-source research with transparent source-quality heuristics
- Session-level approval for direct web access
- Global `Esc` emergency stop for cancelling the current request
- Guarded lock, sleep, restart, and shutdown actions
- CPU, memory, disk, network, GPU, temperature, and battery reporting where Windows exposes it
- Installed-application reporting with registry-provided size estimates
- Isolated Playwright browser fallback with inspected controls, approved clicking and typing,
  screenshots, tabs, scrolling, and navigation
- Automatic isolated-browser cleanup after every browser-assisted request
- Guarded file search, bounded text reads, exact text edits, comparison, creation, copying,
  moving, renaming, and folder creation
- Approved direct-file downloads with public-URL validation, a 1 GB limit, overwrite protection,
  temporary-file cleanup, final content type, byte count, and SHA-256 reporting
- Blocking of private/local web addresses, oversized pages, unsupported downloads, invented
  application IDs, and critical Windows process termination

## Approval controls

At an ordinary approval prompt:

- `y` approves that single action.
- Enter or `n` denies it.
- Web prompts also offer `a`, which allows direct web access for the current Interly session.

Sensitive local-read prompts use a different meaning:

- `Y` runs the command and keeps its raw output only in the terminal.
- `N` denies the command.
- `A` runs the command and explicitly allows that command's output to be sent to Groq.

Sensitive `A` approval applies to one command only; it is never remembered for the session.

Application launches, process termination, and logout always require individual approval.

System reports default to local-only. Raw process lists, application matches, IP and Wi-Fi
configuration, users, routes, performance metrics, and installed-application reports are printed
in the terminal. With `Y`, Interly sends Groq only a short completion status. With `A`, the user
explicitly authorizes that one output to be included in the Groq conversation. For a local-only
app or process lookup, the user must type the exact displayed name and ID or PID before Interly
can continue.

## Recent user-owned progress

- [x] Persistent memory storage for approved facts and preferences
- [x] Memory inspect/export/clear controls available through the chat loop
- [x] Reusable named workflows and workflow listing support
- [x] Repository inspection and bounded repository command execution for developer workflows
- Beta make-memory command idea for saving simple local notes to interly-memory.txt

## Important limitations

Interly is alpha software. Model responses can be wrong, and read-only system output may still
contain private information. Review every proposed action. Forced process termination can lose
unsaved work. Web searches and selected page text are sent to external services and Groq.

Personal-browser access, file deletion, webpage video extraction, streaming-platform downloads,
document parsing, uploads, logins, purchases, and messaging are not implemented. Direct downloads
currently require a public URL that returns the file itself. The emergency stop prevents additional
actions, but an operating-system call that has already completed cannot be reversed.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
pytest -p no:cacheprovider
ruff check src tests
```

## License

MIT
