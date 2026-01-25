# Add Process Plugin

Add a new manufacturing process plugin to OpenAxis.

## Arguments
Process name: $ARGUMENTS

## Steps

1. **Create plugin structure**
   Create files in `src/slicing/processes/{process_name}/`:
   - `__init__.py` - Module exports
   - `process.py` - Main process class
   - `parameters.py` - Process parameters dataclass
   - `slicer.py` - Process-specific slicing logic

2. **Implement Process class**
   ```python
   from openaxis.core.plugin import Process, ProcessType
   from dataclasses import dataclass
   
   @dataclass
   class {ProcessName}Parameters:
       # Define process-specific parameters
       pass
   
   class {ProcessName}Process(Process):
       process_type = ProcessType.ADDITIVE  # or SUBTRACTIVE
       
       def __init__(self, parameters: {ProcessName}Parameters):
           self.parameters = parameters
       
       def validate_parameters(self) -> bool:
           # Validate process parameters
           pass
       
       def get_toolpath_generator(self):
           # Return appropriate slicer
           pass
   ```

3. **Create configuration schema**
   Add `config/processes/{process_name}_default.yaml`:
   ```yaml
   process:
     name: "{Process Name}"
     type: "{process_name}"
   
   parameters:
     # Process-specific parameters
   
   slicing:
     # Slicing configuration
   ```

4. **Register the plugin**
   Update `src/slicing/processes/__init__.py` to export the new process.

5. **Add tests**
   Create `tests/unit/slicing/test_{process_name}.py`:
   - Test parameter validation
   - Test toolpath generation with simple geometry
   - Test edge cases

6. **Add documentation**
   Create `docs/guides/processes/{process_name}.md`:
   - Process description
   - Parameter reference
   - Usage examples

## Validation

- [ ] Plugin loads without errors
- [ ] Parameters validate correctly
- [ ] Basic toolpath generates for simple cube
- [ ] All tests pass
- [ ] Documentation is complete
