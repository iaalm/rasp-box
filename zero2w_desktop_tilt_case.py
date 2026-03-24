"""
Desktop tilted enclosure for Raspberry Pi Zero 2 W (from scratch).

Style goals (close to the reference photo):
- Front display bezel with a large window
- Slight backward tilt for desk viewing
- Side ventilation slots
- Two simple feet integrated into the body
- Rear service cover

Model notes:
- This file is independent from existing models in the repo.
- Dimensions are parametric and tuned for Pi Zero 2 W + 2.13" e-paper class modules.
"""

from pathlib import Path

import cadquery as cq
from cadquery import exporters


PARAMS = {
    # Raspberry Pi Zero 2 W baseline
    "pi_l": 65.0,
    "pi_w": 30.0,
    "pi_hole_dx": 58.0,
    "pi_hole_dy": 23.0,
    # Main body envelope
    "body_l": 96.0,  # X
    "body_h": 64.0,  # Z
    "body_d": 22.0,  # Y (front to back)
    "wall": 2.2,
    "corner_r": 3.0,
    # Front window / bezel
    "view_l": 72.0,
    "view_h": 37.0,
    "view_corner_r": 2.0,
    # Internal mounting
    "standoff_h": 4.0,
    "standoff_od": 5.4,
    "standoff_hole_d": 2.7,  # M2.5 clearance
    "board_z_from_floor": 5.0,  # board center offset in Z
    # Ports (assumes connectors leave from side walls)
    "usb_cut_w": 16.0,
    "usb_cut_h": 8.2,
    "hdmi_cut_w": 15.0,
    "hdmi_cut_h": 8.0,
    "port_z": 9.0,
    "sd_cut_w": 15.0,
    "sd_cut_h": 4.0,
    "sd_z": 4.0,
    # Vents
    "vent_rows": 2,
    "vent_cols": 6,
    "vent_slot_w": 3.8,
    "vent_slot_h": 1.8,
    "vent_pitch_x": 6.2,
    "vent_pitch_z": 5.0,
    "vent_z_center": 16.0,
    # Antenna passthrough (decorative / optional)
    "antenna_hole_d": 7.0,
    "antenna_dx": 23.0,
    "antenna_z": 56.0,
    # Feet
    "foot_l": 16.0,
    "foot_w": 5.0,
    "foot_h": 5.0,
    "foot_y_out": 0.0,
    "foot_z_overlap": 1.0,
    "foot_x_offset": 39.0,
    # Rear cover
    "cover_t": 2.0,
    "cover_lip_h": 3.0,
    "cover_fit_gap": 0.3,
    # Whole body tilt (for desk view)
    "tilt_deg": 13.0,
}
MODEL_NAME = "zero2w_desktop_tilt_case"


def _pi_hole_points(p):
    dx = p["pi_hole_dx"] / 2.0
    dy = p["pi_hole_dy"] / 2.0
    return [(-dx, -dy), (dx, -dy), (-dx, dy), (dx, dy)]


def make_body(p=PARAMS):
    body_l = p["body_l"]
    body_h = p["body_h"]
    body_d = p["body_d"]
    wall = p["wall"]

    # Main shell
    body = (
        cq.Workplane("XZ")
        .rect(body_l, body_h)
        .extrude(body_d)
        .edges("|Y")
        .fillet(p["corner_r"])
    )

    # Back cavity (leave front wall as bezel support)
    cavity = (
        cq.Workplane("XZ")
        .workplane(offset=wall)
        .rect(body_l - 2 * wall, body_h - 2 * wall)
        .extrude(body_d - 2 * wall)
    )
    body = body.cut(cavity)

    # Front display window
    view = (
        cq.Workplane("XZ")
        .workplane(offset=-0.1)
        .rect(p["view_l"], p["view_h"])
        .extrude(wall + 0.4)
        .edges("|Y")
        .fillet(p["view_corner_r"])
    )
    body = body.cut(view)

    # Pi mounting standoffs on inner rear wall (extrude towards the front).
    board_y = body_d - wall
    standoffs = (
        cq.Workplane("XZ")
        .workplane(offset=board_y)
        .pushPoints(_pi_hole_points(p))
        .circle(p["standoff_od"] / 2.0)
        .extrude(-(p["standoff_h"] + 0.8))
    )
    standoff_holes = (
        cq.Workplane("XZ")
        .workplane(offset=board_y)
        .pushPoints(_pi_hole_points(p))
        .circle(p["standoff_hole_d"] / 2.0)
        .extrude(-(p["standoff_h"] + 1.2))
    )
    body = body.union(standoffs).cut(standoff_holes)

    # Left side: dual USB + mini HDMI openings
    left_x = -body_l / 2.0 - 0.1
    usb_cut = (
        cq.Workplane("YZ")
        .workplane(offset=left_x)
        .center(0.0, p["port_z"])
        .rect(p["usb_cut_w"], p["usb_cut_h"])
        .extrude(wall + 0.6)
    )
    hdmi_cut = (
        cq.Workplane("YZ")
        .workplane(offset=left_x)
        .center(12.0, p["port_z"])
        .rect(p["hdmi_cut_w"], p["hdmi_cut_h"])
        .extrude(wall + 0.6)
    )
    body = body.cut(usb_cut).cut(hdmi_cut)

    # Right side: microSD card opening
    right_x = body_l / 2.0 + 0.1
    sd_cut = (
        cq.Workplane("YZ")
        .workplane(offset=right_x)
        .center(-6.0, p["sd_z"])
        .rect(p["sd_cut_w"], p["sd_cut_h"])
        .extrude(wall + 0.6)
    )
    body = body.cut(sd_cut)

    # Vent slots on both sides
    sx = -(p["vent_cols"] - 1) * p["vent_pitch_x"] / 2.0
    sz = p["vent_z_center"] - (p["vent_rows"] - 1) * p["vent_pitch_z"] / 2.0
    vent_pts = []
    for r in range(p["vent_rows"]):
        for c in range(p["vent_cols"]):
            vent_pts.append((sx + c * p["vent_pitch_x"], sz + r * p["vent_pitch_z"]))

    left_vents = (
        cq.Workplane("YZ")
        .workplane(offset=left_x)
        .pushPoints(vent_pts)
        .rect(p["vent_slot_w"], p["vent_slot_h"])
        .extrude(wall + 0.8)
    )
    right_vents = (
        cq.Workplane("YZ")
        .workplane(offset=right_x)
        .pushPoints(vent_pts)
        .rect(p["vent_slot_w"], p["vent_slot_h"])
        .extrude(wall + 0.8)
    )
    body = body.cut(left_vents).cut(right_vents)

    # Top antenna passthrough holes
    top_z = body_h / 2.0 + 0.1
    antenna = (
        cq.Workplane("XY")
        .workplane(offset=top_z)
        .pushPoints([(-p["antenna_dx"], body_d / 2.0), (p["antenna_dx"], body_d / 2.0)])
        .circle(p["antenna_hole_d"] / 2.0)
        .extrude(wall + 0.8)
    )
    body = body.cut(antenna)

    # Tilt whole body around X-axis, front edge as visual reference.
    body = body.rotate((0, 0, 0), (1, 0, 0), p["tilt_deg"])

    # Integrated feet in final orientation; force overlap with shell.
    bb = body.val().BoundingBox()
    foot_y = bb.ymax - wall / 2.0 + p["foot_y_out"]
    foot_z = bb.zmin + p["foot_h"] / 2.0 + p["foot_z_overlap"]
    feet = (
        cq.Workplane("XY")
        .box(p["foot_l"], p["foot_w"], p["foot_h"])
        .translate((-p["foot_x_offset"], foot_y, foot_z))
    ).union(
        cq.Workplane("XY")
        .box(p["foot_l"], p["foot_w"], p["foot_h"])
        .translate((p["foot_x_offset"], foot_y, foot_z))
    )
    body = body.union(feet)
    return body


def make_rear_cover(p=PARAMS):
    body_l = p["body_l"]
    body_h = p["body_h"]
    body_d = p["body_d"]
    wall = p["wall"]

    cover = cq.Workplane("XZ").rect(body_l, body_h).extrude(p["cover_t"])
    cover = cover.edges("|Y").fillet(max(0.8, p["corner_r"] - 0.8))

    lip_l = body_l - 2.0 * (wall + p["cover_fit_gap"])
    lip_h = body_h - 2.0 * (wall + p["cover_fit_gap"])
    lip = (
        cq.Workplane("XZ")
        .workplane(offset=p["cover_t"])
        .rect(lip_l, lip_h)
        .extrude(p["cover_lip_h"])
    )
    cover = cover.union(lip)

    # Place cover at rear opening and apply same tilt.
    cover = cover.translate((0, body_d - p["cover_t"], 0))
    cover = cover.rotate((0, 0, 0), (1, 0, 0), p["tilt_deg"])
    return cover


def build_assembly(p=PARAMS):
    body = make_body(p)
    cover = make_rear_cover(p)
    asm = cq.Assembly(name="zero2w_desktop_tilt_case")
    asm.add(body, name="body", color=cq.Color(0.57, 0.79, 0.94))
    asm.add(cover, name="rear_cover", color=cq.Color(0.50, 0.72, 0.88))
    return asm, body, cover


def build_model(p=PARAMS):
    asm, body, rear_cover = build_assembly(p)
    return {
        "name": MODEL_NAME,
        "assembly": asm,
        "parts": {
            "body": body,
            "rear_cover": rear_cover,
        },
    }


def export_all(prefix="zero2w_desktop_tilt_case", p=PARAMS, output_dir="exports"):
    model = build_model(p)
    asm = model["assembly"]
    parts = model["parts"]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for part_name, shape in parts.items():
        exporters.export(shape, str(out / f"{prefix}_{part_name}.stl"))
        exporters.export(shape, str(out / f"{prefix}_{part_name}.step"))
    try:
        asm.save(str(out / f"{prefix}.step"))
    except Exception:
        pass


if __name__ == "__main__":
    show_object(make_body(), name="body")
    show_object(make_rear_cover(), name="rear_cover")
