Write-Host "=== WORKTREES ==="
git worktree list

Write-Host "`n=== AGENT BRANCHES ==="
git branch --list "agent/*"

Write-Host "`n=== MAIN STATUS ==="
git status --short

Write-Host "`n=== ACTIVE TASK STATES ==="

Get-ChildItem ".\_agent_worktrees\task-*.json" -ErrorAction SilentlyContinue |
    Select-Object Name
