# Chores Project

## Environment

- Use `py` to run Python scripts on this machine (`python` is not on PATH).
- LibreOffice is installed at `C:\Program Files\LibreOffice\program\soffice.exe` (installed via choco). Use this path explicitly; `soffice` is not on PATH.
- `pymupdf` (fitz 1.27.2) is installed — use `import fitz` for PDF→PNG conversion. Do NOT add it to requirements.txt (already present).
- No `ANTHROPIC_API_KEY` is set. Use the Claude Code CLI (`claude`) for any AI calls — it authenticates via the subscription OAuth token.

## Calling Claude from Python scripts

Use `claude -p` with `--allowedTools Read` to analyze images/files without broad permission grants. Claude uses its built-in Read tool to view image files. Use `--output-format json` to get a structured result envelope:

```python
result = subprocess.run(
    ["claude", "-p", f"Read the image at {image_path} and analyze it. {prompt}",
     "--allowedTools", "Read", "--output-format", "json"],
    capture_output=True, text=True, encoding="utf-8", timeout=120,
    stdin=subprocess.DEVNULL
)
envelope = json.loads(result.stdout)
response_text = envelope["result"]  # may have ```json ... ``` fences, strip them
```

**Do NOT use `--input-format stream-json`** for sending user messages — that format only handles tool results in ongoing sessions, not new user messages. It will silently produce no output.

**Do NOT use PowerShell `echo` to pipe to subprocess stdin** — PS 5.1 adds a UTF-8 BOM that breaks JSON parsing. Write temp files with `[System.IO.File]::WriteAllText(path, content, [System.Text.UTF8Encoding]::new($false))` or use Python's subprocess directly.

## Git

- Never add `Co-Authored-By:` lines to commits.

## Working Preferences

- **Use `claude` CLI for AI calls.** Not the anthropic SDK, not other providers. `claude -p` with `--allowedTools` is the right tool.
- **Scope permissions — never use `--dangerously-skip-permissions`.** Use `--allowedTools <specific tool>` instead. Give the minimum needed.
- **Stop and surface after 2–3 failed attempts.** Don't grind through iteration after iteration silently. Say what's been tried, what's known, and ask before going further.
- **Tell before write.** Surface conclusions verbally first. Get confirmation before writing anything permanent (CLAUDE.md, memory, config files).
