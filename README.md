# Interly

Interly is an experimental, permission-aware Windows computer agent powered by Groq. It can
reason about a request, propose a local or web action, show exactly what it wants to do, and
wait for approval before executing it.

Development follows the checked 100-item plan in [ROADMAP.md](ROADMAP.md).

## Install with pipx

Install [Python 3.11 or newer](https://www.python.org/downloads/) and
[pipx](https://pipx.pypa.io/stable/installation/), then run:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

Open a new PowerShell window, then run:

```powershell
pipx install git+https://github.com/interlinkglobal/Interly.git
interlink
```

On first launch, Interly asks for a [Groq API key](https://console.groq.com/keys). Input is
hidden, validated before saving, and stored under the current Windows user's application-data
directory. Type `groq` at any Interly `You:` prompt to securely validate and replace the saved
key without restarting the session.

Upgrade later with:

```powershell
pipx upgrade interly
```

## Current capabilities

- Groq-powered terminal conversation with in-session memory
- Approval before every local action
- Open any application registered with Windows
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
- Isolated Playwright browser fallback for rendered pages, tabs, scrolling, and navigation
- Automatic isolated-browser cleanup after every browser-assisted request
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

## Important limitations

Interly is alpha software. Model responses can be wrong, and read-only system output may still
contain private information. Review every proposed action. Forced process termination can lose
unsaved work. Web searches and selected page text are sent to external services and Groq.

Browser clicking and typing, personal-browser access, file modification, downloads, uploads,
logins, purchases, and messaging are not implemented. The emergency stop prevents additional
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
