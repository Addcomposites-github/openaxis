# Code Review

Perform a comprehensive code review of recent changes.

## Process

1. **Identify changes**
   ```bash
   git diff --name-only HEAD~1  # or specific commit/branch
   git diff HEAD~1  # full diff
   ```

2. **Review each file for:**

   **Code Quality**
   - [ ] Type hints on all functions
   - [ ] Docstrings on public functions/classes
   - [ ] No magic numbers (use constants)
   - [ ] Functions under 50 lines
   - [ ] Clear naming conventions

   **Architecture**
   - [ ] Follows existing patterns in codebase
   - [ ] Proper separation of concerns
   - [ ] No circular imports
   - [ ] Uses COMPAS for geometry (not raw numpy)

   **Error Handling**
   - [ ] Appropriate exception types
   - [ ] Meaningful error messages
   - [ ] No bare except clauses

   **Testing**
   - [ ] New code has tests
   - [ ] Tests cover edge cases
   - [ ] Tests are in correct location

   **Security**
   - [ ] No hardcoded credentials
   - [ ] Input validation where needed
   - [ ] Safe file handling

3. **Run automated checks**
   ```bash
   # Linting
   flake8 src/ tests/ --max-line-length=100

   # Type checking
   mypy src/ --ignore-missing-imports

   # Tests
   pytest tests/unit -v
   ```

4. **Provide feedback**
   - List issues found with file:line references
   - Suggest specific fixes
   - Note any good patterns to reinforce

## Output Format

```markdown
## Code Review Summary

### Files Reviewed
- file1.py: ✓ Approved / ⚠ Issues found
- file2.py: ✓ Approved / ⚠ Issues found

### Issues Found
1. **file1.py:42** - Missing type hint on `process_data` function
2. **file2.py:15** - Magic number should be a named constant

### Suggestions
- Consider extracting X into a separate function
- Could use dataclass instead of dict for Y

### Positive Notes
- Good use of factory pattern in Z
- Clean error handling in W
```
