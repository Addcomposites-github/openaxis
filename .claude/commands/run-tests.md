# Run Tests

Run the OpenAxis test suite with coverage.

## Arguments
Optional: specific test path or marker: $ARGUMENTS

## Steps

1. **Determine test scope**
   - If no arguments: run all unit tests
   - If path provided: run tests in that path
   - If marker provided (e.g., "integration"): run with that marker

2. **Run tests with coverage**
   ```bash
   # All unit tests
   pytest tests/unit -v --cov=src/openaxis --cov-report=term-missing

   # Specific path
   pytest tests/unit/core/test_config.py -v

   # With marker
   pytest tests/ -m "integration" -v
   ```

3. **Analyze failures**
   - If tests fail, read the error messages carefully
   - Check if it's a code issue or test issue
   - Fix the root cause, not the symptom

4. **Report results**
   - Summarize: X passed, Y failed, Z skipped
   - List any failing tests with brief reason
   - Note coverage percentage

## Common Issues

- **Import errors**: Check that the package is installed in editable mode
- **Missing fixtures**: Check conftest.py for required fixtures
- **Async issues**: Ensure pytest-asyncio is installed

## Output

Report:
- Test results summary
- Coverage percentage
- Any failing tests that need attention
