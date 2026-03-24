#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_billboard() -> int:
    import zero2w_billboard_case as m

    _, body, lid = m.make_stand_assembly()
    body_solid_count = body.solids().size()
    lid_solid_count = lid.solids().size()
    body_valid = body.val().isValid()
    lid_valid = lid.val().isValid()

    print("[billboard]")
    print(f"body solids: {body_solid_count}")
    print(f"lid solids: {lid_solid_count}")
    print(f"body isValid: {body_valid}")
    print(f"lid isValid: {lid_valid}")

    ok = body_solid_count == 1 and lid_solid_count == 1 and body_valid and lid_valid
    print(f"PASS: {ok}")
    return 0 if ok else 1


def check_case() -> int:
    import zero2w_waveshare213_ir_case as m

    base = m.make_base()
    lid = m.make_lid()
    base_solid_count = base.solids().size()
    lid_solid_count = lid.solids().size()
    base_valid = base.val().isValid()
    lid_valid = lid.val().isValid()

    print("[case]")
    print(f"base solids: {base_solid_count}")
    print(f"lid solids: {lid_solid_count}")
    print(f"base isValid: {base_valid}")
    print(f"lid isValid: {lid_valid}")

    ok = base_solid_count == 1 and lid_solid_count == 1 and base_valid and lid_valid
    print(f"PASS: {ok}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Check model connectivity/validity")
    parser.add_argument("--model", choices=["billboard", "case", "all"], default="all")
    args = parser.parse_args()

    status = 0
    if args.model in ("billboard", "all"):
        status = max(status, check_billboard())
    if args.model in ("case", "all"):
        status = max(status, check_case())
    return status


if __name__ == "__main__":
    raise SystemExit(main())
