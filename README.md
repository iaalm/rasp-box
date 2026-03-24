# rasp-box

Parametric CadQuery models for Raspberry Pi Zero 2 W enclosures.

## Structure

- `zero2w_waveshare213_ir_case.py`: compact enclosure model
- `zero2w_billboard_case.py`: billboard-style stand model
- `zero2w_desktop_tilt_case.py`: desktop tilted enclosure model
- `scripts/export_model.py`: unified exporter (`--model case|billboard|desktop`)
- `scripts/export_case.py`: compatibility wrapper for `--model case`
- `scripts/export_billboard.py`: compatibility wrapper for `--model billboard`
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
./.venv311/bin/python scripts/check_connectivity.py --model case
./.venv311/bin/python scripts/check_connectivity.py --model billboard
./.venv311/bin/python scripts/check_connectivity.py --model desktop
./.venv311/bin/python scripts/export_model.py --model case
./.venv311/bin/python scripts/export_model.py --model billboard
./.venv311/bin/python scripts/export_model.py --model desktop
```
