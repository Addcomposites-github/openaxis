# Catchup

Quickly get up to speed on recent changes in the codebase.

## Process

1. **Check git status**
   ```bash
   git status
   git log --oneline -10
   ```

2. **Review recent changes**
   ```bash
   git diff HEAD~5 --stat
   ```

3. **Read modified files**
   For each modified file, understand what changed and why.

4. **Check for TODO/FIXME**
   ```bash
   grep -r "TODO\|FIXME" src/ --include="*.py"
   ```

5. **Review open issues**
   Check the project board or issues for current priorities.

6. **Summarize context**
   Provide a brief summary of:
   - Current branch and its purpose
   - Recent changes made
   - Any pending work or known issues
   - Next steps based on ROADMAP.md

## Output

```markdown
## Session Context

**Branch:** feature/xyz
**Recent commits:**
- abc123: Added X feature
- def456: Fixed Y bug

**Modified files:**
- src/core/config.py (configuration changes)
- tests/test_config.py (new tests)

**Current focus:** [Based on branch name and recent commits]

**Next steps:** [Based on ROADMAP.md phase]
```
