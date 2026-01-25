# Implement Feature

Implement a new feature following OpenAxis development standards.

## Process

1. **Understand the requirement**
   - Read the feature description: $ARGUMENTS
   - Check if related issues exist in the codebase
   - Identify which module(s) this affects

2. **Research existing code**
   - Search for similar patterns in the codebase
   - Check relevant documentation in `docs/`
   - Review any related tests

3. **Plan the implementation**
   - List files that need to be created or modified
   - Identify any new dependencies needed
   - Consider edge cases and error handling

4. **Implement with tests**
   - Write tests FIRST (TDD approach)
   - Implement the feature
   - Ensure type hints are added
   - Add docstrings to public functions/classes

5. **Validate**
   - Run `pytest tests/` to ensure all tests pass
   - Run `python scripts/lint.py` to check code style
   - Run `python scripts/typecheck.py` for type checking

6. **Document**
   - Update relevant documentation if needed
   - Add to CHANGELOG.md if significant

## Code Standards

- Use type hints for all function parameters and returns
- Follow existing patterns in the codebase
- Keep functions focused and under 50 lines when possible
- Use COMPAS data structures for geometry (not raw numpy)
- Async/await for any I/O or hardware operations

## Output

Provide a summary of:
- Files created/modified
- Tests added
- Any documentation updates
- Remaining TODO items if any
