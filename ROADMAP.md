# Interly: 100-Item Roadmap

This is the working roadmap for Interly. Checked items are implemented and verified. Unchecked
items remain future work. Safety and reliability work should precede higher-risk capabilities.

## 1. Core agent foundation

1. [✅] Create the Python project and isolated development environment.
2. [✅] Implement a terminal conversation loop.
3. [✅] Maintain conversation history for the current session.
4. [✅] Connect the agent to Groq.
5. [✅] Separate the model, chat loop, configuration, and tools.
6. [✅] Add clean handling for empty input, API errors, `Ctrl+C`, and exit commands.
7. [✅] Add a one-word `interlink` terminal command.
8. [✅] Add secure first-run Groq API-key setup.
9. [✅] Store configuration in the current Windows user's application-data directory.
10. [✅] Package Interly for installation with `pipx`.

## 2. Permissions and safety

11. [✅] Require explicit approval before every local tool execution.
12. [✅] Show the proposed action and reason before approval.
13. [✅] Display stronger warnings for logout and forced process termination.
14. [✅] Deny actions unless the user explicitly enters an approval response.
15. [✅] Support session-level approval for direct web access.
16. [✅] Block termination of critical Windows processes.
17. [✅] Validate application IDs against the Windows application catalog.
18. [✅] Restrict system-information commands to a fixed read-only allowlist.
19. [✅] Limit web searches, webpage reads, and model/tool rounds per request.
20. [✅] Add `Esc` as the global emergency-stop keyboard shortcut.

## 3. Existing Windows capabilities

21. [✅] Read the current local date, time, and timezone.
22. [✅] Discover applications registered with Windows.
23. [✅] Open a selected registered application after approval.
24. [✅] Resolve ambiguous application names before launching.
25. [✅] Count and list running processes.
26. [✅] Find processes by name or visible window title.
27. [✅] Close an exact process by PID.
28. [✅] Force-kill an exact process by PID with a warning.
29. [✅] Sign the current user out of Windows with a warning.
30. [✅] Lock, sleep, restart, and shut down Windows with distinct warnings.

## 4. Read-only system commands

31. [✅] Read general Windows system information.
32. [✅] Read full IP configuration.
33. [✅] Read Wi-Fi information.
34. [✅] List local user accounts.
35. [✅] Read the current Windows identity and hostname.
36. [✅] List network adapters.
37. [✅] Read the routing table.
38. [✅] Read disk and volume capacity information.
39. [✅] Add CPU, memory, disk-I/O, GPU, temperature, and battery metrics.
40. [✅] Add installed-application and application-size reporting.

## 5. Direct web access

41. [✅] Search the public web without opening a browser.
42. [✅] Return multiple search results from one query.
43. [✅] Read a selected public webpage.
44. [✅] Extract readable text while removing scripts and styles.
45. [✅] Include source URLs in web-assisted answers.
46. [✅] Block localhost, private-network, credential-bearing, and special-purpose URLs.
47. [✅] Validate every redirect and limit redirect depth.
48. [✅] Enforce response-size, page-text, timeout, and content-type limits.
49. [✅] Treat webpage content as untrusted data rather than instructions.
50. [✅] Add multi-source research reports with deduplication and source-quality scoring.

## 6. Isolated browser automation

51. [✅] Install Playwright and a dedicated isolated Chromium profile.
52. [✅] Open approved URLs in the isolated browser.
53. [✅] Read JavaScript-rendered page content.
54. [✅] List, open, switch, and close browser tabs.
55. [✅] Scroll pages and navigate backward or forward.
56. [✅] Inspect links, buttons, forms, and accessible page controls.
57. [✅] Click a selected control after showing an exact preview.
58. [✅] Type approved text into a selected field.
59. [✅] Take browser screenshots for visual verification.
60. [✅] Fall back to the isolated browser only when direct HTTP fails.

## 7. Files, documents, and downloads

61. [✅] Search for files by name, type, date, or content.
62. [✅] Read approved text and source-code files.
63. [✅] Preview and create new text files.
64. [✅] Preview and apply edits to existing files.
65. [✅] Create, copy, move, and rename files or folders.
66. [ ] Send deleted items to the Windows Recycle Bin.
67. [ ] Summarize PDF, Word, spreadsheet, and presentation files.
68. [ ] Compare two files and explain their differences.
69. [✅] Download direct public file URLs with type, size, hash, and destination approval.
70. [ ] Add malware scanning and quarantine checks for downloads.

## 8. Desktop interaction and media

71. [ ] List, focus, minimize, maximize, move, and resize windows.
72. [ ] Read and write the clipboard with separate approvals.
73. [ ] Take full-screen or selected-window screenshots.
74. [ ] Extract visible text from screenshots with OCR.
75. [ ] Identify visible controls without automatically clicking them.
76. [ ] Add guarded mouse and keyboard control.
77. [ ] Adjust system volume and mute state.
78. [ ] Adjust display brightness where supported.
79. [ ] Add push-to-talk speech input.
80. [ ] Add spoken responses and an optional wake phrase.

## 9. Workflows, memory, and developer tools

81. [ ] Save conversation history with explicit retention controls.
82. [ ] Remember user-approved preferences and named facts.
83. [ ] Add commands to inspect, export, and erase all memory.
84. [ ] Show a plan before beginning a multi-step task.
85. [ ] Support grouped, scoped approvals for a displayed plan.
86. [ ] Save and rerun named workflows.
87. [ ] Add scheduled workflows, reminders, and monitors.
88. [ ] Add Git repository inspection and status tools.
89. [ ] Run approved tests, linters, builds, and development servers.
90. [ ] Add structured log monitoring with cancellation and timeouts.

## 10. Quality, publishing, and long-term reliability

91. [✅] Add automated tests for agent, tools, configuration, and web safety.
92. [✅] Add Ruff code-quality checks.
93. [✅] Publish the source in the public `interlinkglobal/Interly` GitHub repository.
94. [✅] Add installation, capability, permission, limitation, and license documentation.
95. [ ] Add a persistent, privacy-aware audit log for every proposed and executed action.
96. [ ] Add dry-run mode and configurable permission policies.
97. [ ] Add API token, latency, request, and estimated-cost reporting.
98. [ ] Add GitHub Actions for tests, linting, packaging, and security checks.
99. [ ] Publish signed versioned releases and a trusted update command.
100. [ ] Complete an external security review and threat-model audit before a stable 1.0 release.
