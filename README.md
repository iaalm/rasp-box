# rasp-box

Parametric CadQuery models for Raspberry Pi Zero 2 W enclosures.

## Structure

- `zero2w_waveshare213_ir_case.py`: compact enclosure model
- `zero2w_billboard_case.py`: billboard-style stand model
- `scripts/export_case.py`: export compact enclosure STL/STEP
- `scripts/export_billboard.py`: export billboard STL/STEP
- `scripts/check_connectivity.py`: validate single-solid connectivity
- `exports/`: generated CAD files (ignored by git)

## Setup

```bash
python3.11 -m venv .venv311
./.venv311/bin/python -m pip install --upgrade pip
./.venv311/bin/python -m pip install cadquery
```

## Usage

```bash
./.venv311/bin/python scripts/check_connectivity.py --model all
./.venv311/bin/python scripts/export_case.py
./.venv311/bin/python scripts/export_billboard.py
```
