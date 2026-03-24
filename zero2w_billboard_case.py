"""
Billboard-style enclosure for Raspberry Pi Zero 2 W + Waveshare 2.13" e-Paper.

Concept:
- A weighted "base box" contains the Pi Zero 2 W and wiring.
- A vertical post lifts the display to a "billboard panel" area.
- The billboard head has a front viewing window for the e-paper.
- Dedicated IR LED position on the front of the base (AC control use case).

This is a parametric starter model. Tune PARAMS for your exact module revisions.
"""

import cadquery as cq
from cadquery import exporters
from pathlib import Path


PARAMS = {
    # Pi Zero 2 W
    "pi_l": 65.0,
    "pi_w": 30.0,
    "pi_hole_dx": 58.0,
    "pi_hole_dy": 23.0,
    "standoff_h": 3.5,
    "standoff_od": 5.2,
    "standoff_hole_d": 2.7,
    # E-paper (Waveshare 2.13")
    "disp_pcb_l": 65.0,
    "disp_pcb_w": 30.2,
    "disp_pcb_t": 2.0,
    "disp_view_l": 48.55,
    "disp_view_w": 23.71,
    # Base box
    "base_wall": 2.4,
    "base_floor": 2.4,
    "base_margin_x": 8.0,
    "base_margin_y": 10.0,
    "base_inner_h": 17.0,
    "base_corner_r": 4.0,
    # Base lid
    "lid_thickness": 2.0,
    "lid_lip_h": 3.0,
    "fit_gap": 0.3,
    # Billboard post
    "post_w": 12.0,
    "post_t": 8.0,
    "post_h": 48.0,
    "neck_w": 10.0,      # connector width between post and head
    "neck_h": 8.0,       # connector height between post and head
    "neck_drop": 6.0,    # how far below head center the connector sits
    # Billboard head (panel housing)
    "head_wall": 2.0,
    "head_depth": 8.0,
    "head_bezel": 3.0,
    "head_corner_r": 2.0,
    # Display mount pads in head
    "disp_pad_d": 4.0,
    "disp_pad_hole_d": 2.1,
    "disp_pad_h": 3.0,
    # Cable channel
    "cable_slot_w": 8.0,
    "cable_slot_h": 4.0,
    # IR LED on base front
    "ir_led_d": 5.2,
    "ir_pos_x": 0.0,
    "ir_pos_z": 8.0,
    "ir_tunnel_d": 6.8,
    "ir_tunnel_len": 8.0,
}
MODEL_NAME = "zero2w_billboard_case"


def _pi_hole_points(p):
    dx = p["pi_hole_dx"] / 2.0
    dy = p["pi_hole_dy"] / 2.0
    return [(-dx, -dy), (dx, -dy), (-dx, dy), (dx, dy)]


def _base_sizes(p):
    inner_l = p["pi_l"] + 2 * p["base_margin_x"]
    inner_w = p["pi_w"] + 2 * p["base_margin_y"]
    outer_l = inner_l + 2 * p["base_wall"]
    outer_w = inner_w + 2 * p["base_wall"]
    outer_h = p["base_floor"] + p["base_inner_h"]
    return inner_l, inner_w, outer_l, outer_w, outer_h


def make_base_body(p=PARAMS):
    inner_l, inner_w, outer_l, outer_w, outer_h = _base_sizes(p)

    base = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(outer_h)
        .edges("|Z")
        .fillet(p["base_corner_r"])
    )

    cavity = (
        cq.Workplane("XY")
        .workplane(offset=p["base_floor"])
        .rect(inner_l, inner_w)
        .extrude(p["base_inner_h"] + 0.4)
    )
    base = base.cut(cavity)

    # Pi standoffs
    standoffs = (
        cq.Workplane("XY")
        .workplane(offset=p["base_floor"])
        .pushPoints(_pi_hole_points(p))
        .circle(p["standoff_od"] / 2.0)
        .extrude(p["standoff_h"])
    )
    standoff_holes = (
        cq.Workplane("XY")
        .workplane(offset=p["base_floor"])
        .pushPoints(_pi_hole_points(p))
        .circle(p["standoff_hole_d"] / 2.0)
        .extrude(p["standoff_h"] + 0.5)
    )
    base = base.union(standoffs).cut(standoff_holes)

    # Front IR LED tunnel
    _, _, _, _, _ = _base_sizes(p)
    front_y = -outer_w / 2.0
    ir_tunnel = (
        cq.Workplane("XZ")
        .workplane(offset=front_y - p["ir_tunnel_len"])
        .center(p["ir_pos_x"], p["ir_pos_z"])
        .circle(p["ir_tunnel_d"] / 2.0)
        .extrude(p["ir_tunnel_len"])
    )
    ir_hole = (
        cq.Workplane("XZ")
        .workplane(offset=front_y - p["base_wall"] - 0.1)
        .center(p["ir_pos_x"], p["ir_pos_z"])
        .circle(p["ir_led_d"] / 2.0)
        .extrude(p["base_wall"] + 0.6)
    )
    base = base.union(ir_tunnel).cut(ir_hole)

    # Back cable notch
    back_y = outer_w / 2.0 + 0.1
    cable_cut = (
        cq.Workplane("XZ")
        .workplane(offset=back_y)
        .center(0, p["base_floor"] + 6.0)
        .rect(p["cable_slot_w"], p["cable_slot_h"])
        .extrude(p["base_wall"] + 0.6)
    )
    base = base.cut(cable_cut)

    return base


def make_base_lid(p=PARAMS):
    _, _, outer_l, outer_w, _ = _base_sizes(p)
    lid = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(p["lid_thickness"])
        .edges("|Z")
        .fillet(max(1.0, p["base_corner_r"] - 0.8))
    )
    lip = (
        cq.Workplane("XY")
        .workplane(offset=-p["lid_lip_h"])
        .rect(
            outer_l - 2 * (p["base_wall"] + p["fit_gap"]),
            outer_w - 2 * (p["base_wall"] + p["fit_gap"]),
        )
        .extrude(p["lid_lip_h"])
    )
    return lid.union(lip)


def make_billboard_head(p=PARAMS):
    view_l = p["disp_view_l"]
    view_w = p["disp_view_w"]
    bezel = p["head_bezel"]
    head_w = p["disp_pcb_l"] + 2 * (bezel + 1.0)
    head_h = p["disp_pcb_w"] + 2 * (bezel + 1.0)
    head_d = p["head_depth"]

    # Head block, centered at origin in XY, extruded in +Z
    head = (
        cq.Workplane("XY")
        .rect(head_w, head_h)
        .extrude(head_d)
        .edges("|Z")
        .fillet(p["head_corner_r"])
    )

    # Hollow pocket from rear
    pocket = (
        cq.Workplane("XY")
        .workplane(offset=p["head_wall"])
        .rect(head_w - 2 * p["head_wall"], head_h - 2 * p["head_wall"])
        .extrude(head_d)
    )
    head = head.cut(pocket)

    # Front viewing window
    window_cut = (
        cq.Workplane("XY")
        .workplane(offset=-0.1)
        .rect(view_l, view_w)
        .extrude(p["head_wall"] + 0.5)
    )
    head = head.cut(window_cut)

    # Display mounting pads (2 diagonal points)
    post_x = p["disp_pcb_l"] / 2.0 - 3.0
    post_y = p["disp_pcb_w"] / 2.0 - 3.0
    pad_pts = [(-post_x, -post_y), (post_x, post_y)]
    pads = (
        cq.Workplane("XY")
        .workplane(offset=p["head_wall"])
        .pushPoints(pad_pts)
        .circle(p["disp_pad_d"] / 2.0)
        .extrude(p["disp_pad_h"])
    )
    pad_holes = (
        cq.Workplane("XY")
        .workplane(offset=p["head_wall"])
        .pushPoints(pad_pts)
        .circle(p["disp_pad_hole_d"] / 2.0)
        .extrude(p["disp_pad_h"] + 0.4)
    )
    head = head.union(pads).cut(pad_holes)

    # Wire pass-through to post
    pass_hole = (
        cq.Workplane("YZ")
        .workplane(offset=0)
        .center(0, p["head_wall"] + 3.0)
        .rect(p["cable_slot_w"], p["cable_slot_h"])
        .extrude(head_w / 2.0 + 1.0)
        .translate((-head_w / 2.0, 0, 0))
    )
    head = head.cut(pass_hole)

    return head, head_w, head_h


def make_post(p=PARAMS):
    return cq.Workplane("XY").rect(p["post_w"], p["post_t"]).extrude(p["post_h"])


def make_stand_assembly(p=PARAMS):
    _, _, _, outer_w, base_h = _base_sizes(p)
    base = make_base_body(p)
    lid = make_base_lid(p).translate((0, 0, base_h + p["fit_gap"]))

    # Anchor post on rear wall region (solid material), not over the hollow center.
    post_y = outer_w / 2.0 - p["base_wall"] / 2.0
    # Sink post 1 mm into base to guarantee boolean overlap.
    post = make_post(p).translate((0, post_y, base_h - 1.0))
    head, _, _ = make_billboard_head(p)
    # Rotate so the display window faces the front (-Y), matching IR direction.
    head = head.rotate((0, 0, 0), (1, 0, 0), -90)
    head = head.translate((0, -outer_w / 2.0 - p["head_depth"] / 2.0, base_h + p["post_h"]))

    # Structural neck: explicitly overlap both post and head.
    # Using overlap (not just touching) avoids disconnected solids after booleans.
    neck_y_start = post_y - p["post_t"] / 2.0
    # End inside the head rear wall region to force solid overlap.
    neck_y_end = -outer_w / 2.0 - p["head_depth"] / 2.0 + 0.5
    neck_len = abs(neck_y_end - neck_y_start)
    neck_center_y = (neck_y_start + neck_y_end) / 2.0
    neck = (
        cq.Workplane("XY")
        .box(p["neck_w"], neck_len, p["neck_h"])
        .translate((0, neck_center_y, base_h + p["post_h"] - p["neck_drop"]))
    )

    # Bridge block guarantees overlap between neck and head shell.
    head_bridge = (
        cq.Workplane("XY")
        .box(p["neck_w"] + 2.0, 6.0, p["neck_h"] + 4.0)
        .translate(
            (
                0,
                -outer_w / 2.0 - p["head_depth"] / 2.0 + 2.0,
                base_h + p["post_h"] - p["neck_drop"],
            )
        )
    )

    # Merge post into base as one printable "body"
    body = base.union(post).union(neck).union(head_bridge).union(head)

    asm = cq.Assembly(name="zero2w_billboard_case")
    asm.add(body, name="body", color=cq.Color(0.22, 0.22, 0.24))
    asm.add(lid, name="lid", color=cq.Color(0.14, 0.14, 0.16))
    return asm, body, lid


def build_model(p=PARAMS):
    asm, body, lid = make_stand_assembly(p)
    return {
        "name": MODEL_NAME,
        "assembly": asm,
        "parts": {
            "body": body,
            "lid": lid,
        },
    }


def export_all(prefix="zero2w_billboard_case", p=PARAMS, output_dir="exports"):
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
    _, body, lid = make_stand_assembly()
    show_object(body, name="body")
    show_object(lid, name="lid")
