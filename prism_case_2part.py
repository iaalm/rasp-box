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
  ./.venv311/bin/python scripts/check_connectivity.py --model prism_case_2part
  ./.venv311/bin/python scripts/export_model.py --model prism_case_2part
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

from prism_case import build_prism_unsplit_shell


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
    "NARROW_PROTRUDE": 3.0,
    "NARROW_ANCHOR": 1.0,
    "HOLE_D": 3.0,
    "HOLE_SPACING_SHORT": 23.0,
    "HOLE_SPACING_LONG": 58.0,
    "FILLET_R": 0.25,
    "TAB_THICK": 8.0,
    "TAB_ARM": 1.0,
    "TAB_ANCHOR": 4.0,
}

MODEL_NAME = "prism_case_2part"


def build_model(p=PARAMS):
    SIDE = p["SIDE"]
    LENGTH = p["LENGTH"]
    WALL = p["WALL"]
    OPENING_W = p["OPENING_W"]
    OPENING_L = p["OPENING_L"]
    OPENING_SHORT_OFFSET = p["OPENING_SHORT_OFFSET"]
    TAB_THICK = p["TAB_THICK"]
    TAB_ARM = p["TAB_ARM"]

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
    # 外棱柱 (所有外棱倒圆 R=0.25mm, 即直径 0.5mm)
    # 内棱柱、掏空、阶梯开口、支撑、斜面孔：实现见 prism_case.build_prism_unsplit_shell
    FILLET_R = p["FILLET_R"]
    result = build_prism_unsplit_shell(
        p,
        fillet_outer=True,
        narrow_supports=True,
        fillet_r=FILLET_R,
    )

    # ============================================================
    # 从中间切开 (Z=LENGTH/2, 平行于三角形截面)
    # ============================================================

    SPLIT_Z = LENGTH / 2  # = 35mm

    # 前半 (Z=0 到 Z=35)
    cut_front = (
        cq.Workplane("XY")
        .box(SIDE + 10, TRI_H + 10, LENGTH)
        .translate((0, TRI_H / 2, SPLIT_Z + LENGTH / 2))
    )
    half_front = result.cut(cut_front)

    # front 内侧三角形突起 (切面 Z=35 处, 三个角各一个)
    # 从 Z=35 伸出 1mm 到 Z=36, 插入后半做定位加强

    # 内三角形三个顶点
    inner_corners = [
        (-inner_side / 2, inner_bottom_y),           # 左下
        (inner_side / 2, inner_bottom_y),            # 右下
        (0, inner_bottom_y + inner_tri_h),           # 顶
    ]

    for i, (cx, cy) in enumerate(inner_corners):
        # 相邻两个顶点
        n1 = inner_corners[(i + 1) % 3]
        n2 = inner_corners[(i + 2) % 3]

        # 从角点沿两条边方向各延伸 TAB_ARM
        def arm_point(corner, neighbor):
            dx = neighbor[0] - corner[0]
            dy = neighbor[1] - corner[1]
            dist = math.sqrt(dx * dx + dy * dy)
            return (corner[0] + dx / dist * TAB_ARM,
                    corner[1] + dy / dist * TAB_ARM)

        p1 = (cx, cy)
        p2 = arm_point((cx, cy), n1)
        p3 = arm_point((cx, cy), n2)

        # 4mm 锚固在 front 内 (Z=31~35), 4mm 伸出 (Z=35~39)
        TAB_ANCHOR = p["TAB_ANCHOR"]
        TAB_EXTEND = TAB_THICK - TAB_ANCHOR  # = 4.0

        tab = (
            cq.Workplane("XY")
            .transformed(offset=(0, 0, SPLIT_Z - TAB_ANCHOR))
            .moveTo(p1[0], p1[1])
            .lineTo(p2[0], p2[1])
            .lineTo(p3[0], p3[1])
            .close()
            .extrude(TAB_THICK)
        )
        half_front = half_front.union(tab)

    # 后半 (Z=35 到 Z=70)
    cut_back = (
        cq.Workplane("XY")
        .box(SIDE + 10, TRI_H + 10, LENGTH)
        .translate((0, TRI_H / 2, SPLIT_Z - LENGTH / 2))
    )
    half_back = result.cut(cut_back)

    return {
        "name": MODEL_NAME,
        "assembly": None,
        "parts": {
            "full": result,
            "front": half_front,
            "back": half_back,
        },
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
    SPLIT_Z = LENGTH / 2
    print(f"=== 三棱柱外壳 ===")
    print(f"  正三角形边长: {SIDE}mm")
    print(f"  棱柱长度: {LENGTH}mm")
    print(f"  壁厚: {WALL}mm")
    print(f"  三角形高: {TRI_H:.1f}mm")
    print(f"  内腔三角形边长: {inner_side:.1f}mm")
    print(f"  开口: {OPENING_W}x{OPENING_L}mm (底面)")
    print(f"  开口位置 (短边): {OPENING_SHORT_OFFSET}mm + {OPENING_W}mm + {SIDE - OPENING_SHORT_OFFSET - OPENING_W}mm")
    print(f"  开口位置 (长边): {(LENGTH - OPENING_L)/2:.0f}mm + {OPENING_L}mm + {(LENGTH - OPENING_L)/2:.0f}mm (居中)")
    print(f"  切割: Z={SPLIT_Z}mm 处分为前后两半")
    print(f"\n  build_model parts: {list(m['parts'].keys())}")
