# Interly: 101-Item Roadmap

This is the verified working roadmap for Interly.

Status rule:
- ✅ = the complete item is implemented and verified.
- ❌ = the item is not fully complete. Partial implementation still counts as ❌.

Current verified status: **88/101 complete**.

## 1. Core agent foundation

1. ✅ Create the Python project and isolated development environment.
2. ✅ Implement a terminal conversation loop.
3. ✅ Maintain conversation history for the current session.
4. ✅ Connect the agent to Groq.
5. ✅ Separate the model, chat loop, configuration, and tools.
6. ✅ Add clean handling for empty input, API errors, `Ctrl+C`, and exit commands.
7. ✅ Add the one-word `interly` terminal command, retaining `interlink` as a compatibility alias.
8. ✅ Add secure first-run Groq API-key setup.
9. ✅ Store configuration in the current Windows user's application-data directory.
10. ✅ Package Interly for installation with `pipx` as the development/fallback route.

## 2. Permissions and safety

11. ✅ Require explicit approval before every local tool execution during normal approval mode.
12. ✅ Show the proposed action and reason before approval.
13. ✅ Display stronger warnings for logout, power actions, and forced process termination.
14. ✅ Deny actions unless the user explicitly enters an approval response during normal approval mode.
15. ✅ Support session-level approval for direct web access.
16. ✅ Block termination of critical Windows processes.
17. ✅ Validate application IDs against the Windows application catalogue.
18. ✅ Restrict system-information commands to a fixed read-only allowlist.
19. ✅ Limit web searches, webpage reads, browser reads, and model/tool rounds per request.
20. ✅ Add `Esc` as the global emergency-stop keyboard shortcut.

## 3. Existing Windows capabilities

21. ✅ Read the current local date, time, and timezone.
22. ✅ Discover applications registered with Windows.
23. ✅ Open a selected registered application or resolved executable command after approval.
24. ✅ Resolve ambiguous application names before launching.
25. ✅ Count and list running processes.
26. ✅ Find processes by name or visible window title.
27. ✅ Close an exact process by PID.
28. ✅ Force-kill an exact process by PID with a warning.
29. ✅ Sign the current user out of Windows with a warning.
30. ✅ Lock, sleep, restart, and shut down Windows with distinct warnings.

## 4. Read-only system commands

31. ✅ Read general Windows system information.
32. ✅ Read full IP configuration.
33. ✅ Read Wi-Fi information.
34. ✅ List local user accounts.
35. ✅ Read the current Windows identity and hostname.
36. ✅ List network adapters.
37. ✅ Read the routing table.
38. ✅ Read disk and volume capacity information.
39. ✅ Add CPU, memory, disk-I/O, GPU, temperature, and battery metrics.
40. ✅ Add installed-application and application-size reporting.

## 5. Direct web access

41. ✅ Search the public web without opening a browser.
42. ✅ Return multiple search results from one query.
43. ✅ Read a selected public webpage.
44. ✅ Extract readable text while removing scripts and styles.
45. ✅ Include source URLs in web-assisted answers.
46. ✅ Block localhost, private-network, credential-bearing, and special-purpose URLs.
47. ✅ Validate every redirect and limit redirect depth.
48. ✅ Enforce response-size, page-text, timeout, and content-type limits.
49. ✅ Treat webpage content as untrusted data rather than instructions.
50. ✅ Add multi-source research reports with deduplication and source-quality scoring.

## 6. Isolated browser automation

51. ✅ Add Playwright with a dedicated isolated Chromium-based browser profile.
52. ✅ Open approved public URLs in the isolated browser.
53. ✅ Read JavaScript-rendered page content.
54. ✅ List, open, switch, and close browser tabs.
55. ✅ Scroll pages and navigate backward or forward.
56. ✅ Inspect links, buttons, forms, and accessible page controls.
57. ✅ Click a selected control after showing an exact preview.
58. ✅ Type approved text into a selected field.
59. ✅ Take browser screenshots for visual verification.
60. ✅ Use the isolated browser when direct HTTP is insufficient or when the user explicitly requests it.

## 7. Files, documents, and downloads

61. ✅ Search for files by name, type, date, or content.
62. ✅ Read approved text and source-code files.
63. ✅ Preview and create new text files.
64. ✅ Preview and apply exact text edits to existing files.
65. ✅ Create, copy, move, and rename files or folders.
66. ❌ Add file deletion with Windows Recycle Bin support.
67. ❌ Add structured PDF, Word, Excel, and PowerPoint understanding.
68. ✅ Compare two approved text files and return their differences.
69. ✅ Download direct public file URLs with type, size, hash, and destination approval.
70. ❌ Add malware scanning and quarantine checks for downloads.

## 8. Desktop interaction and media

71. ✅ Add desktop window manipulation: list, focus, minimise, maximise, move, resize, and restore windows.
72. ✅ Add clipboard access with separately approved reads and writes.
73. ✅ Add full-screen and desktop screenshots, including selected-window capture.
74. ✅ Add OCR for extracting visible text from screenshots and desktop captures.
75. ✅ Identify visible desktop controls without automatically activating them.
76. ✅ Add guarded generic mouse control.
77. ✅ Add guarded generic keyboard control.
78. ❌ Add system volume and mute control.
79. ❌ Add display brightness control where supported.
80. ❌ Add speech input, including push-to-talk.
81. ❌ Add speech output and an optional wake phrase.

## 9. Workflows, memory, and developer tools

82. ✅ Add persistent conversation memory with explicit retention controls.
83. ✅ Add personal facts and preferences memory with explicit user approval.
84. ✅ Add memory management: inspect, export, and delete retained memory.
85. ✅ Add multi-step plan presentation before beginning complex tasks.
86. ✅ Add grouped and scoped approvals for a displayed plan.
87. ✅ Add reusable workflows that can be saved and rerun by name.
88. ❌ Add scheduled tasks, reminders, and monitors.
89. ✅ Add Git repository operations, including inspection and status tools.
90. ✅ Run approved development tests, linters, builds, and development servers as agent workflows.
91. ❌ Add structured log monitoring with cancellation and timeouts.

## 10. Quality, publishing, and long-term reliability

92. ✅ Add automated tests for agent, tools, configuration, web safety, browser behaviour, files, installer, distribution, and updater behaviour.
93. ✅ Add Ruff code-quality checks.
94. ✅ Publish the source in the public `interlinkglobal/interly` GitHub repository.
95. ✅ Add installation, capability, permission, limitation, and licence documentation.
96. ✅ Add persistent, privacy-aware action audit logs for every proposed and executed action.
97. ✅ Add dry-run mode and configurable permission policies.
98. ❌ Add API token usage, latency, request-count, and estimated-cost reporting.
99. ❌ Complete GitHub Actions coverage for tests, linting, packaging, and dedicated security checks. Tests, linting, and packaging exist; dedicated security checks do not.
100. ❌ Publish signed versioned releases with a trusted update path. Versioned releases and SHA-256-verified updating exist; Windows release artifacts are not yet code-signed.
101. ❌ Complete an external security review and threat-model audit before a stable 1.0 release.
