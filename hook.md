# Hooks for EmergentDB

Hooks are shell commands that run automatically at specific points in Claude Code's lifecycle. Use them to enforce rules, automate tasks, and integrate EmergentDB into your workflow.

## Quick Start

The fastest way to create a hook is through the `/hooks` menu in Claude Code. Or add them directly to your settings file.

### Your First Hook: Desktop Notifications

Get notified when Claude finishes working instead of watching the terminal.

Type `/hooks` → select `Notification` → set matcher to `*` → add this command:

**macOS:**
```
osascript -e 'display notification "Claude Code needs your attention" with title "Claude Code"'
```

**Linux:**
```
notify-send 'Claude Code' 'Claude Code needs your attention'
```

Save to **User settings** (`~/.claude/settings.json`) to apply across all projects.

## Example: Auto-Format After Edits

Run Prettier on every file Claude edits:

Add to `.claude/settings.json` in your project:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ]
  }
}
```

## Example: Protect Sensitive Files

Block Claude from editing `.env`, `package-lock.json`, or `.git/`:

Create `.claude/hooks/protect-files.sh`:

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done
exit 0
```

Make it executable and register it:

```bash
chmod +x .claude/hooks/protect-files.sh
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh"
          }
        ]
      }
    ]
  }
}
```

## Example: Re-inject Context After Compaction

When Claude's context fills up and compacts, important details can get lost. Re-inject them:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: use EmergentDB for all vector operations. API key is in EMERGENTDB_API_KEY env var. Always use batch_insert for multiple vectors.'"
          }
        ]
      }
    ]
  }
}
```

## Example: Log All Bash Commands

Track every command Claude runs for audit purposes:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' >> ~/.claude/command-log.txt"
          }
        ]
      }
    ]
  }
}
```

## Example: Validate Before Stopping

Use a prompt-based hook to check if Claude actually completed the task before stopping:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains to be done\"}."
          }
        ]
      }
    ]
  }
}
```

## Hook Reference

### Events

| Event | When it fires |
|-------|---------------|
| `SessionStart` | Session begins, resumes, or context compacts |
| `UserPromptSubmit` | User submits a prompt, before Claude processes it |
| `PreToolUse` | Before a tool executes (can block it) |
| `PostToolUse` | After a tool succeeds |
| `PostToolUseFailure` | After a tool fails |
| `Notification` | Claude needs your attention |
| `Stop` | Claude finishes responding |
| `SubagentStart` | A subagent spawns |
| `SubagentStop` | A subagent finishes |
| `ConfigChange` | A config file changes during the session |
| `PreCompact` | Before context compaction |
| `SessionEnd` | Session terminates |

### Hook Types

| Type | Description |
|------|-------------|
| `command` | Run a shell command |
| `prompt` | Ask a Claude model for a yes/no decision (single-turn) |
| `agent` | Spawn a subagent that can use tools to verify conditions (multi-turn) |

### Matchers

Matchers filter when a hook fires. Without one, it fires on every event.

| Event | Matches on | Examples |
|-------|-----------|----------|
| `PreToolUse`, `PostToolUse` | Tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| `SessionStart` | How session started | `startup`, `resume`, `compact` |
| `Notification` | Notification type | `permission_prompt`, `idle_prompt` |
| `SessionEnd` | Exit reason | `clear`, `logout` |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Allow the action. Stdout is added to context for `SessionStart` and `UserPromptSubmit`. |
| `2` | Block the action. Stderr is sent to Claude as feedback. |
| Other | Allow the action. Stderr is logged but not shown. |

### Input/Output

Hooks receive JSON on stdin with event-specific data:

```json
{
  "session_id": "abc123",
  "cwd": "/Users/you/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test"
  }
}
```

For structured control, exit 0 and print JSON to stdout:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Use bun instead of npm"
  }
}
```

### Where to Put Hooks

| Location | Scope |
|----------|-------|
| `~/.claude/settings.json` | All your projects (personal) |
| `.claude/settings.json` | This project (shareable via git) |
| `.claude/settings.local.json` | This project (gitignored) |

## Tips

- Use `/hooks` in Claude Code to create and manage hooks interactively.
- Toggle verbose mode with `Ctrl+O` to see hook output in the transcript.
- `PreToolUse` hooks can block actions. `PostToolUse` hooks cannot undo them.
- All matching hooks run in parallel. Identical commands are deduplicated.
- Hook timeout defaults to 10 minutes. Set `"timeout"` (in seconds) per hook to override.
- Install `jq` for JSON parsing in hook scripts: `brew install jq` (macOS) or `apt-get install jq` (Linux).
- Wrap `echo` statements in your shell profile with `if [[ $- == *i* ]]` to avoid polluting hook JSON output.
