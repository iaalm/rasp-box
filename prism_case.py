"""
三棱柱外壳 - 正三角形截面, 横放

坐标系:
  - XY 平面: 三角形截面 (底边沿 X 轴, 中心对齐)
  - Z 轴: 棱柱长度方向 (0 → 70mm)

  截面 (从前方看):
           * (0, 43.3)
          / \
         /   \
        /     \
       *───────*
    (-25,0)  (25,0)

  底面 (Y=0) 朝下, 平放在桌面上

运行: source ~/cad-env/bin/activate && python prism_case.py

导出 / 检查:
  ./.venv311/bin/python scripts/check_connectivity.py --model prism_case
  ./.venv311/bin/python scripts/export_model.py --model prism_case
"""

import sys
import types
import math

# ---- Mock ----
_nlopt = types.ModuleType("nlopt")
class _MockOpt:
    def __init__(self, *a, **kw): pass
    def __getattr__(self, name): return lambda *a, **kw: None
_nlopt.opt = _MockOpt
for _a in ["LN_BOBYQA", "GN_DIRECT", "GN_DIRECT_L", "LN_SBPLX",
           "G_MLSL", "LD_SLSQP", "LN_COBYLA", "LD_MMA", "AUGLAG"]:
    setattr(_nlopt, _a, 0)
sys.modules["nlopt"] = _nlopt
class _MockCasadi(types.ModuleType):
    class MX:
        sym = staticmethod(lambda *a, **kw: None)
    class SX:
        sym = staticmethod(lambda *a, **kw: None)
    class DM: pass
    class Opti: pass
    def __getattr__(self, name): return lambda *a, **kw: None
sys.modules["casadi"] = _MockCasadi("casadi")
# ---- End mock ----

import cadquery as cq
from cadquery import Plane, Vector


# ============================================================
# 参数
# ============================================================

PARAMS = {
    "SIDE": 50.0,       # 正三角形边长
    "LENGTH": 70.0,     # 棱柱长度
    "WALL": 3.0,        # 壁厚
    "OPENING_L": 60.0,  # 长边 (沿棱柱长度方向), 居中
    "OPENING_W": 30.0,  # 短边 (沿三角形边方向)
    "OPENING_SHORT_OFFSET": 5.0,  # 短边起始偏移
    "OUTER_DEPTH": 1.0,
    "INNER_OPENING_W": 32.0,
    "INNER_OPENING_L": 66.0,
    "INNER_DEPTH": 2.0,
    "SUPPORT_W": 5.0,
    "SUPPORT_PROTRUDE": 3.0,
    "SUPPORT_ANCHOR": 2.0,
    "SUPPORT_THICK": 2.0,
    "HOLE_D": 3.0,
    "HOLE_SPACING_SHORT": 23.0,
    "HOLE_SPACING_LONG": 58.0,
    "NARROW_PROTRUDE": 3.0,
    "NARROW_ANCHOR": 1.0,
    "FILLET_R": 0.25,
    "HOLE_OFFSET_SHORT": 6.0,
    "HOLE_OFFSET_LONG": -2.0
}

MODEL_NAME = "prism_case"


def build_prism_unsplit_shell(
    p,
    *,
    fillet_outer: bool = False,
    narrow_supports: bool = False,
    fillet_r: float | None = None,
):
    """
    完整三棱柱壳体（未沿 Z 切开）。供 prism_case / prism_case_2part 共用。
    """
    SIDE = p["SIDE"]
    LENGTH = p["LENGTH"]
    WALL = p["WALL"]
    OPENING_L = p["OPENING_L"]
    OPENING_W = p["OPENING_W"]
    OPENING_SHORT_OFFSET = p["OPENING_SHORT_OFFSET"]
    OUTER_DEPTH = p["OUTER_DEPTH"]
    INNER_OPENING_W = p["INNER_OPENING_W"]
    INNER_OPENING_L = p["INNER_OPENING_L"]
    INNER_DEPTH = p["INNER_DEPTH"]
    SUPPORT_W = p["SUPPORT_W"]
    SUPPORT_PROTRUDE = p["SUPPORT_PROTRUDE"]
    SUPPORT_ANCHOR = p["SUPPORT_ANCHOR"]
    SUPPORT_THICK = p["SUPPORT_THICK"]
    HOLE_D = p["HOLE_D"]
    HOLE_SPACING_SHORT = p["HOLE_SPACING_SHORT"]
    HOLE_SPACING_LONG = p["HOLE_SPACING_LONG"]
    HOLE_OFFSET_SHORT = p["HOLE_OFFSET_SHORT"]
    HOLE_OFFSET_LONG = p["HOLE_OFFSET_LONG"]
    if fillet_r is None:
        fillet_r = p["FILLET_R"]

    # ============================================================
    # 计算
    # ============================================================

    TRI_H = SIDE * math.sqrt(3) / 2  # 三角形高 ≈ 43.3mm

    # 外三角形顶点 (底边沿 X, 居中)
    outer_pts = [
        (-SIDE / 2, 0),
        (SIDE / 2, 0),
        (0, TRI_H),
    ]

    # 内三角形 (各边向内偏移 WALL)
    # 正三角形内切圆半径 = SIDE * √3 / 6
    inradius = SIDE * math.sqrt(3) / 6       # ≈ 14.43mm
    inner_inradius = inradius - WALL          # ≈ 11.43mm
    inner_side = inner_inradius * 2 * math.sqrt(3)  # ≈ 39.6mm
    inner_tri_h = inner_side * math.sqrt(3) / 2     # ≈ 34.3mm

    # 两个三角形共享重心 (0, TRI_H/3)
    centroid_y = TRI_H / 3                   # ≈ 14.43mm
    inner_bottom_y = centroid_y - inner_inradius  # = 3.0mm (= WALL)

    inner_pts = [
        (-inner_side / 2, inner_bottom_y),
        (inner_side / 2, inner_bottom_y),
        (0, inner_bottom_y + inner_tri_h),
    ]

    # ============================================================
    # 建模
    # ============================================================

    # 外棱柱
    outer = (
        cq.Workplane("XY")
        .polyline(outer_pts).close()
        .extrude(LENGTH)
    )
    if fillet_outer:
        outer = outer.edges().fillet(fillet_r)

    # 内棱柱 (前后各缩短 WALL)
    inner = (
        cq.Workplane("XY")
        .transformed(offset=(0, 0, WALL))
        .polyline(inner_pts).close()
        .extrude(LENGTH - 2 * WALL)
    )

    # 掏空
    shell = outer.cut(inner)

    # ============================================================
    # 阶梯式开口 (底面 Y=0)
    # ============================================================
    # 外层: 30×60mm, 1mm 深 (从 Y=0 到 Y=1)
    # 内层: 66×32mm, 2mm 深 (从 Y=1 到 Y=3), 打穿壁厚
    # 两层共享同一中心点

    # 外层 (小窗口, 显示区)
    OUTER_OPENING_W = OPENING_W   # 30mm (X方向)
    OUTER_OPENING_L = OPENING_L   # 60mm (Z方向)

    # 内层 (大口袋, 容纳 PCB/面板)

    # 两层中心 (沿用外层定位: 短边 5+30+15, 长边居中)
    opening_x_center = -SIDE / 2 + OPENING_SHORT_OFFSET + OPENING_W / 2  # = -5
    opening_z_center = LENGTH / 2  # = 35

    # 外层切割: Y=0 向内 1mm
    cut_outer = (
        cq.Workplane("XY")
        .box(OUTER_OPENING_W, OUTER_DEPTH + 0.1, OUTER_OPENING_L)
        .translate((opening_x_center, OUTER_DEPTH / 2 - 0.05, opening_z_center))
    )

    # 内层切割: Y=1 向内 2mm (到 Y=3, 打穿)
    cut_inner = (
        cq.Workplane("XY")
        .box(INNER_OPENING_W, INNER_DEPTH + 0.1, INNER_OPENING_L)
        .translate((opening_x_center, OUTER_DEPTH + INNER_DEPTH / 2, opening_z_center))
    )

    result = shell.cut(cut_outer).cut(cut_inner)

    # ============================================================
    # 支撑: 内层开口 (66×32) 的 4 个角, 内侧, 共 4 个
    # ============================================================
    # 从内壁伸入内层开口区域, 屏幕/PCB 搁在支撑上
    # 伸出3mm (进入开口) + 2mm (锚固在壁体内), 5mm宽 (Z方向), 2mm厚 (Y方向)

    # 内层开口边界
    inner_x_start = opening_x_center - INNER_OPENING_W / 2   # = -21
    inner_x_end = opening_x_center + INNER_OPENING_W / 2     # = 11
    inner_z_start = opening_z_center - INNER_OPENING_L / 2   # = 2
    inner_z_end = opening_z_center + INNER_OPENING_L / 2     # = 68

    # 支撑 Y 位置: 紧贴内壁面 (Y=WALL=3), 向内腔延伸
    # Y 从 WALL 到 WALL + SUPPORT_THICK = 3 到 5mm
    support_y_center = WALL + SUPPORT_THICK / 2  # = 4.0

    support_total_x = SUPPORT_PROTRUDE + SUPPORT_ANCHOR  # 5mm

    if narrow_supports:
        NARROW_PROTRUDE = p["NARROW_PROTRUDE"]
        NARROW_ANCHOR = p["NARROW_ANCHOR"]

        # X+ 侧 (15mm 宽, 空间充裕): 3mm 伸出 + 2mm 锚固 = 5mm
        # X- 侧 (5mm 窄边, 壁薄): 2mm 伸出 + 2mm 锚固 = 4mm

        # 4 个支撑: 两条长边 (X方向) × 两端 (Z方向)
        # 每个支撑存 (x_center, z_pos, total_x)
        support_specs = []
        for z_pos in [inner_z_start + SUPPORT_W / 2,    # Z ≈ 4.5
                      inner_z_end - SUPPORT_W / 2]:       # Z ≈ 65.5
            # X+ 侧 (15mm 宽边): 5mm 总宽
            total_x = SUPPORT_PROTRUDE + SUPPORT_ANCHOR
            sx = inner_x_end - SUPPORT_PROTRUDE / 2 + SUPPORT_ANCHOR / 2
            support_specs.append((sx, z_pos, total_x))

            # X- 侧 (5mm 窄边): 4mm 总宽
            total_x_narrow = NARROW_PROTRUDE + NARROW_ANCHOR
            sx = inner_x_start + NARROW_PROTRUDE / 2 - NARROW_ANCHOR / 2
            support_specs.append((sx, z_pos, total_x_narrow))

        for sx, sz, total_x in support_specs:
            support = (
                cq.Workplane("XY")
                .box(total_x, SUPPORT_THICK, SUPPORT_W)
                .translate((sx, support_y_center, sz))
            )
            result = result.union(support)
    else:
        # 4 个支撑: 两条长边 (X方向) × 两端 (Z方向)
        support_positions = []
        for z_pos in [inner_z_start + SUPPORT_W / 2,    # Z ≈ 4.5
                      inner_z_end - SUPPORT_W / 2]:       # Z ≈ 65.5
            # X+ 侧长边 (inner_x_end=11): 向开口内伸
            sx = inner_x_end - SUPPORT_PROTRUDE / 2 + SUPPORT_ANCHOR / 2
            support_positions.append((sx, z_pos))

            # X- 侧长边 (inner_x_start=-21): 向开口内伸
            sx = inner_x_start + SUPPORT_PROTRUDE / 2 - SUPPORT_ANCHOR / 2
            support_positions.append((sx, z_pos))

        for sx, sz in support_positions:
            support = (
                cq.Workplane("XY")
                .box(support_total_x, SUPPORT_THICK, SUPPORT_W)
                .translate((sx, support_y_center, sz))
            )
            result = result.union(support)

    # ============================================================
    # 右斜面 4 个圆孔 (Pi Zero 安装孔, 23×58mm 矩形排列)
    # ============================================================
    # 右斜面: 从 (25, 0) 到 (0, TRI_H), 与开口 (底面偏左) 距离最远
    #
    # 斜面参数:
    #   中心点 (截面): (12.5, TRI_H/2)
    #   Z 方向中心: LENGTH/2
    #   法线 (外向): (TRI_H/SIDE, 0.5, 0) = (0.866, 0.5, 0)
    #   边方向 (沿斜边): (-0.5, 0.866, 0)

    # 斜面中心
    face_cx = (SIDE / 2 + 0) / 2    # = 12.5
    face_cy = (0 + TRI_H) / 2       # = 21.65
    face_cz = LENGTH / 2            # = 35

    # 斜边方向 (单位向量, 从 (25,0) 指向 (0, TRI_H))
    edge_dx = -0.5          # = -25/50
    edge_dy = TRI_H / SIDE  # = 43.3/50 = 0.866

    # 法线方向 (单位向量, 向外)
    norm_dx = TRI_H / SIDE  # = 0.866
    norm_dy = 0.5

    # 4 个孔位
    hole_positions = []
    for edge_off in [-HOLE_SPACING_SHORT / 2 + HOLE_OFFSET_SHORT, HOLE_SPACING_SHORT / 2 + HOLE_OFFSET_SHORT]:
        for z_off in [-HOLE_SPACING_LONG / 2 + HOLE_OFFSET_LONG, HOLE_SPACING_LONG / 2 + HOLE_OFFSET_LONG]:
            hx = face_cx + edge_off * edge_dx
            hy = face_cy + edge_off * edge_dy
            hz = face_cz + z_off
            hole_positions.append((hx, hy, hz))

    # 钻孔: 沿法线方向创建圆柱体, 切穿斜面壁
    for hx, hy, hz in hole_positions:
        origin = Vector(hx, hy, hz)
        normal = Vector(norm_dx, norm_dy, 0)
        z_dir = Vector(0, 0, 1)

        plane = Plane(origin=origin, normal=normal, xDir=z_dir)
        hole_cyl = (
            cq.Workplane(plane)
            .circle(HOLE_D / 2)
            .extrude(WALL + 2)         # 向外
        )
        hole_cyl2 = (
            cq.Workplane(plane)
            .circle(HOLE_D / 2)
            .extrude(-(WALL + 2))      # 向内
        )
        result = result.cut(hole_cyl).cut(hole_cyl2)

    return result


def build_model(p=PARAMS):
    body = build_prism_unsplit_shell(p, fillet_outer=False, narrow_supports=False)
    return {
        "name": MODEL_NAME,
        "assembly": None,
        "parts": {"body": body},
    }


if __name__ == "__main__":
    m = build_model()
    SIDE = PARAMS["SIDE"]
    LENGTH = PARAMS["LENGTH"]
    WALL = PARAMS["WALL"]
    OPENING_W = PARAMS["OPENING_W"]
    OPENING_L = PARAMS["OPENING_L"]
    OPENING_SHORT_OFFSET = PARAMS["OPENING_SHORT_OFFSET"]
    TRI_H = SIDE * math.sqrt(3) / 2
    inradius = SIDE * math.sqrt(3) / 6
    inner_inradius = inradius - WALL
    inner_side = inner_inradius * 2 * math.sqrt(3)
    print(f"=== 三棱柱外壳 ===")
    print(f"  正三角形边长: {SIDE}mm")
    print(f"  棱柱长度: {LENGTH}mm")
    print(f"  壁厚: {WALL}mm")
    print(f"  三角形高: {TRI_H:.1f}mm")
    print(f"  内腔三角形边长: {inner_side:.1f}mm")
    print(f"  开口: {OPENING_W}x{OPENING_L}mm (底面)")
    print(f"  开口位置 (短边): {OPENING_SHORT_OFFSET}mm + {OPENING_W}mm + {SIDE - OPENING_SHORT_OFFSET - OPENING_W}mm")
    print(f"  开口位置 (长边): {(LENGTH - OPENING_L)/2:.0f}mm + {OPENING_L}mm + {(LENGTH - OPENING_L)/2:.0f}mm (居中)")
    print(f"\n  build_model parts: {list(m['parts'].keys())}")
