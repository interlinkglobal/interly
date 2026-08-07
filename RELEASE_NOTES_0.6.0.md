# Interly 0.6.0

Interly 0.6.0 is the first release where the agent can inspect and interact with the visible Windows desktop while using a stronger host-side governance layer.

## Highlights

### Execution governance
- Add session dry-run mode with `dry-run`, `dry-run on`, and `dry-run off`.
- Add persistent per-tool permission policies with `prompt`, `allow`, and `deny` modes.
- Add multi-step plan presentation before complex work.
- Add one-request scoped plan approval limited to the tools and scopes shown in the plan.
- Keep process termination, logout, restart, shutdown, and other destructive Windows actions individually confirmed.
- Add persistent privacy-aware JSONL action audit logs with sensitive text and URL secrets redacted.

### Desktop perception and interaction
- List visible top-level Windows windows with exact handles, PIDs, titles, and rectangles.
- Focus, minimise, maximise, restore, move, and resize exact windows after revalidation.
- Capture the full virtual desktop or a selected window to PNG.
- Add bundled OCR with detected text and bounding boxes.
- Inspect visible foreground controls through Windows UI Automation without activating them.
- Add guarded generic mouse movement, clicking, double-clicking, and bounded scrolling.
- Add guarded generic keyboard typing and bounded key combinations.
- Add separately approved Windows clipboard reads and writes.

### Memory and reusable work
- Add persistent conversation memory with explicit retention controls.
- Add approved personal facts and preferences memory.
- Add memory inspection, export, and clear controls.
- Add reusable named workflows.
- Add the beta `make-memory` command for simple local note capture.

### Developer workflows
- Add repository inspection.
- Add bounded repository command execution for tests, linters, builds, and development-server workflows.

### Distribution and updates
- Bump the package, CLI, standalone executable, installer, and WinGet manifest version to 0.6.0.
- Include the desktop OCR/UI Automation dependencies in normal developer requirements.
- Make the fallback pipx installer install from `main` instead of the old roadmap branch.
- Make pipx update checks follow `main` as well.
- Keep `interly` as the canonical command while retaining `interlink` as a compatibility alias.
- Generate 0.6.0 Windows executable, installer, and WinGet manifest artifacts through the existing Windows distribution workflow.

## Verified roadmap state

Interly is currently at **88/101 verified roadmap items**.

## Still not included

- Recycle Bin file deletion
- Structured PDF, Word, Excel, and PowerPoint understanding
- Malware scanning and quarantine for downloads
- Scheduled tasks, reminders, and monitors
- Structured log monitoring
- Token, cost, latency, and request-count reporting
- Volume and brightness controls
- Speech input and output
- Signed Windows release artifacts
- External 1.0 security review

## Release procedure

After the 0.6.0 release-prep PR is merged and the site deployment is complete:

1. Create tag `v0.6.0` on the current `main` commit.
2. The Windows distribution workflow will build and publish:
   - `interly.exe`
   - `interlink.exe`
   - `InterlySetup-x64.exe`
   - `Interly-0.6.0-winget-manifests.zip`
3. Confirm the GitHub Release contains the installer SHA-256 digest.
4. Install or run `update` from an existing standalone Interly installation and verify `interly --version` reports `Interly 0.6.0`.
