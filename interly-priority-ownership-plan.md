# Interly Remaining Roadmap — Priority & Ownership Plan

> Working reference for the remaining ❌ Interly roadmap items.
>
> This document defines **implementation priority**, **ownership**, and the **meeting point** between parallel workstreams.  
> Completed ✅ roadmap items are intentionally excluded.

## Working Agreement

- **ChatGPT** owns **Priority 1 — Execution Governance** and **Priority 2 — Desktop Perception & Interaction**.
- **User** owns **Priority 4 — Persistent Memory & Reusable Work** and **Priority 5 — Developer Agent**.
- We **meet at Priority 3 — Documents & Safe Filesystem Completion** after the parallel work above is complete enough to converge.
- **Priorities 6–8 remain deferred** until after the Priority 3 convergence point unless we explicitly agree otherwise.
- Status in this document should be updated as work progresses so it remains the reference for **who is doing what**.

---

# Priority 1 — Execution Governance

**Owner: ChatGPT**  
**Status: Assigned**

Goal: establish the control architecture Interly should use before receiving substantially broader autonomy.

1. **#97 — Dry-run mode + configurable permission policies**
2. **#85 — Multi-step plan presentation**
3. **#86 — Grouped/scoped plan approvals**
4. **#96 — Persistent privacy-aware action audit logs**

### Intended flow

`request → plan → dry run / policy evaluation → scoped approval → execution → audit record`

### Completion outcome

Interly can present a larger operation as a governed plan rather than a chain of unrelated approval prompts, with policy evaluation and a durable record of what was proposed and executed.

---

# Priority 2 — Desktop Perception & Interaction

**Owner: ChatGPT**  
**Status: Assigned**

Goal: turn Interly from a Windows command/tool agent into a desktop-capable computer agent.

1. **#71 — Desktop window manipulation**
   - list
   - focus
   - minimise
   - maximise
   - move
   - resize
   - restore
2. **#73 — Full-screen and selected-window screenshots**
3. **#74 — OCR**
4. **#75 — Visible desktop-control identification**
5. **#76 — Guarded generic mouse control**
6. **#77 — Guarded generic keyboard control**
7. **#72 — Clipboard access with separate read/write approvals**

### Intended flow

`windows → screenshots → understanding → control identification → mouse / keyboard → clipboard`

### Dependency rule

Generic mouse and keyboard control should not become the primary interaction path before Interly can identify what is on screen and where the intended target is.

### Completion outcome

Interly can inspect the visible Windows desktop, understand relevant on-screen content and controls, and interact with them through permission-gated input.

---

# Priority 3 — Documents & Safe Filesystem Completion

**Owner: Joint / Convergence Point**  
**Status: Waiting for both parallel workstreams**

This is where **ChatGPT and the User regroup** after working independently on Priorities 1–2 and 4–5.

Goal: complete Interly's existing filesystem layer and expand it from text-file access into structured document work.

1. **#67 — Structured PDF, Word, Excel and PowerPoint understanding**
2. **#66 — File deletion through the Windows Recycle Bin**
3. **#70 — Malware scanning and quarantine checks for downloads**

### Intended file flow

`find → read → understand → compare → create/edit → move/copy → delete safely`

### Intended download flow

`download → inspect → scan → accept / quarantine`

### Completion outcome

Interly can work with common structured documents, complete ordinary filesystem management safely, and treat downloaded files as a security-sensitive pipeline.

---

# Priority 4 — Persistent Memory & Reusable Work

**Owner: User**  
**Status: Assigned**

Goal: move Interly from session-only context toward persistent continuity and reusable work.

1. [x] **#82 — Persistent conversation memory with explicit retention controls**
2. [x] **#84 — Memory inspect/export/delete controls**
3. [x] **#83 — Personal facts/preferences memory with explicit user approval**
4. [x] **#87 — Reusable named workflows**
5. [ ] **#88 — Scheduled tasks, reminders and monitors**

### Intended flow

`persistent storage → user control → approved facts/preferences → reusable workflows → recurrence`

### Dependency rule

Memory management and deletion controls should exist alongside persistent memory before expanding into personal facts/preferences.

### Completion outcome

Interly can retain approved context across sessions, let the user inspect and control that retained information, and convert repeated work into reusable or scheduled workflows.

---

# Priority 5 — Developer Agent

**Owner: User**  
**Status: Assigned**

Goal: turn Interly's existing machine and file capabilities into a coherent software-development workflow.

1. [x] **#89 — Git repository operations**
2. [x] **#90 — Tests, linters, builds and development servers as agent workflows**
3. [ ] **#91 — Structured log monitoring with cancellation and timeouts**
4. [ ] **#98 — Token, cost, latency and request-count reporting**

### Intended flow

`repository → inspect/change → build/test/run → monitor logs → measure execution`

### Completion outcome

Interly can work inside a development repository, run and supervise development commands, observe structured logs, and expose the operational cost/performance of agent work.

---

# Priority 6 — Release & Supply-Chain Security

**Owner: Deferred / Unassigned**  
**Status: After Priority 3 convergence**

Goal: harden the distribution path for a machine-level Windows agent.

1. **#99 — Complete GitHub Actions security coverage**
2. **#100 — Signed Windows releases with a trusted update path**

### Intended flow

`source → tests/lint → security checks → package → sign → release → verified update`

---

# Priority 7 — Human & OS Interface Controls

**Owner: Deferred / Unassigned**  
**Status: After Priority 3 convergence**

Goal: add useful human-facing and environmental controls once the major architecture is stable.

1. **#78 — Volume and mute control**
2. **#79 — Brightness control**
3. **#80 — Speech input**
4. **#81 — Speech output and optional wake phrase**

### Intended flow

`speech input → Interly → speech output`

Volume and brightness remain independent OS controls within the same lower-priority interface layer.

---

# Priority 8 — 1.0 External Security Validation

**Owner: Deferred / External**  
**Status: Last major gate before stable 1.0**

1. **#101 — External security review and threat-model audit**

This comes after the major capability and security architecture stabilises so the external review evaluates the actual 1.0 candidate rather than a moving target.

---

# Parallel Work Map

| Priority | Workstream | Owner | Current State |
|---|---|---|---|
| 1 | Execution Governance | **ChatGPT** | Assigned |
| 2 | Desktop Perception & Interaction | **ChatGPT** | Assigned |
| 3 | Documents & Safe Filesystem Completion | **Joint** | Convergence point |
| 4 | Persistent Memory & Reusable Work | **User** | Assigned |
| 5 | Developer Agent | **User** | Assigned |
| 6 | Release & Supply-Chain Security | Deferred | After convergence |
| 7 | Human & OS Interface Controls | Deferred | After convergence |
| 8 | External Security Validation | External / Deferred | Final gate |

## Current execution pattern

**ChatGPT:** `Priority 1 → Priority 2`  
**User:** `Priority 4 → Priority 5`

Then:

**Both:** `→ Priority 3`

After Priority 3, ownership and order for Priorities 6–8 can be reassigned based on the state of the system.

---

# Reference Rule

When we say:

- **“my work”** in this plan, it refers to the User-owned priorities **4 and 5**.
- **“your work”** in this plan, it refers to ChatGPT-owned priorities **1 and 2**.
- **“meet at three”** means both parallel streams converge on **Priority 3 — Documents & Safe Filesystem Completion**.
- Priorities **6–8 are not active assignments yet**.

