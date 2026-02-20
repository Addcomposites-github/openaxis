# Test Fixtures

This directory holds **human-verified** reference outputs that the automated test suite
compares against. Every file here was produced by running real software (ORNL Slicer 2,
a real robot, or an independently verified tool) — not by running OpenAxis and accepting
what it produced.

## Why fixtures must be created by a human

An automated test that compares OpenAxis output against itself proves nothing. If the
slicer has a bug that shifts all Z coordinates by 1 mm, and we generate the fixture
by running the same slicer, both the expected and actual values will be wrong by 1 mm
and the test will pass. Fixtures catch bugs only when they were created independently.

## Current Fixtures

*(none yet — waiting for first ORNL Slicer 2 run)*

## How to Add a Fixture

1. Open ORNL Slicer 2 (must be installed — see `docs/user-guide/ornl-slicer-setup.md`)
2. Load the STL from `test-geometry/`
3. Set **exact** parameters (document them in this README under the fixture name)
4. Run the slicer
5. Save the `.gcode` output to this directory
6. Add an entry to the table below
7. Commit with message: `test: add ORNL fixture for <geometry> <settings>`

## Fixture Registry

| File | Geometry | Settings | Date created | Created by |
|------|----------|----------|--------------|------------|
| *(none)* | — | — | — | — |

## First Fixture to Create

**File:** `test_box_2mm_1wall_0infill.gcode`
**Geometry:** `test-geometry/test_box.stl`
**Settings:**
```
Layer height:   2.0 mm
Bead width:     6.0 mm
Perimeters:     1
Infill density: 0%
Support:        off
Auto-centre:    on
```

Once this file exists, the test `tests/integration/test_slicing_fixtures.py` will
automatically activate (it currently skips with a clear message).
