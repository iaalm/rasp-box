"""
Parametric Raspberry Pi Zero 2 W case with:
- Waveshare 2.13" display tray (wired, no 40-pin HAT stacking)
- Dedicated IR LED holder for AC remote control

How to use (CadQuery 2.x):
1) cq-editor: open this file and run.
2) Python:
   import zero2w_waveshare213_ir_case as m
   m.export_all()

This model intentionally keeps dimensions configurable. Please verify display PCB
size and connector positions, then adjust PARAMS.
"""

import cadquery as cq
from cadquery import exporters
from pathlib import Path


PARAMS = {
    # General shell
    "wall": 2.0,
    "floor": 2.0,
    "inner_clearance_z": 15.0,
    "corner_r": 3.0,
    "lid_overlap_h": 3.0,
    "lid_thickness": 2.0,
    "fit_gap": 0.3,  # assembly gap between base and lid
    # Pi Zero 2 W board (official board approx 65 x 30 mm)
    "pi_l": 65.0,
    "pi_w": 30.0,
    "pi_t": 1.6,
    # M2.5 mounting hole spacing for Zero family
    "pi_hole_dx": 58.0,
    "pi_hole_dy": 23.0,
    "standoff_h": 3.5,
    "standoff_od": 5.2,
    "standoff_hole_d": 2.7,  # loose M2.5
    # Inner margins around board
    "margin_x": 5.0,
    "margin_y": 6.0,
    # Connector side openings (tune with your cable set)
    "usb_window_w": 16.0,
    "usb_window_h": 8.0,
    "usb_window_z": 4.5,
    "hdmi_window_w": 18.0,
    "hdmi_window_h": 8.0,
    "hdmi_window_z": 4.5,
    "sd_window_w": 14.0,
    "sd_window_h": 4.0,
    "sd_window_z": 2.5,
    # Waveshare 2.13" display tray (wired, no header mating)
    # Waveshare 2.13" e-Paper HAT manual (common V2/V3/V4):
    # Driver board 65.0 x 30.2 mm, visible area 48.55 x 23.71 mm.
    "disp_pcb_l": 65.0,
    "disp_pcb_w": 30.2,
    "disp_pcb_t": 2.0,
    "disp_clearance": 0.5,
    "disp_raise_h": 4.0,      # tray stand height above case floor
    "disp_offset_y": 0.0,     # center offset in Y
    "disp_mount_post_d": 4.0,
    "disp_mount_hole_d": 2.1, # M2
    # Lid viewing window for the display
    # If your visible area differs from PCB size, tune these two values.
    "disp_view_l": 48.55,
    "disp_view_w": 23.71,
    "disp_view_corner_r": 1.5,
    "disp_view_bezel": 2.0,   # frame width around viewing window
    # FPC/wire routing
    "wire_slot_w": 10.0,
    "wire_slot_h": 3.5,
    # IR LED holder (5mm LED + aiming tunnel)
    "ir_led_d": 5.2,
    "ir_led_clip_len": 7.0,
    "ir_tunnel_d": 6.5,
    "ir_tunnel_len": 8.0,
    "ir_pos_x": 0.0,   # relative to case center
    "ir_pos_y": -20.0,
    "ir_pos_z": 8.0,
    # Ventilation
    "vent_rows": 2,
    "vent_cols": 6,
    "vent_slot_w": 4.0,
    "vent_slot_h": 1.8,
    "vent_pitch_x": 7.0,
    "vent_pitch_y": 5.0,
}
MODEL_NAME = "zero2w_waveshare213_ir_case"


def _case_outer_size(p):
    inner_l = p["pi_l"] + 2 * p["margin_x"]
    inner_w = p["pi_w"] + 2 * p["margin_y"]
    outer_l = inner_l + 2 * p["wall"]
    outer_w = inner_w + 2 * p["wall"]
    outer_h = p["floor"] + p["inner_clearance_z"]
    return inner_l, inner_w, outer_l, outer_w, outer_h


def _pi_hole_points(p):
    dx = p["pi_hole_dx"] / 2.0
    dy = p["pi_hole_dy"] / 2.0
    return [(-dx, -dy), (dx, -dy), (-dx, dy), (dx, dy)]


def make_base(p=PARAMS):
    inner_l, inner_w, outer_l, outer_w, outer_h = _case_outer_size(p)

    base = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(outer_h)
        .edges("|Z")
        .fillet(p["corner_r"])
    )

    # Hollow cavity
    cavity = (
        cq.Workplane("XY")
        .workplane(offset=p["floor"])
        .rect(inner_l, inner_w)
        .extrude(p["inner_clearance_z"] + 0.2)
    )
    base = base.cut(cavity)

    # Pi standoffs and through holes
    standoff_plane = cq.Workplane("XY").workplane(offset=p["floor"])
    standoffs = (
        standoff_plane
        .pushPoints(_pi_hole_points(p))
        .circle(p["standoff_od"] / 2.0)
        .extrude(p["standoff_h"])
    )
    standoff_holes = (
        standoff_plane
        .pushPoints(_pi_hole_points(p))
        .circle(p["standoff_hole_d"] / 2.0)
        .extrude(p["standoff_h"] + 0.4)
    )
    base = base.union(standoffs).cut(standoff_holes)

    # Display tray (upper side, still inside enclosure)
    tray_l = p["disp_pcb_l"] + 2 * p["disp_clearance"]
    tray_w = p["disp_pcb_w"] + 2 * p["disp_clearance"]
    tray_z = p["floor"] + p["disp_raise_h"]
    tray = (
        cq.Workplane("XY")
        .workplane(offset=tray_z)
        .center(0, p["disp_offset_y"])
        .rect(tray_l, tray_w)
        .extrude(p["disp_pcb_t"])
    )
    base = base.union(tray)

    # Connect tray to floor with ribs so it is a single printable body.
    rib_pts = [
        (tray_l / 2.0 - 2.0, tray_w / 2.0 - 2.0),
        (-tray_l / 2.0 + 2.0, tray_w / 2.0 - 2.0),
        (tray_l / 2.0 - 2.0, -tray_w / 2.0 + 2.0),
        (-tray_l / 2.0 + 2.0, -tray_w / 2.0 + 2.0),
    ]
    tray_ribs = (
        cq.Workplane("XY")
        .workplane(offset=p["floor"])
        .center(0, p["disp_offset_y"])
        .pushPoints(rib_pts)
        .rect(3.0, 3.0)
        .extrude(max(0.8, p["disp_raise_h"]))
    )
    base = base.union(tray_ribs)

    # Two display mount posts (generic M2)
    post_y = p["disp_pcb_w"] / 2.0 - 3.0
    post_x = p["disp_pcb_l"] / 2.0 - 3.0
    post_pts = [(-post_x, -post_y), (post_x, post_y)]
    disp_posts = (
        cq.Workplane("XY")
        .workplane(offset=tray_z + p["disp_pcb_t"])
        .pushPoints(post_pts)
        .circle(p["disp_mount_post_d"] / 2.0)
        .extrude(4.0)
    )
    disp_post_holes = (
        cq.Workplane("XY")
        .workplane(offset=tray_z + p["disp_pcb_t"])
        .pushPoints(post_pts)
        .circle(p["disp_mount_hole_d"] / 2.0)
        .extrude(4.2)
    )
    base = base.union(disp_posts).cut(disp_post_holes)

    # Cable slot near display tray
    cable_slot = (
        cq.Workplane("YZ")
        .workplane(offset=0)
        .center(0, tray_z + p["disp_pcb_t"] / 2.0)
        .rect(p["wire_slot_w"], p["wire_slot_h"])
        .extrude(outer_l / 2.0 + p["wall"])
        .translate((-outer_l / 2.0, 0, 0))
    )
    base = base.cut(cable_slot)

    # USB/HDMI openings on one long side
    side_x = outer_l / 2.0 + 0.1
    usb_cut = (
        cq.Workplane("YZ")
        .workplane(offset=side_x)
        .center(-7.0, p["usb_window_z"])
        .rect(p["usb_window_w"], p["usb_window_h"])
        .extrude(p["wall"] + 0.4)
    )
    hdmi_cut = (
        cq.Workplane("YZ")
        .workplane(offset=side_x)
        .center(8.0, p["hdmi_window_z"])
        .rect(p["hdmi_window_w"], p["hdmi_window_h"])
        .extrude(p["wall"] + 0.4)
    )
    base = base.cut(usb_cut).cut(hdmi_cut)

    # microSD opening on short side
    side_y = -outer_w / 2.0 - 0.1
    sd_cut = (
        cq.Workplane("XZ")
        .workplane(offset=side_y)
        .center(0.0, p["sd_window_z"])
        .rect(p["sd_window_w"], p["sd_window_h"])
        .extrude(p["wall"] + 0.4)
    )
    base = base.cut(sd_cut)

    # IR LED holder: clip hole + aim tunnel
    ir_x = p["ir_pos_x"]
    ir_y = p["ir_pos_y"]
    ir_z = p["ir_pos_z"]
    tunnel = (
        cq.Workplane("YZ")
        .workplane(offset=-outer_l / 2.0 - p["ir_tunnel_len"] / 2.0)
        .center(ir_y, ir_z)
        .circle(p["ir_tunnel_d"] / 2.0)
        .extrude(p["ir_tunnel_len"])
    )
    led_hole = (
        cq.Workplane("YZ")
        .workplane(offset=-outer_l / 2.0 + p["wall"] / 2.0)
        .center(ir_y, ir_z)
        .circle(p["ir_led_d"] / 2.0)
        .extrude(p["ir_led_clip_len"])
    )
    base = base.union(tunnel).cut(led_hole)

    return base.translate((ir_x, 0, 0))


def make_lid(p=PARAMS):
    inner_l, inner_w, outer_l, outer_w, _ = _case_outer_size(p)
    fit_l = outer_l - 2 * p["fit_gap"]
    fit_w = outer_w - 2 * p["fit_gap"]

    lid = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(p["lid_thickness"])
        .edges("|Z")
        .fillet(max(0.8, p["corner_r"] - 0.6))
    )

    # Inner lip to align lid into base
    lip = (
        cq.Workplane("XY")
        .workplane(offset=-p["lid_overlap_h"])
        .rect(fit_l - 2 * p["wall"], fit_w - 2 * p["wall"])
        .extrude(p["lid_overlap_h"])
    )
    lid = lid.union(lip)

    # Display viewing window on top lid
    window_l = p["disp_view_l"]
    window_w = p["disp_view_w"]
    window_r = min(p["disp_view_corner_r"], min(window_l, window_w) / 2.0 - 0.1)
    view_cut = (
        cq.Workplane("XY")
        .center(0, p["disp_offset_y"])
        .rect(window_l, window_w)
        .extrude(p["lid_thickness"] + 0.6)
        .edges("|Z")
        .fillet(max(0.2, window_r))
    )
    lid = lid.cut(view_cut)

    # Keep minimum frame around window for strength
    frame_outer_l = window_l + 2 * p["disp_view_bezel"]
    frame_outer_w = window_w + 2 * p["disp_view_bezel"]
    frame = (
        cq.Workplane("XY")
        .center(0, p["disp_offset_y"])
        .rect(frame_outer_l, frame_outer_w)
        .extrude(0.6)
    )
    frame_cut = (
        cq.Workplane("XY")
        .center(0, p["disp_offset_y"])
        .rect(window_l, window_w)
        .extrude(0.8)
    )
    lid = lid.union(frame.cut(frame_cut))

    # Vent slots
    start_x = -(p["vent_cols"] - 1) * p["vent_pitch_x"] / 2.0
    start_y = -(p["vent_rows"] - 1) * p["vent_pitch_y"] / 2.0
    vents = []
    for r in range(p["vent_rows"]):
        for c in range(p["vent_cols"]):
            vents.append((start_x + c * p["vent_pitch_x"], start_y + r * p["vent_pitch_y"]))
    vent_cut = (
        cq.Workplane("XY")
        .workplane(offset=0.3)
        .pushPoints(vents)
        .rect(p["vent_slot_w"], p["vent_slot_h"])
        .extrude(p["lid_thickness"] + 0.4)
    )
    lid = lid.cut(vent_cut)

    return lid


def build_assembly(p=PARAMS):
    inner_l, inner_w, outer_l, outer_w, outer_h = _case_outer_size(p)
    base = make_base(p)
    lid = make_lid(p).translate((0, 0, outer_h + p["fit_gap"]))

    asm = cq.Assembly(name="zero2w_waveshare213_ir_case")
    asm.add(base, name="base", color=cq.Color(0.2, 0.2, 0.25))
    asm.add(lid, name="lid", color=cq.Color(0.15, 0.15, 0.18))
    return asm, base, lid


def build_model(p=PARAMS):
    asm, base, lid = build_assembly(p)
    return {
        "name": MODEL_NAME,
        "assembly": asm,
        "parts": {
            "base": base,
            "lid": lid,
        },
    }


def export_all(prefix="zero2w_waveshare213_ir_case", p=PARAMS, output_dir="exports"):
    model = build_model(p)
    asm = model["assembly"]
    parts = model["parts"]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for part_name, shape in parts.items():
        exporters.export(shape, str(out / f"{prefix}_{part_name}.stl"))
        exporters.export(shape, str(out / f"{prefix}_{part_name}.step"))
    # CadQuery versions differ on assembly export APIs. Keep part exports
    # deterministic, and export assembly only when supported.
    try:
        asm.save(str(out / f"{prefix}.step"))
    except Exception:
        pass


if __name__ == "__main__":
    show_object(make_base(), name="base")
    show_object(make_lid().translate((0, 0, 20)), name="lid")
