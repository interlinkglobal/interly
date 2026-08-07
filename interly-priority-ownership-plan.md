# Interly Remaining Roadmap — Priority & Ownership Plan

> Working reference for the remaining ❌ Interly roadmap items.
>
> This document defines **implementation priority**, **ownership**, and the **meeting point** between parallel workstreams.

## Working Agreement

- **ChatGPT** owned **Priority 1 — Execution Governance** and **Priority 2 — Desktop Perception & Interaction**. That implementation pass is complete and verified by the Windows test/lint stage.
- **User** owned **Priority 4 — Persistent Memory & Reusable Work** and **Priority 5 — Developer Agent**. The completed portions are recorded below; remaining unchecked items stay open rather than being silently marked complete.
- We have reached **Priority 3 — Documents & Safe Filesystem Completion**, the joint convergence point.
- **Priorities 6–8 remain deferred** until after Priority 3 unless we explicitly agree otherwise.
- `ROADMAP.md` remains the strict ✅/❌ source of truth for feature completion.

---

# Priority 1 — Execution Governance

**Owner: ChatGPT**  
**Status: Complete ✅**

Goal: establish the control architecture Interly should use before receiving substantially broader autonomy.

1. [x] **#97 — Dry-run mode + configurable permission policies**
2. [x] **#85 — Multi-step plan presentation**
3. [x] **#86 — Grouped/scoped plan approvals**
4. [x] **#96 — Persistent privacy-aware action audit logs**

### Implemented flow

`request → plan → dry run / policy evaluation → scoped approval → execution → audit record`

### Completion outcome

Interly can present larger operations as governed plans instead of chains of unrelated prompts. Policies can prompt, allow, or deny by tool; dry-run prevents approved actions from executing; plan approval lasts only for the current request; destructive Windows actions still require individual confirmation; and proposed/executed actions are recorded in a privacy-aware JSONL audit log.

---

# Priority 2 — Desktop Perception & Interaction

**Owner: ChatGPT**  
**Status: Complete ✅**

Goal: turn Interly from a Windows command/tool agent into a desktop-capable computer agent.

1. [x] **#71 — Desktop window manipulation**
   - list
   - focus
   - minimise
   - maximise
   - move
   - resize
   - restore
2. [x] **#73 — Full-screen and selected-window screenshots**
3. [x] **#74 — OCR**
4. [x] **#75 — Visible desktop-control identification**
5. [x] **#76 — Guarded generic mouse control**
6. [x] **#77 — Guarded generic keyboard control**
7. [x] **#72 — Clipboard access with separate read/write approvals**

### Implemented flow

`windows → screenshots → understanding → control identification → mouse / keyboard → clipboard`

### Dependency rule

Generic mouse and keyboard control are downstream of desktop inspection. Interly is instructed to use exact window handles, returned control rectangles, or other known coordinates instead of inventing screen positions.

### Completion outcome

Interly can inspect the visible Windows desktop, capture it, extract text through bundled OCR, enumerate visible UI Automation controls, and perform permission-gated pointer, keyboard, window, and clipboard actions.

---

# Priority 3 — Documents & Safe Filesystem Completion

**Owner: Joint / Convergence Point**  
**Status: Active — structured documents complete; filesystem safety remains**

This is the current shared workstream after the parallel implementation passes.

Goal: complete Interly's existing filesystem layer and expand it from text-file access into structured document work.

1. [x] **#67 — Structured PDF, Word, Excel and PowerPoint understanding**
   - PDF pages, text, heuristic headings, tables and metadata
   - Word ordered headings, paragraphs, tables and metadata
   - Excel sheets, used ranges, headers, rows and formulas
   - PowerPoint slides, titles, text blocks, tables, speaker notes and metadata
   - read-only and local-only by default through the existing sensitive file-read approval path
   - verified in the packaged Windows executable
2. [ ] **#66 — File deletion through the Windows Recycle Bin**
3. [ ] **#70 — Malware scanning and quarantine checks for downloads**

### Current file flow

`find → read → understand ✅ → compare → create/edit → move/copy → delete safely`

### Remaining download flow

`download → inspect → scan → accept / quarantine`

### Current outcome

Interly can now understand common structured documents instead of treating them as opaque files. Priority 3 remains active until ordinary file deletion uses the Windows Recycle Bin and downloaded files have a malware scanning/quarantine path.

---

# Priority 4 — Persistent Memory & Reusable Work

**Owner: User**  
**Status: User checkpoint complete; one roadmap item remains open**

Goal: move Interly from session-only context toward persistent continuity and reusable work.

1. [x] **#82 — Persistent conversation memory with explicit retention controls**
2. [x] **#84 — Memory inspect/export/delete controls**
3. [x] **#83 — Personal facts/preferences memory with explicit user approval**
4. [x] **#87 — Reusable named workflows**
5. [x] **Beta idea — make-memory for simple queued local notes in interly-memory.txt**
6. [ ] **#88 — Scheduled tasks, reminders and monitors**

### Implemented flow so far

`persistent storage → user control → approved facts/preferences → reusable workflows`

### Remaining extension

`→ recurrence`

---

# Priority 5 — Developer Agent

**Owner: User**  
**Status: User checkpoint complete; two roadmap items remain open**

Goal: turn Interly's existing machine and file capabilities into a coherent software-development workflow.

1. [x] **#89 — Git repository operations**
2. [x] **#90 — Tests, linters, builds and development servers as agent workflows**
3. [ ] **#91 — Structured log monitoring with cancellation and timeouts**
4. [ ] **#98 — Token, cost, latency and request-count reporting**

### Implemented flow so far

`repository → inspect/change → build/test/run`

### Remaining extensions

`→ monitor logs → measure execution`

---

# Priority 6 — Release & Supply-Chain Security

**Owner: Deferred / Unassigned**  
**Status: After Priority 3 convergence**

1. [ ] **#99 — Complete GitHub Actions security coverage**
2. [ ] **#100 — Signed Windows releases with a trusted update path**

### Intended flow

`source → tests/lint → security checks → package → sign → release → verified update`

---

# Priority 7 — Human & OS Interface Controls

**Owner: Deferred / Unassigned**  
**Status: After Priority 3 convergence**

1. [ ] **#78 — Volume and mute control**
2. [ ] **#79 — Brightness control where supported**
3. [ ] **#80 — Speech input**
4. [ ] **#81 — Speech output and optional wake phrase**

### Intended flow

`speech input → Interly → speech output`

Volume and brightness remain independent OS controls within the same lower-priority interface layer.

---

# Priority 8 — 1.0 External Security Validation

**Owner: Deferred / External**  
**Status: Final gate**

1. [ ] **#101 — External security review and threat-model audit**

This comes after the major capability and security architecture stabilises so the external review evaluates the actual 1.0 candidate rather than a moving target.

---

# Parallel Work Map

| Priority | Workstream | Owner | Current State |
|---|---|---|---|
| 1 | Execution Governance | **ChatGPT** | Complete ✅ |
| 2 | Desktop Perception & Interaction | **ChatGPT** | Complete ✅ |
| 3 | Documents & Safe Filesystem Completion | **Joint** | **Active — #67 complete; #66/#70 open** |
| 4 | Persistent Memory & Reusable Work | **User** | Checkpoint complete; #88 open |
| 5 | Developer Agent | **User** | Checkpoint complete; #91 and #98 open |
| 6 | Release & Supply-Chain Security | Deferred | After Priority 3 |
| 7 | Human & OS Interface Controls | Deferred | After Priority 3 |
| 8 | External Security Validation | External / Deferred | Final gate |

## Current execution pattern

Completed parallel passes:

**ChatGPT:** `Priority 1 → Priority 2`  
**User:** `Priority 4 → Priority 5 checkpoint`

Current shared position:

**Both:** `→ Priority 3 (#67 ✅; #66/#70 next)`

---

# Reference Rule

When we say:

- **“my work”** in this plan refers to the User-owned Priority 4/5 implementation pass.
- **“your work”** refers to the ChatGPT-owned Priority 1/2 implementation pass.
- **“meet at three”** now means **Priority 3 is the active joint workstream**.
- Unchecked #88, #91, and #98 remain real roadmap work and have not been reclassified as complete.
- Priorities **6–8 are not active assignments yet**.
