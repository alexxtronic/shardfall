"""Ambron structures for Shardfall: the seven buildings of the robot race, built by script.

Style (docs/ART_SPEC.md, art/ref/ambron_style_reference.png): chunky, rounded, toy-like sci-fi. Cream
plates, warm gold trim, graphite housings and joints, glowing cyan lenses, big soft bevels. Every
building shares the same base language (a graphite plinth with a gold lip and a cream tier, cyan studs
on its corners) and borrows the Harvester drone's parts: round "ear" lens pods (cream disc, gold rim,
graphite ring, cyan lens), tall gold ear fins with a cyan inner strip, graphite joints with cyan caps.

    Blender --background --factory-startup --python-exit-code 1 --python art/ambron_buildings/build.py -- <id|all> [options]

Options:
    --round NAME   review renders go to review/NAME/ (default "latest")
    --fast         flat colours, no bake and no export: a quick geometry check (renders to review/fast/)
    lineup         instead of building, import every exported Ambron GLB and render them side by side
    AMBRON_PARTS=1 (environment) prints the triangle count per part type, for budget work

Pipeline per building: parts are built as separate objects with bevel + weighted-normal modifiers in a
small set of flat source materials (src_cream, src_gold, src_graphite ...). They are applied and joined;
the cream/gold/graphite faces are unwrapped (Smart UV) and baked in Cycles to one colour texture (flat
colour x ambient occlusion, with a ground plane for contact shadow) plus one metallic-roughness texture,
so the body becomes a single material, `ambron_body`. Glowing faces keep a `glow...` material and the
accent strips keep `team` (light grey; the game recolours it). Floating parts (the Relay's crystal, the
Spire's halo) are split off as their own objects with their origin at their own centre.

Outputs: assets/models/<id>.glb, assets/icons/<id>.png (256 px, transparent), review renders in
art/ambron_buildings/review/<round>/, numbers in art/ambron_buildings/stats.json.
Units are metres, Z up here (+Y up in the GLB), front faces -Y here (+Z in Godot), origin at the
centre of the footprint on the ground.
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "icons")
REVIEW = os.path.join(HERE, "review")
CACHE = os.path.join(HERE, "cache")          # baked textures (gitignored; they are packed in the GLB)
STATS = os.path.join(HERE, "stats.json")

# --- palette ---------------------------------------------------------------------------------------
# key: (hex sRGB, roughness, metallic). Baked into ambron_body; the bake classifies each texel back
# to its nearest entry to write the metallic-roughness texture.
PAL = {
    "cream":     ("#EDE3CF", 0.45, 0.0),
    "cream2":    ("#DDD0B6", 0.50, 0.0),    # secondary cream for tiers and back plates
    "gold":      ("#E0A33A", 0.36, 0.25),
    "gold2":     ("#B9771E", 0.42, 0.25),   # darker gold for hazard stripes and braces
    "graphite":  ("#2B2F36", 0.52, 0.12),
    "graphite2": ("#3E444E", 0.48, 0.18),   # lighter graphite for slats and louvres
    "slime":     ("#17121F", 0.22, 0.0),    # black void slime inside the Void Machine's tank
}
GLOWS = {
    "glow":         ("#5FE3FF", 1.4),       # Ambron cyan
    "glow_core":    ("#8A3CFF", 1.5),       # violet: void slime energy in the Void Machine
    "glow_furnace": ("#FF8A2A", 1.5),       # furnace heat in the Mech Forge
}
TEAM_HEX = "#C8CCD2"

BUILDINGS = ["ambron_citadel", "ambron_relay", "ambron_void_machine", "ambron_assembly",
             "ambron_forge", "ambron_skyport", "ambron_spire"]
FOOTPRINT = {"ambron_citadel": 5, "ambron_relay": 2, "ambron_void_machine": 3, "ambron_assembly": 3,
             "ambron_forge": 3, "ambron_skyport": 3, "ambron_spire": 4}
FLOATS = {"ambron_relay": {1: "ambron_relay_crystal"}, "ambron_spire": {1: "ambron_spire_halo"}}
TEX_RES = {"ambron_relay": 512}             # everything else 1024

PARTS = []
GROUP = 0
MATS = {}


def hex_lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def lin_srgb(a):
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)


# --- scene and materials ---------------------------------------------------------------------------

def reset():
    global GROUP
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PARTS.clear()
    MATS.clear()
    GROUP = 0
    for k, (hx, rough, metal) in PAL.items():
        m = bpy.data.materials.new("src_" + k)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*hex_lin(hx), 1.0)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        MATS[k] = m
    for k, (hx, strength) in GLOWS.items():
        m = bpy.data.materials.new(k)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*[c * 0.3 for c in hex_lin(hx)], 1.0)   # the light is the emission
        b.inputs["Emission Color"].default_value = (*hex_lin(hx), 1.0)
        b.inputs["Emission Strength"].default_value = strength
        b.inputs["Roughness"].default_value = 0.3
        MATS[k] = m
    m = bpy.data.materials.new("team")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hex_lin(TEAM_HEX), 1.0)
    b.inputs["Roughness"].default_value = 0.45
    MATS["team"] = m


def M(key):
    return MATS[key]


def group(k):
    """Parts built after this call belong to floating group k (0 = the building itself)."""
    global GROUP
    GROUP = k


# --- geometry helpers ------------------------------------------------------------------------------

def E(rot):
    """Rotation as an Euler: degrees tuple, Euler, Quaternion or Matrix."""
    if isinstance(rot, Euler):
        return rot
    if isinstance(rot, Quaternion):
        return rot.to_euler()
    if isinstance(rot, Matrix):
        return rot.to_euler()
    return Euler([math.radians(a) for a in rot])


def aim(direction):
    """Euler that turns local +Z toward direction."""
    return Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized()).to_euler()


def rz(deg):
    return Matrix.Rotation(math.radians(deg), 3, "Z")


def mods(ob, bevel=0.0, seg=3, angle=30, shade="wn", split=35):
    me = ob.data
    me.polygons.foreach_set("use_smooth", [shade != "flat"] * len(me.polygons))
    if bevel > 0.0:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = seg
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(angle)
        b.use_clamp_overlap = True
        b.miter_outer = "MITER_ARC"
    if shade == "wn":
        w = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        w.mode = "FACE_AREA"
        w.keep_sharp = True
        w.weight = 50
    elif shade == "split":
        s = ob.modifiers.new("split", "EDGE_SPLIT")
        s.split_angle = math.radians(split)
    return ob


def _mk(name, bm, mat, loc=(0, 0, 0), rot=(0, 0, 0)):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    ob.location = loc
    ob.rotation_euler = E(rot)
    ob["fgroup"] = GROUP
    PARTS.append(ob)
    return ob


def box(name, size, loc, mat, bevel=0.05, seg=2, rot=(0, 0, 0), angle=30, shade="wn"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    ob = _mk(name, bm, mat, loc, rot)
    return mods(ob, min(bevel, min(size) * 0.48), seg, angle, shade)


def boxz(name, sx, sy, z0, z1, x, y, mat, **kw):
    return box(name, (sx, sy, z1 - z0), (x, y, (z0 + z1) / 2), mat, **kw)


def strut(name, p0, p1, w, h, mat, bevel=0.03, seg=2, extend=0.0):
    """A box running from p0 to p1 (w x h in section)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length + 2 * extend
    return box(name, (w, h, L), (p0 + p1) / 2, mat, bevel=bevel, seg=seg, rot=aim(d))


def cyl(name, r1, r2, depth, loc, mat, n=32, rot=(0, 0, 0), bevel=0.0, seg=2, angle=40, shade="wn"):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r1, radius2=r2, depth=depth)
    ob = _mk(name, bm, mat, loc, rot)
    if bevel > 0.0:
        bevel = min(bevel, depth * 0.48, min(r1, r2 if r2 > 0 else r1) * 0.48)
    return mods(ob, bevel, seg, angle, shade if bevel > 0 else ("split" if shade == "wn" else shade), split=50)


def cylz(name, r1, r2, z0, z1, x, y, mat, **kw):
    return cyl(name, r1, r2, z1 - z0, (x, y, (z0 + z1) / 2), mat, **kw)


def rod(name, p0, p1, r, mat, n=16, bevel=0.0, seg=2):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    return cyl(name, r, r, d.length, (p0 + p1) / 2, mat, n=n, rot=aim(d), bevel=bevel, seg=seg)


def lathe(name, prof, mat, n=48, loc=(0, 0, 0), rot=(0, 0, 0), closed=False, a0=0.0, a1=None,
          bevel=0.0, seg=2, angle=30, shade=None, split=35):
    """Spins a profile [(r, z), ...] round Z. A closed profile should run counter-clockwise with r to
    the right and z up. a0/a1 (degrees) make a sector (closed profiles only), capped at both ends."""
    bm = bmesh.new()
    full = a1 is None
    count = n if full else n + 1
    span = 2 * math.pi if full else math.radians(a1 - a0)
    start = 0.0 if full else math.radians(a0)
    poles, rings = {}, []
    for i in range(count):
        a = start + span * i / n
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for j, (r, z) in enumerate(prof):
            if r < 1e-6:
                if j not in poles:
                    poles[j] = bm.verts.new((0.0, 0.0, z))
                ring.append(poles[j])
            else:
                ring.append(bm.verts.new((r * ca, r * sa, z)))
        rings.append(ring)
    m = len(prof)
    for i in range(n):
        A = rings[i]
        B = rings[(i + 1) % count] if full else rings[i + 1]
        for j in range(m if closed else m - 1):
            j2 = (j + 1) % m
            vs = []
            for v in (A[j], B[j], B[j2], A[j2]):
                if v not in vs:
                    vs.append(v)
            if len(vs) >= 3:
                bm.faces.new(vs)
    if not full and closed:
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])
    if full and not closed:
        if prof[0][0] > 1e-6:
            bm.faces.new([rings[i][0] for i in range(n)])
        if prof[-1][0] > 1e-6:
            bm.faces.new([rings[i][-1] for i in range(n)])
    ob = _mk(name, bm, mat, loc, rot)
    if shade is None:
        shade = "wn" if bevel > 0 else "split"
    return mods(ob, bevel, seg, angle, shade, split)


def torus(name, R, r, loc, mat, rot=(0, 0, 0), major=48, minor=8, a0=0.0, a1=None):
    prof = [(R + r * math.cos(2 * math.pi * k / minor), r * math.sin(2 * math.pi * k / minor)) for k in range(minor)]
    return lathe(name, prof, mat, n=major, loc=loc, rot=rot, closed=True, a0=a0, a1=a1, shade="smooth")


def ring(name, r0, r1, z0, z1, mat, n=48, loc=(0, 0, 0), bevel=0.0, a0=0.0, a1=None, seg=2):
    """A flat band: annulus from r0 to r1, z0 to z1 (or a sector of one)."""
    prof = [(r1, z0), (r1, z1), (r0, z1), (r0, z0)]
    return lathe(name, prof, mat, n=n, loc=loc, closed=True, a0=a0, a1=a1, bevel=bevel, seg=seg)


def _extrude(name, pa, off, mat, loc, rot, bevel, seg, angle, shade):
    bm = bmesh.new()
    A = [bm.verts.new(p) for p in pa]
    B = [bm.verts.new(Vector(p) + Vector(off)) for p in pa]
    n = len(A)
    bm.faces.new(A)
    bm.faces.new(list(reversed(B)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((A[i], A[j], B[j], B[i]))
    ob = _mk(name, bm, mat, loc, rot)
    return mods(ob, bevel, seg, angle, shade)


def prism(name, pts, z0, z1, mat, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.04, seg=3, angle=30, shade="wn"):
    """A polygon drawn in XY, from z0 to z1."""
    return _extrude(name, [(x, y, z0) for x, y in pts], (0, 0, z1 - z0), mat, loc, rot, bevel, seg, angle, shade)


def slab(name, pts, t, mat, plane="xz", loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.04, seg=3, angle=30, shade="wn"):
    """A polygon drawn in a vertical plane, given thickness t centred on it. plane 'xz': (u, v) = (x, z),
    thickness along Y. plane 'yz': (u, v) = (y, z), thickness along X."""
    if plane == "xz":
        pa = [(u, -t / 2, v) for u, v in pts]
        off = (0, t, 0)
    else:
        pa = [(-t / 2, u, v) for u, v in pts]
        off = (t, 0, 0)
    return _extrude(name, pa, off, mat, loc, rot, bevel, seg, angle, shade)


def pod(name, size, loc, mat, boxy=0.55, u=28, v=16, rot=(0, 0, 0)):
    """A squared-off ball (superellipsoid): the drone's head shape."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    for vert in bm.verts:
        c = [math.copysign(abs(a) ** boxy, a) for a in vert.co]
        vert.co = Vector((c[0] * size[0] / 2, c[1] * size[1] / 2, c[2] * size[2] / 2))
    ob = _mk(name, bm, mat, loc, rot)
    return mods(ob, shade="smooth")


def pipe(name, pts, r, mat, bevel_res=1, res=5):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.bevel_depth = r
    cu.bevel_resolution = bevel_res
    cu.use_fill_caps = True
    cu.resolution_u = res
    tmp = bpy.data.objects.new(name + "_curve", cu)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bpy.data.meshes.remove(me)
    ob = _mk(name, bm, mat)
    return mods(ob, shade="split", split=60)


def octa(h, c):
    """A square of half-size h with its corners chamfered by c, counter-clockwise."""
    return [(h - c, -h), (h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c), (-h + c, -h)]


# --- shared Ambron kit -----------------------------------------------------------------------------

def base(h, c, z1=0.2, tier_h=0.14, studs=True):
    """Graphite plinth, gold lip, cream tier; cyan studs on the four chamfered corners. Returns the
    tier's top height."""
    prism("plinth", octa(h, c), 0.0, z1, M("graphite"), bevel=0.06, seg=2)
    prism("plinth_trim", octa(h - 0.06, c * 0.96), z1 - 0.02, z1 + 0.07, M("gold"), bevel=0.025, seg=2)
    top = z1 + 0.07 + tier_h
    prism("tier", octa(h - 0.15, c * 0.92), z1 + 0.05, top, M("cream2"), bevel=0.05, seg=2)
    if studs:
        d = (2 * h - c) / math.sqrt(2)
        for k in range(4):
            a = math.radians(45 + 90 * k)
            dv = Vector((math.cos(a), math.sin(a), 0))
            cyl("stud", 0.075, 0.075, 0.05, dv * (d + 0.005) + Vector((0, 0, z1 * 0.5)), M("glow"), n=12,
                rot=aim(dv))
    return top


def lens_pod(name, c, d, R, depth=None):
    """The drone's ear disc: cream shell, gold rim, graphite ring and a cyan lens, facing d."""
    c, d = Vector(c), Vector(d).normalized()
    depth = depth or 0.42 * R
    rot = aim(d)
    n = 24 if R > 0.4 else (20 if R > 0.25 else 16)
    cyl(name + "_shell", R, R * 0.9, depth, c, M("cream"), n=n, rot=rot, bevel=R * 0.2, seg=2)
    face = c + d * depth / 2
    torus(name + "_rim", R * 0.8, R * 0.075, face - d * R * 0.02, M("gold"), rot=rot, major=n, minor=4)
    cyl(name + "_ring", R * 0.64, R * 0.6, R * 0.16, face + d * R * 0.03, M("graphite"), n=n, rot=rot,
        bevel=R * 0.05, seg=1)
    cyl(name + "_lens", R * 0.44, R * 0.4, R * 0.1, face + d * R * 0.1, M("glow"), n=n, rot=rot,
        bevel=R * 0.035, seg=1)


def ear_fin(name, base_pt, h, w, t, side, splay=12, strip=True):
    """A tall gold ear fin like the drone's: a blade in the YZ plane that sweeps back to a chisel tip,
    leaning outward by splay degrees, with a cyan strip on its inner face."""
    pts = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.62, h * 0.72), (w * 0.5, h), (w * 0.18, h * 0.96),
           (-w * 0.32, h * 0.38)]
    rot = Matrix.Rotation(math.radians(splay * side), 3, "Y")
    slab(name, pts, t, M("gold"), plane="yz", loc=base_pt, rot=rot, bevel=t * 0.42, seg=3)
    if strip:
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        inner = [(cx + (u - cx) * 0.58, cz + (v - cz) * 0.62 + h * 0.04) for u, v in pts]
        off = rot @ Vector((-side * (t * 0.5 + 0.004), 0, 0))
        slab(name + "_strip", inner, 0.03, M("glow"), plane="yz", loc=Vector(base_pt) + off, rot=rot,
             bevel=0.012, seg=1)


def stud(name, c, d, r, mat=None, collar=True):
    """A small cyan light set in a graphite collar, facing d."""
    c, d = Vector(c), Vector(d).normalized()
    if collar:
        cyl(name + "_collar", r * 1.5, r * 1.4, r * 0.7, c, M("graphite"), n=12, rot=aim(d), bevel=r * 0.25, seg=1)
    cyl(name, r, r * 0.9, r * 0.6, c + d * r * 0.35, mat or M("glow"), n=12, rot=aim(d), bevel=r * 0.2, seg=1)


def joint(name, c, axis, r, L, lens=True):
    """A graphite hinge cylinder along axis with cyan caps, like the drone's elbows."""
    c, axis = Vector(c), Vector(axis).normalized()
    cyl(name, r, r, L, c, M("graphite"), n=18, rot=aim(axis), bevel=r * 0.25, seg=2)
    if lens:
        for s in (-1, 1):
            cyl(name + "_cap", r * 0.55, r * 0.5, 0.03, c + axis * s * (L / 2 + 0.008), M("glow"), n=12,
                rot=aim(axis * s))


def chevron_strip(name, x0, x1, z0, z1, y, n, colours=("gold", "graphite"), slant=30):
    """Hazard trim on a front face (normal -Y): alternating slanted bars between x0 and x1."""
    w = (x1 - x0) / n
    for i in range(n):
        x = x0 + w * (i + 0.5)
        box(f"{name}_{i}", (w * 0.98, 0.05, (z1 - z0) * 1.0), (x, y, (z0 + z1) / 2), M(colours[i % 2]),
            bevel=0.012, seg=1, rot=(0, slant, 0))


# --- the buildings ---------------------------------------------------------------------------------

def build_citadel():
    """Main base: a domed cream command hub on a graphite octagon, a ring of cyan light round its
    shoulder, gold petals on the dome, a cyan beacon on top flanked by two big ear fins, the drone's
    lens pods on its flanks, and a docking bay mouth at the front where Harvesters drop crystals."""
    H = 2.35
    Z = base(H, 0.78, z1=0.30, tier_h=0.22)                     # deck top 0.59
    # the round core
    ring("core_foot", 1.2, 1.84, Z - 0.02, Z + 0.17, M("graphite"), n=28, a0=298, a1=602, bevel=0.05, seg=1)
    torus("core_foot_trim", 1.78, 0.05, (0, 0, Z + 0.18), M("gold"), major=34, minor=4, a0=299, a1=601)
    cylz("core_wall", 1.62, 1.62, Z + 0.15, 2.08, 0, 0, M("cream"), n=44)
    cylz("core_channel", 1.57, 1.57, 2.0, 2.42, 0, 0, M("graphite"), n=44)
    ring("light_ring", 1.50, 1.655, 2.15, 2.27, M("glow"), n=44)
    torus("trim_lo", 1.62, 0.06, (0, 0, 2.07), M("gold"), major=40, minor=4)
    torus("trim_hi", 1.60, 0.06, (0, 0, 2.36), M("gold"), major=40, minor=4)
    # the dome: an ellipse from the channel up to the beacon collar
    R0, z0, hd = 1.6, 2.38, 1.18
    dome = [(0.0, z0)] + [(R0 * math.cos(math.radians(a)), z0 + hd * math.sin(math.radians(a)) ** 0.92)
                          for a in range(0, 91, 9)]
    dome[-1] = (0.0, dome[-1][1])
    lathe("dome", dome, M("cream"), n=40, split=60)
    # gold petals on the dome, offset a little proud of its surface
    def dome_pt(a, off):
        r = R0 * math.cos(math.radians(a)) + off * math.cos(math.radians(a))
        z = z0 + hd * math.sin(math.radians(a)) ** 0.92 + off * math.sin(math.radians(a))
        return r, z
    outer = [dome_pt(a, 0.045) for a in range(8, 60, 12)]
    inner = [dome_pt(a, -0.03) for a in range(56, 7, -12)]
    for k in range(4):
        ac = 45 + 90 * k
        lathe("petal", outer + inner, M("gold"), n=6, closed=True, a0=ac - 13, a1=ac + 13, bevel=0.035, seg=1)
    # beacon on top
    cylz("beacon_collar", 0.66, 0.6, 3.36, 3.64, 0, 0, M("graphite"), n=28, bevel=0.07)
    torus("beacon_trim", 0.6, 0.06, (0, 0, 3.64), M("gold"), major=28, minor=5)
    lathe("beacon", [(0.0, 3.58)] + [(0.46 * math.cos(math.radians(a)), 3.58 + 0.36 * math.sin(math.radians(a)))
                                     for a in range(0, 91, 15)], M("glow"), n=24, split=80)
    # two big ear fins, rising either side of the beacon
    for s in (-1, 1):
        boxz("fin_socket", 0.34, 0.7, 3.12, 3.5, s * 0.82, 0.12, M("graphite"), bevel=0.1)
        ear_fin("fin", (s * 0.84, 0.12, 3.36), 1.22, 0.78, 0.17, s, splay=13)
    # lens pods on the flanks (the drone's ears)
    for s in (-1, 1):
        lens_pod("pod", (s * 1.66, 0.25, 1.32), (s, 0, 0), 0.6)
    # the docking bay, front (-Y): a cream hood with a dark mouth, gold frame, cyan strip above
    yf, yb, yw = -2.0, -0.95, -1.6                               # hood front, hood back, mouth's back wall
    zt = 1.72                                                     # top of the opening
    for s in (-1, 1):
        boxz("bay_jamb", 0.52, yb - yf, Z - 0.02, 1.9, s * 0.97, (yf + yb) / 2, M("cream"), bevel=0.13, seg=3)
        boxz("bay_liner", 0.05, yw - yf, Z, zt, s * 0.725, (yf + yw) / 2, M("graphite"), bevel=0.01, seg=1)
        boxz("bay_frame", 0.12, 0.12, Z, zt + 0.08, s * 0.74, yf - 0.03, M("gold"), bevel=0.04, seg=2)
        boxz("bay_team", 0.13, 0.04, Z + 0.2, 1.6, s * 0.98, yf - 0.012, M("team"), bevel=0.015, seg=1)
    boxz("bay_lintel", 2.46, yb - yf, zt - 0.02, 2.12, 0, (yf + yb) / 2, M("cream"), bevel=0.12, seg=3)
    boxz("bay_frame_top", 1.6, 0.12, zt - 0.02, zt + 0.1, 0, yf - 0.03, M("gold"), bevel=0.04, seg=2)
    boxz("bay_ceiling", 1.42, yw - yf, zt - 0.05, zt, 0, (yf + yw) / 2, M("graphite"), bevel=0.01, seg=1)
    box("bay_strip", (1.3, 0.06, 0.08), (0, yf - 0.03, 1.97), M("glow"), bevel=0.025, seg=1)
    boxz("bay_back", 1.5, 0.16, Z, zt, 0, yw, M("graphite"), bevel=0.03)
    box("bay_intake", (1.0, 0.05, 0.1), (0, yw - 0.085, 1.28), M("glow"), bevel=0.02, seg=1)
    boxz("bay_hopper", 1.2, 0.16, Z, 0.92, 0, yw - 0.14, M("gold2"), bevel=0.04)
    boxz("bay_floor", 1.42, yw - yf, Z - 0.01, Z + 0.03, 0, (yf + yw) / 2, M("graphite2"), bevel=0.01, seg=1)
    # ramp down the front of the plinth into the bay
    slab("bay_ramp", [(-2.33, 0.0), (yf + 0.05, 0.0), (yf + 0.05, Z + 0.03), (-2.33, 0.34)], 1.36,
         M("graphite2"), plane="yz", bevel=0.03, seg=2)
    for s in (-1, 1):
        slab("ramp_rail", [(-2.32, 0.30), (yf + 0.05, Z + 0.0), (yf + 0.05, Z + 0.08), (-2.32, 0.39)], 0.1,
             M("gold"), plane="yz", loc=(s * 0.7, 0, 0), bevel=0.025, seg=2)
    # back module
    boxz("rear", 1.5, 0.95, Z - 0.02, 1.86, 0, 1.55, M("cream2"), bevel=0.16, seg=3)
    boxz("rear_band", 1.56, 1.0, 1.42, 1.56, 0, 1.55, M("gold"), bevel=0.04, seg=2)
    for i in range(3):
        boxz("rear_louvre", 1.0, 0.08, 0.8 + i * 0.17, 0.88 + i * 0.17, 0, 2.04, M("graphite"), bevel=0.02, seg=1)
    # corner pylons
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 1.62, sy * 1.62
            cylz("pylon", 0.21, 0.19, Z - 0.02, Z + 0.72, x, y, M("graphite"), n=14, bevel=0.05, seg=1)
            cylz("pylon_team", 0.215, 0.215, Z + 0.28, Z + 0.42, x, y, M("team"), n=14)
            cylz("pylon_band", 0.235, 0.235, Z + 0.7, Z + 0.78, x, y, M("gold"), n=14)
            cylz("pylon_cap", 0.25, 0.22, Z + 0.76, Z + 0.96, x, y, M("cream"), n=14, bevel=0.07, seg=1)
            lathe("pylon_lens", [(0.0, Z + 0.94)] + [(0.13 * math.cos(math.radians(a)), Z + 0.94 + 0.1 * math.sin(math.radians(a)))
                                                    for a in range(0, 91, 30)], M("glow"), n=12, loc=(x, y, 0), split=80)


def build_relay():
    """Supply: a slim cream obelisk with gold collars and cyan seams on a graphite base; four gold claws
    on top hold a floating cyan crystal (separate object, group 1)."""
    H = 0.85
    Z = base(H, 0.28, z1=0.2, tier_h=0.16)                      # 0.43
    z0, z1, w0, w1 = Z, 1.82, 0.30, 0.19
    q2 = math.sqrt(2)
    cyl("shaft", w0 * q2, w1 * q2, z1 - z0, (0, 0, (z0 + z1) / 2), M("cream"), n=4, rot=(0, 0, 45), bevel=0.07, seg=3)

    def hw(z):
        return w0 - (w0 - w1) * (z - z0) / (z1 - z0)

    def band(name, za, zb, mat, grow=0.03, flare=0.0):
        cyl(name, (hw(za) + grow) * q2, (hw(zb) + grow + flare) * q2, zb - za, (0, 0, (za + zb) / 2), mat, n=4,
            rot=(0, 0, 45), bevel=0.03, seg=2)
    band("collar_lo", z0 - 0.02, z0 + 0.18, M("gold"), grow=0.05)
    band("team_band", 1.08, 1.19, M("team"), grow=0.018)
    band("collar_hi", 1.66, 1.82, M("gold"), grow=0.03, flare=0.03)
    cyl("cap", 0.25 * q2, 0.17 * q2, 0.11, (0, 0, 1.875), M("graphite"), n=4, rot=(0, 0, 45), bevel=0.035, seg=2)
    # glowing seams down the middle of each face, tilted with the taper
    tilt = math.degrees(math.atan((w0 - w1) / (z1 - z0)))
    for k in range(4):
        R3 = rz(90 * k)
        rot = (R3 @ Matrix.Rotation(math.radians(-tilt), 3, "X")).to_euler()
        for za, zb in ((z0 + 0.24, 1.04), (1.23, 1.62)):
            zc = (za + zb) / 2
            box("seam", (0.06, 0.04, zb - za), R3 @ Vector((0, -(hw(zc) + 0.004), zc)), M("glow"), bevel=0.015,
                seg=1, rot=rot)
    # claws
    claw = [(0.08, 0.0), (0.2, 0.0), (0.32, 0.17), (0.31, 0.33), (0.25, 0.35), (0.21, 0.14)]
    for k in range(4):
        slab("claw", [(u, v + 1.8) for u, v in claw], 0.075, M("gold"), plane="xz", rot=(0, 0, 45 + 90 * k),
             bevel=0.03, seg=2)
    # small pylons on the tier corners
    for k in range(4):
        a = math.radians(45 + 90 * k)
        x, y = 0.665 * math.cos(a), 0.665 * math.sin(a)
        cylz("post", 0.06, 0.05, Z - 0.02, Z + 0.2, x, y, M("graphite"), n=12, bevel=0.015, seg=1)
        cylz("post_tip", 0.045, 0.03, Z + 0.2, Z + 0.26, x, y, M("glow"), n=12, bevel=0.01, seg=1)
    # the floating crystal
    group(1)
    lathe("crystal", [(0.0, 1.99), (0.21, 2.14), (0.21, 2.26), (0.0, 2.5)], M("glow"), n=6, shade="flat")
    group(0)


def build_void_machine():
    """Extractor over a 3x3 slime pile: a squat pump on four splayed stabiliser legs. A cream-armoured
    skirt covers the pile, a violet glowing tank shows black slime being drawn up through a front
    window, gold pipes climb to the pump head."""
    # skirt over the pile
    cylz("skirt_lip", 1.3, 1.27, 0.0, 0.2, 0, 0, M("graphite"), n=40, bevel=0.05)
    sk = [(1.25, 0.18), (1.2, 0.4), (1.06, 0.6), (0.84, 0.76)]
    lathe("skirt_under", [(0.0, 0.16)] + [(r - 0.05, z) for r, z in sk] + [(0.0, 0.76)], M("graphite"), n=40, split=50)
    shell = sk + [(r - 0.08, z) for r, z in reversed(sk)]
    for a0 in (0, 90, 180, 270):
        lathe("skirt_plate", shell, M("cream"), n=7, closed=True, a0=a0 - 33, a1=a0 + 33, bevel=0.035, seg=1)
    torus("skirt_trim", 0.84, 0.05, (0, 0, 0.77), M("gold"), major=36, minor=5)
    # the tank: a violet core behind cream armour, open at the front
    cylz("core", 0.68, 0.68, 0.74, 1.94, 0, 0, M("glow_core"), n=32)
    cylz("tank_lo", 0.86, 0.84, 0.72, 0.92, 0, 0, M("graphite"), n=36, bevel=0.05)
    cylz("tank_hi", 0.84, 0.86, 1.78, 1.98, 0, 0, M("graphite"), n=36, bevel=0.05)
    for a0, a1 in ((303, 391), (42, 138), (149, 237)):
        ring("armour", 0.72, 0.87, 0.9, 1.8, M("cream"), n=10, a0=a0, a1=a1, bevel=0.04, seg=1)
    for a in (37, 143):
        x, y = 0.86 * math.cos(math.radians(a)), 0.86 * math.sin(math.radians(a))
        boxz("armour_seam", 0.09, 0.09, 0.9, 1.8, x, y, M("gold"), bevel=0.03, seg=2, rot=(0, 0, a))
    for a0, a1 in ((308, 386), (154, 232)):
        ring("team_band", 0.86, 0.885, 1.28, 1.42, M("team"), n=8, a0=a0, a1=a1)
    # window mullions and slime blobs inside
    for a in (258, 282):
        x, y = 0.72 * math.cos(math.radians(a)), 0.72 * math.sin(math.radians(a))
        boxz("mullion", 0.06, 0.06, 0.9, 1.8, x, y, M("gold"), bevel=0.02, seg=1, rot=(0, 0, a))
    rng = np.random.default_rng(7)
    for i in range(7):
        a = math.radians(rng.uniform(247, 293))
        z = 0.99 + i * 0.1 + rng.uniform(-0.03, 0.03)
        r = rng.uniform(0.055, 0.095)
        pod("slime", (2 * r, 2 * r, 2.4 * r), (0.67 * math.cos(a), 0.67 * math.sin(a), z), M("slime"),
            boxy=1.0, u=8, v=6)
    # pump head
    lathe("head", [(0.0, 1.96), (0.88, 1.96), (0.88, 2.04), (0.8, 2.15), (0.58, 2.25), (0.0, 2.27)], M("cream"),
          n=36, bevel=0.03, seg=2)
    torus("head_trim", 0.87, 0.05, (0, 0, 1.99), M("gold"), major=36, minor=5)
    cylz("piston", 0.32, 0.3, 2.2, 2.44, 0, 0, M("graphite"), n=24, bevel=0.05)
    ring("piston_light", 0.28, 0.325, 2.3, 2.36, M("glow"), n=24)
    cylz("piston_cap", 0.24, 0.2, 2.42, 2.52, 0, 0, M("gold"), n=24, bevel=0.04)
    # gold pipes from the skirt up to the head
    for a in (0, 90, 180):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        pts = [(1.2, 0.28), (1.13, 0.9), (1.02, 1.75), (0.86, 2.06), (0.62, 2.16)]
        pipe("pipe", [(r * c, r * s, z) for r, z in pts], 0.065, M("gold"), res=4)
        cylz("pipe_collar", 0.11, 0.11, 0.5, 0.6, 1.17 * c, 1.17 * s, M("graphite"), n=12, bevel=0.03, seg=1)
    # four splayed legs
    for k in range(4):
        a = math.radians(45 + 90 * k)
        u = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-u.y, u.x, 0))
        hip = u * 0.92 + Vector((0, 0, 1.18))
        knee = u * 1.5 + Vector((0, 0, 1.0))
        foot = u * 1.58
        cyl("hip", 0.15, 0.15, 0.34, hip, M("graphite"), n=12, rot=aim(t), bevel=0.04, seg=1)
        strut("thigh", hip, knee, 0.27, 0.3, M("cream"), bevel=0.09, seg=2)
        strut("thigh_trim", hip + (knee - hip) * 0.3 + Vector((0, 0, 0.16)), knee + (hip - knee) * 0.2 + Vector((0, 0, 0.16)),
              0.12, 0.05, M("gold"), bevel=0.02, seg=1)
        cyl("knee", 0.14, 0.14, 0.36, knee, M("graphite"), n=14, rot=aim(t), bevel=0.035, seg=1)
        for sgn in (-1, 1):
            cyl("knee_cap", 0.075, 0.07, 0.03, knee + t * sgn * 0.188, M("glow"), n=10, rot=aim(t * sgn))
        rod("shin", knee, foot + Vector((0, 0, 0.1)), 0.075, M("graphite"), n=10)
        rod("shin_sleeve", knee + (foot - knee) * 0.08, knee + (foot - knee) * 0.5, 0.1, M("gold"), n=12, bevel=0.02, seg=1)
        cylz("foot", 0.22, 0.17, 0.0, 0.12, foot.x, foot.y, M("graphite"), n=14, bevel=0.04, seg=1)
        cylz("foot_band", 0.17, 0.15, 0.11, 0.17, foot.x, foot.y, M("gold"), n=14)
    # front sensor
    lens_pod("sensor", (0, -1.12, 0.47), (0, -1, 0.75), 0.2)


def vault_pts(half_w, wall_z, rise, z0, n=18, e=0.7):
    pts = [(-half_w, z0), (half_w, z0)]
    for i in range(n + 1):
        a = math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        pts.append((half_w * math.copysign(abs(c) ** e, c), wall_z + rise * abs(s) ** e))
    return pts


def build_assembly():
    """Infantry factory: a rounded cream hangar with gold ribs, a big gold-framed shutter door at the
    front under a cyan light strip, and a robotic crane arm on the roof."""
    H = 1.35
    Z = base(H, 0.32, z1=0.18, tier_h=0.12)                     # 0.37
    yf, yb = -1.0, 1.12
    slab("hall", vault_pts(1.15, 1.45, 0.75, Z - 0.02), yb - yf, M("cream"), plane="xz", loc=(0, (yf + yb) / 2, 0),
         bevel=0.17, seg=4)
    for y, mat, t in ((-0.4, "gold", 0.14), (0.08, "team", 0.1), (0.98, "gold", 0.14)):
        slab("rib", vault_pts(1.2, 1.47, 0.78, Z - 0.02), t, M(mat), plane="xz", loc=(0, y, 0), bevel=0.04, seg=2)
    # door
    dz0, dz1, dw = Z, 1.62, 1.5
    boxz("door", dw, 0.1, dz0, dz1, 0, yf - 0.02, M("graphite"), bevel=0.03)
    for i in range(6):
        z = dz0 + 0.14 + i * 0.2
        box("slat", (dw - 0.08, 0.05, 0.07), (0, yf - 0.08, z), M("graphite2"), bevel=0.02, seg=1)
    for s in (-1, 1):
        boxz("jamb", 0.14, 0.18, dz0 - 0.02, dz1 + 0.02, s * (dw / 2 + 0.07), yf - 0.05, M("gold"), bevel=0.045, seg=2)
    boxz("lintel", dw + 0.42, 0.2, dz1, dz1 + 0.22, 0, yf - 0.05, M("gold"), bevel=0.06, seg=2)
    box("door_light", (dw + 0.1, 0.06, 0.08), (0, yf - 0.17, dz1 + 0.11), M("glow"), bevel=0.025, seg=1)
    # lens pods on the flanks
    for s in (-1, 1):
        lens_pod("pod", (s * 1.16, 0.3, 0.98), (s, 0, 0), 0.32)
    # back vent
    boxz("vent", 1.2, 0.2, 0.62, 1.22, 0, yb + 0.06, M("graphite"), bevel=0.05)
    for i in range(3):
        box("louvre", (1.05, 0.06, 0.06), (0, yb + 0.17, 0.76 + i * 0.16), M("graphite2"), bevel=0.02, seg=1)
    # crane arm on the roof
    tx, ty = 0.0, 0.52
    cylz("crane_base", 0.4, 0.36, 2.1, 2.36, tx, ty, M("graphite"), n=24, bevel=0.06)
    torus("crane_trim", 0.37, 0.045, (tx, ty, 2.36), M("gold"), major=24, minor=5)
    sh = Vector((tx, ty, 2.56))
    el = Vector((tx, -0.02, 3.04))
    wr = Vector((tx, -0.84, 2.7))
    boxz("crane_yoke", 0.46, 0.34, 2.32, 2.62, tx, ty, M("cream"), bevel=0.1)
    joint("shoulder", sh, (1, 0, 0), 0.16, 0.56)
    strut("boom", sh, el, 0.3, 0.3, M("cream"), bevel=0.1, seg=3)
    strut("boom_trim", sh + (el - sh) * 0.25 + Vector((0, 0.1, 0.11)), sh + (el - sh) * 0.8 + Vector((0, 0.1, 0.11)),
          0.12, 0.06, M("gold"), bevel=0.02, seg=1)
    joint("elbow", el, (1, 0, 0), 0.15, 0.42)
    strut("forearm", el, wr, 0.22, 0.22, M("gold"), bevel=0.07, seg=2)
    joint("wrist", wr, (1, 0, 0), 0.1, 0.3, lens=False)
    boxz("claw_head", 0.32, 0.26, 2.46, 2.68, tx, wr.y, M("graphite"), bevel=0.06)
    cyl("claw_lens", 0.06, 0.06, 0.03, (tx, wr.y - 0.135, 2.57), M("glow"), n=12, rot=(90, 0, 0))
    for s in (-1, 1):
        strut("claw_finger", (tx + s * 0.11, wr.y, 2.5), (tx + s * 0.16, wr.y - 0.05, 2.3), 0.07, 0.1,
              M("gold"), bevel=0.025, seg=1)


def build_forge():
    """Vehicle factory: heavy and industrial. A wide shutter door over a ramp, framed in gold-and-
    graphite hazard stripes, exhaust stacks glowing with furnace heat, orange furnace vents in the
    walls, cyan lens lights on the flanks."""
    H = 1.35
    Z = base(H, 0.3, z1=0.18, tier_h=0.1)                       # 0.35
    yf = -0.78
    boxz("hall", 2.42, 1.98, Z - 0.02, 1.82, 0, 0.2, M("cream"), bevel=0.17, seg=4)
    boxz("hall_band", 2.48, 2.04, 1.62, 1.76, 0, 0.2, M("gold"), bevel=0.05, seg=2)
    boxz("upper", 1.96, 1.3, 1.76, 2.22, 0, 0.38, M("cream2"), bevel=0.13, seg=3)
    # brow over the door with hazard stripes
    slab("brow", [(-0.76, 1.42), (-0.76, 1.84), (-1.0, 1.72), (-1.04, 1.5)], 2.3, M("graphite"), plane="yz",
         bevel=0.04, seg=2)
    for i in range(11):
        x = -1.0 + i * 0.2
        box("hazard", (0.1, 0.04, 0.24), (x, -1.03, 1.61), M("gold2" if i % 2 == 0 else "gold"), bevel=0.012, seg=1,
            rot=(0, 35, 0))
    # wide door and ramp
    boxz("door", 1.9, 0.1, Z + 0.04, 1.42, 0, yf - 0.02, M("graphite"), bevel=0.03)
    for i in range(5):
        box("slat", (1.82, 0.05, 0.08), (0, yf - 0.08, Z + 0.2 + i * 0.22), M("graphite2"), bevel=0.02, seg=1)
    box("door_seam", (0.05, 0.05, 1.0), (0, yf - 0.09, 0.9), M("graphite"), bevel=0.015, seg=1)
    for s in (-1, 1):
        for i in range(6):
            boxz("jamb_hazard", 0.16, 0.12, Z + i * 0.18, Z + (i + 1) * 0.18 - 0.01, s * 1.04, yf - 0.06,
                 M("gold" if (i + (s > 0)) % 2 == 0 else "graphite"), bevel=0.025, seg=1)
    slab("ramp", [(yf - 0.02, 0.0), (yf - 0.02, Z + 0.05), (-1.34, 0.14), (-1.34, 0.0)], 1.84, M("graphite2"),
         plane="yz", bevel=0.03, seg=2)
    slope = math.degrees(math.atan2(Z + 0.05 - 0.14, 1.34 + (yf - 0.02)))
    for s in (-1, 1):
        slab("ramp_rail", [(yf - 0.02, Z + 0.03), (yf - 0.02, Z + 0.11), (-1.34, 0.2), (-1.34, 0.12)], 0.1,
             M("gold"), plane="yz", loc=(s * 0.95, 0, 0), bevel=0.025, seg=1)
    for i in range(3):
        t = (i + 0.5) / 3
        y = (yf - 0.02) + t * (-1.34 - (yf - 0.02))
        z = (Z + 0.05) + t * (0.14 - (Z + 0.05))
        box("ramp_stripe", (1.6, 0.08, 0.03), (0, y, z + 0.005), M("gold2"), bevel=0.01, seg=1, rot=(slope, 0, 0))
    # exhaust stacks
    for s in (-1, 1):
        x, y = s * 0.78, 0.72
        cylz("stack", 0.27, 0.23, 1.7, 3.0, x, y, M("graphite"), n=22, bevel=0.04)
        torus("stack_trim", 0.25, 0.04, (x, y, 2.42), M("gold"), major=22, minor=5)
        cylz("stack_team", 0.25, 0.245, 2.6, 2.74, x, y, M("team"), n=22)
        ring("stack_mouth", 0.16, 0.28, 2.98, 3.16, M("gold"), n=22, loc=(x, y, 0), bevel=0.03)
        cylz("stack_fire", 0.17, 0.17, 2.9, 3.1, x, y, M("glow_furnace"), n=14)
    cylz("stack_small", 0.17, 0.15, 2.0, 2.7, 0, 0.92, M("graphite"), n=16, bevel=0.03)
    ring("stack_small_mouth", 0.1, 0.18, 2.68, 2.8, M("gold"), n=16, loc=(0, 0.92, 0), bevel=0.02)
    cylz("stack_small_fire", 0.11, 0.11, 2.62, 2.76, 0, 0.92, M("glow_furnace"), n=12)
    # furnace vents on the flanks and on the upper block's front
    for s in (-1, 1):
        x = s * 1.21
        boxz("vent_frame", 0.1, 0.95, 0.66, 1.4, x, 0.38, M("graphite"), bevel=0.04)
        for i in range(3):
            box("vent_glow", (0.06, 0.82, 0.09), (x + s * 0.04, 0.38, 0.82 + i * 0.21), M("glow_furnace"), bevel=0.02, seg=1)
        lens_pod("pod", (s * 1.22, -0.42, 1.1), (s, 0, 0), 0.2)
    for x in (-0.5, 0.0, 0.5):
        box("brow_vent", (0.12, 0.05, 0.26), (x, -0.28, 1.99), M("glow_furnace"), bevel=0.025, seg=1)
    # cyan corner lights on the upper block
    for s in (-1, 1):
        box("corner_light", (0.05, 0.05, 0.3), (s * 0.98, -0.28, 1.98), M("glow"), bevel=0.02, seg=1)


def build_skyport():
    """Air factory: a raised round landing pad (team ring, cyan landing lights) on a rounded cream
    tower, propped by struts, with a lattice gantry on one side and a small drone-headed control pod
    on the other."""
    H = 1.35
    Z = base(H, 0.32, z1=0.18, tier_h=0.14)                     # 0.39
    cylz("tower_foot", 0.78, 0.74, Z - 0.02, Z + 0.18, 0, 0, M("graphite"), n=36, bevel=0.05)
    lathe("tower", [(0.0, Z + 0.1), (0.68, Z + 0.1), (0.66, 0.8), (0.6, 1.45), (0.53, 2.0), (0.5, 2.36), (0.0, 2.36)],
          M("cream"), n=40, split=40)
    torus("tower_trim", 0.64, 0.05, (0, 0, 1.02), M("gold"), major=36, minor=5)
    torus("tower_trim", 0.535, 0.05, (0, 0, 1.96), M("gold"), major=36, minor=5)
    # door and visor at the front
    boxz("door", 0.56, 0.16, Z + 0.1, Z + 0.78, 0, -0.64, M("graphite"), bevel=0.05)
    for s in (-1, 1):
        boxz("door_jamb", 0.08, 0.14, Z + 0.1, Z + 0.84, s * 0.32, -0.67, M("gold"), bevel=0.03, seg=1)
    boxz("door_lintel", 0.72, 0.14, Z + 0.8, Z + 0.9, 0, -0.67, M("gold"), bevel=0.03, seg=1)
    box("door_light", (0.5, 0.05, 0.06), (0, -0.745, Z + 0.85), M("glow"), bevel=0.02, seg=1)
    boxz("visor_housing", 0.24, 0.14, 1.32, 1.86, 0, -0.57, M("graphite"), bevel=0.06)
    boxz("visor", 0.12, 0.06, 1.38, 1.8, 0, -0.64, M("glow"), bevel=0.04, seg=2)
    # landing pad
    lathe("pad_under", [(0.0, 2.3), (0.46, 2.3), (1.05, 2.62), (1.2, 2.7), (0.0, 2.7)], M("graphite"), n=48, split=30)
    cylz("pad_rim", 1.3, 1.3, 2.66, 2.86, 0, 0, M("cream"), n=56, bevel=0.07)
    torus("pad_trim", 1.24, 0.05, (0, 0, 2.86), M("gold"), major=56, minor=5)
    cylz("pad_deck", 1.17, 1.17, 2.8, 2.9, 0, 0, M("graphite"), n=56, bevel=0.02, seg=1)
    ring("pad_marking", 0.62, 0.76, 2.88, 2.925, M("team"), n=48)
    cylz("pad_centre", 0.26, 0.24, 2.88, 2.94, 0, 0, M("gold"), n=24, bevel=0.02, seg=1)
    ring("pad_centre_light", 0.12, 0.17, 2.93, 2.95, M("glow"), n=24)
    for i in range(12):
        a = math.radians(i * 30 + 15)
        cylz("pad_light", 0.06, 0.05, 2.88, 2.95, 1.03 * math.cos(a), 1.03 * math.sin(a), M("glow"), n=10)
    # struts
    for k in range(4):
        a = math.radians(45 + 90 * k)
        u = Vector((math.cos(a), math.sin(a), 0))
        p0, p1 = u * 0.5 + Vector((0, 0, 1.5)), u * 1.0 + Vector((0, 0, 2.62))
        strut("strut", p0, p1, 0.11, 0.11, M("graphite"), bevel=0.03)
        cyl("strut_foot", 0.1, 0.1, 0.1, u * 0.58 + Vector((0, 0, 1.6)), M("gold"), n=12, rot=aim(p1 - p0), bevel=0.02, seg=1)
    # gantry on +X
    gx = 1.1
    for y in (-0.22, 0.3):
        boxz("gantry_post", 0.1, 0.1, Z - 0.02, 2.7, gx, y, M("graphite"), bevel=0.025, seg=1)
    zs = [0.62, 1.12, 1.62, 2.12, 2.6]
    for z in zs:
        box("gantry_rung", (0.07, 0.52, 0.07), (gx, 0.04, z), M("gold"), bevel=0.02, seg=1)
    for i in range(len(zs) - 1):
        ya, yb = (-0.22, 0.3) if i % 2 == 0 else (0.3, -0.22)
        strut("gantry_brace", (gx, ya, zs[i]), (gx, yb, zs[i + 1]), 0.05, 0.05, M("gold2"), bevel=0.012, seg=1)
    boxz("walkway", 0.5, 0.36, 1.6, 1.66, 0.8, 0.04, M("graphite2"), bevel=0.015, seg=1)
    # control pod on -X
    pc = Vector((-0.98, -0.28, 1.36))
    strut("pod_arm", (-0.5, -0.12, 1.3), pc + Vector((0.2, 0.05, -0.04)), 0.16, 0.14, M("graphite"), bevel=0.04)
    pod("pod_head", (0.56, 0.52, 0.46), pc, M("cream"), boxy=0.6, u=22, v=12)
    box("pod_band", (0.6, 0.56, 0.08), pc + Vector((0, 0, -0.08)), M("gold"), bevel=0.03, seg=2)
    box("pod_visor_back", (0.34, 0.06, 0.18), pc + Vector((0, -0.25, 0.04)), M("graphite"), bevel=0.05, seg=2)
    box("pod_visor", (0.26, 0.05, 0.1), pc + Vector((0, -0.28, 0.04)), M("glow"), bevel=0.035, seg=2)
    for s in (-1, 1):
        ear_fin("pod_fin", pc + Vector((s * 0.15, 0.04, 0.16)), 0.36, 0.22, 0.06, s, splay=12, strip=False)
    # antenna mast at the back of the pad
    rod("mast", (0, 1.08, 2.84), (0, 1.08, 3.18), 0.035, M("graphite"), n=12)
    cylz("mast_collar", 0.07, 0.06, 2.84, 2.96, 0, 1.08, M("gold"), n=16, bevel=0.02, seg=1)
    lathe("mast_tip", [(0.0, 3.16), (0.06, 3.18), (0.06, 3.21), (0.0, 3.25)], M("glow"), n=12, split=60)


def build_spire():
    """Late-game special building: a tall, stacked spire on a stepped octagon base with a cyan ring of
    light, four thick swept buttress fins with gold edges and team inlays, gilded strips up the lower
    spire, an exposed bright cyan core in a gold cage halfway up, gold rings stacked toward a cyan tip,
    and a floating gold halo (separate object, group 1)."""
    H = 1.85
    Z = base(H, 0.56, z1=0.24, tier_h=0.18)                     # 0.49
    cylz("drum", 1.32, 1.28, Z - 0.02, Z + 0.22, 0, 0, M("cream"), n=44, bevel=0.06)
    torus("drum_trim", 1.29, 0.05, (0, 0, Z + 0.22), M("gold"), major=44, minor=4)
    ring("drum_light", 0.98, 1.17, Z + 0.19, Z + 0.245, M("glow"), n=44)
    Z2 = Z + 0.22
    low = [(0.74, Z2 - 0.02), (0.69, 1.1), (0.58, 1.6), (0.52, 1.95)]
    lathe("lower", [(0.0, Z2 - 0.02)] + low + [(0.0, 1.95)], M("cream"), n=40, split=40)

    def r_low(z):
        for (r0, z0), (r1, z1) in zip(low, low[1:]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return low[-1][0]
    for k in range(4):
        ac = 90 * k
        za = 1.38 if k == 3 else Z2 + 0.06                      # above the door at the front
        zs = [za + (1.9 - za) * i / 5 for i in range(6)]
        prof = [(r_low(z) + 0.035, z) for z in zs] + [(r_low(z) - 0.03, z) for z in reversed(zs)]
        lathe("gilt", prof, M("gold"), n=2, closed=True, a0=ac - 7, a1=ac + 7, bevel=0.02, seg=1)
    cylz("collar1", 0.6, 0.58, 1.9, 2.1, 0, 0, M("graphite"), n=32, bevel=0.05)
    torus("collar1_trim", 0.58, 0.05, (0, 0, 2.1), M("gold"), major=32, minor=5)
    # the core and its cage
    lathe("core", [(0.0, 2.04), (0.26, 2.16), (0.42, 2.42), (0.44, 2.66), (0.41, 2.92), (0.26, 3.14), (0.0, 3.26)],
          M("glow"), n=8, shade="flat")
    rib = [(0.46, 2.06), (0.6, 2.4), (0.62, 2.66), (0.56, 2.94), (0.46, 3.24), (0.36, 3.24), (0.46, 2.94),
           (0.5, 2.66), (0.48, 2.4), (0.34, 2.06)]
    for k in range(4):
        slab("cage", rib, 0.11, M("gold"), plane="xz", rot=(0, 0, 45 + 90 * k), bevel=0.035, seg=2)
    cylz("collar2", 0.5, 0.46, 3.16, 3.34, 0, 0, M("graphite"), n=32, bevel=0.05)
    torus("collar2_trim", 0.49, 0.045, (0, 0, 3.18), M("gold"), major=32, minor=5)
    # stacked upper segments
    segs = [(3.32, 3.7, 0.42, 0.34), (3.76, 4.06, 0.32, 0.25), (4.12, 4.36, 0.23, 0.16)]
    for i, (za, zb, ra, rb) in enumerate(segs):
        cylz("upper", ra, rb, za, zb, 0, 0, M("cream"), n=24, bevel=0.04, seg=1)
        if i < 2:
            torus("upper_ring", (rb + segs[i + 1][2]) / 2 + 0.01, 0.045, (0, 0, (zb + segs[i + 1][0]) / 2), M("gold"),
                  major=24, minor=4)
    cylz("tip", 0.17, 0.02, 4.34, 4.78, 0, 0, M("gold"), n=16, bevel=0.01, seg=1)
    lathe("tip_light", [(0.0, 4.74), (0.08, 4.86), (0.0, 5.0)], M("glow"), n=6, shade="flat")
    # front door
    boxz("door", 0.42, 0.16, Z2 - 0.02, Z2 + 0.58, 0, -0.68, M("graphite"), bevel=0.05)
    for s in (-1, 1):
        boxz("door_jamb", 0.07, 0.12, Z2 - 0.02, Z2 + 0.62, s * 0.245, -0.71, M("gold"), bevel=0.025, seg=1)
    box("door_light", (0.42, 0.05, 0.06), (0, -0.77, Z2 + 0.68), M("glow"), bevel=0.02, seg=1)
    # buttress fins on the diagonals
    fin = [(0.56, Z - 0.02), (2.0, Z - 0.02), (2.0, Z + 0.26), (1.62, 0.94), (1.24, 1.34), (0.9, 1.74),
           (0.6, 2.04)]
    edge = [(2.0, Z + 0.26), (1.62, 0.94), (1.24, 1.34), (0.9, 1.74), (0.62, 2.02)]
    # team stripe: a band parallel to the gold edge, inset from it
    run = [(1.74, 0.78), (1.62, 0.94), (1.24, 1.34), (0.96, 1.66)]
    def inset(i, d):
        a, b = Vector(run[max(i - 1, 0)]), Vector(run[min(i + 1, len(run) - 1)])
        t = (b - a).normalized()
        return tuple(Vector(run[i]) + Vector((-t.y, t.x)) * d)
    team = [inset(i, 0.13) for i in range(len(run))] + [inset(i, 0.25) for i in reversed(range(len(run)))]
    for k in range(4):
        ang = 45 + 90 * k
        R3 = rz(ang)
        slab("fin", fin, 0.3, M("cream"), plane="xz", rot=(0, 0, ang), bevel=0.1, seg=2)
        pipe("fin_edge", [R3 @ Vector((u, 0, v)) for u, v in edge], 0.09, M("gold"), res=4)
        slab("fin_team", team, 0.33, M("team"), plane="xz", rot=(0, 0, ang), bevel=0.02, seg=1)
        stud("fin_light", R3 @ Vector((2.0, 0, Z + 0.11)), R3 @ Vector((1, 0, 0)), 0.07, collar=False)
    # lens pods on the drum between the fins
    for k in range(3):
        a = math.radians(90 * k)
        u = Vector((math.cos(a), math.sin(a), 0))
        lens_pod("pod", u * 1.32 + Vector((0, 0, Z + 0.1)), u, 0.17)
    # the floating halo
    group(1)
    torus("halo", 0.82, 0.08, (0, 0, 4.18), M("gold"), major=48, minor=6)
    torus("halo_light", 0.725, 0.032, (0, 0, 4.18), M("glow"), major=48, minor=4)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        box("halo_nub", (0.13, 0.13, 0.22), (0.87 * math.cos(a), 0.87 * math.sin(a), 4.18), M("gold"), bevel=0.045,
            seg=1, rot=(0, 0, 45 + 90 * k))
    group(0)


BUILD = {"ambron_citadel": build_citadel, "ambron_relay": build_relay, "ambron_void_machine": build_void_machine,
         "ambron_assembly": build_assembly, "ambron_forge": build_forge, "ambron_skyport": build_skyport,
         "ambron_spire": build_spire}


# --- join, unwrap, bake ------------------------------------------------------------------------------

def deselect_all():
    for o in bpy.context.view_layer.objects:
        o.select_set(False)


def activate(ob):
    deselect_all()
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def join_parts(bid):
    dg = bpy.context.evaluated_depsgraph_get()
    news = [(ob, bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg))
            for ob in PARTS]
    if os.environ.get("AMBRON_PARTS"):
        agg = {}
        for ob, me in news:
            me.calc_loop_triangles()
            key = ob.name.split(".")[0]
            agg[key] = agg.get(key, 0) + len(me.loop_triangles)
        print("[parts]", bid, sorted(agg.items(), key=lambda kv: -kv[1])[:18])
    for ob, me in news:
        old = ob.data
        ob.modifiers.clear()
        ob.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
        a = me.attributes.new("fgroup", "INT", "FACE")
        a.data.foreach_set("value", [int(ob["fgroup"])] * len(me.polygons))
    root = bpy.data.objects.new(bid, bpy.data.meshes.new(bid))
    bpy.context.scene.collection.objects.link(root)
    deselect_all()
    for ob in PARTS:
        ob.select_set(True)
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.object.join()
    PARTS.clear()
    return root


def cull_hidden(ob):
    """Deletes faces nobody can see: faces on the ground facing down, and faces buried inside another
    part (every ray cast out along the face's normal, from a spread of points over the face, meets the
    inside of another solid first). Saves texture space and triangles."""
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    kill = []
    for f in bm.faces:
        n = f.normal
        c = f.calc_center_median()
        if c.z < 0.004 and n.z < -0.98:
            kill.append(f)
            continue
        buried = True
        vs = [v.co for v in f.verts]
        mids = [(vs[i] + vs[(i + 1) % len(vs)]) / 2 for i in range(len(vs))]
        samples = [c] + [c.lerp(q, t) for q in vs for t in (0.3, 0.6, 0.92)] + [c.lerp(q, t) for q in mids for t in (0.5, 0.92)]
        for p in samples:
            hit, hn, _, _ = bvh.ray_cast(p + n * 2e-4, n, 20.0)
            if hit is None or hn.dot(n) <= 0.0:
                buried = False
                break
        if buried:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.update_edit_mesh(ob.data)
    bpy.ops.object.mode_set(mode="OBJECT")
    return len(kill)


def separate_faces(ob, pred, name):
    """Splits the faces where pred(bmface, bm) is true off into a new object called name."""
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(ob.data)
    bm.select_mode = {"FACE"}
    for f in bm.faces:
        f.select_set(False)
    hit = 0
    for f in bm.faces:
        if pred(f, bm):
            f.select_set(True)
            hit += 1
    bm.select_flush_mode()
    bmesh.update_edit_mesh(ob.data)
    new = None
    if hit:
        bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    if hit:
        new = [o for o in bpy.context.selected_objects if o is not ob][0]
        new.name = name
        new.data.name = name
    return new


def add_ground(size=40.0, mat=None, z=0.0, name="ground"):
    bm = bmesh.new()
    s = size / 2
    vs = [bm.verts.new(p) for p in ((-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z))]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def bake_body(bid, body, res):
    """Unwraps the body and bakes flat colour x AO and a metallic-roughness map. Returns the material."""
    activate(body)
    bpy.ops.object.material_slot_remove_unused()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), island_margin=0.006, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = 1.1
    ground = add_ground(60.0, name="bake_ground")
    imgs = {}
    for kind in ("col", "ao"):
        imgs[kind] = bpy.data.images.new(f"{bid}_{kind}", res, res, alpha=False, float_buffer=True)
    nodes = []
    mats = [m for m in body.data.materials if m is not None]
    for m in mats:
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        m.node_tree.nodes.active = t
        nodes.append(t)
    bk = sc.render.bake
    bk.margin = max(4, res // 64)
    bk.margin_type = "EXTEND"
    bk.use_clear = True
    bk.target = "IMAGE_TEXTURES"
    activate(body)
    for t in nodes:
        t.image = imgs["col"]
    sc.cycles.samples = 1
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
    for t in nodes:
        t.image = imgs["ao"]
    sc.cycles.samples = 160
    bpy.ops.object.bake(type="AO")
    bpy.data.objects.remove(ground)
    for m, t in zip(mats, nodes):
        m.node_tree.nodes.remove(t)
    col = np.array(imgs["col"].pixels[:], dtype=np.float32).reshape(res, res, 4)[..., :3]
    ao = np.array(imgs["ao"].pixels[:], dtype=np.float32).reshape(res, res, 4)[..., 0]
    keys = list(PAL)
    pl = np.array([hex_lin(PAL[k][0]) for k in keys], dtype=np.float32)
    idx = ((col[:, :, None, :] - pl[None, None]) ** 2).sum(-1).argmin(-1)
    rough = np.array([PAL[k][1] for k in keys], dtype=np.float32)[idx]
    metal = np.array([PAL[k][2] for k in keys], dtype=np.float32)[idx]
    shade = 0.48 + 0.52 * np.clip(ao, 0, 1) ** 0.9
    final = lin_srgb(col * shade[..., None])
    os.makedirs(CACHE, exist_ok=True)
    out = {}
    for kind, rgb, cs in (("albedo", final, "sRGB"),
                          ("mr", np.dstack([np.ones_like(rough), rough, metal]), "Non-Color")):
        img = bpy.data.images.new(f"{bid}_{kind}", res, res, alpha=False)
        img.colorspace_settings.name = cs
        px = np.ones((res, res, 4), dtype=np.float32)
        px[..., :3] = rgb
        img.pixels.foreach_set(px.ravel())
        img.filepath_raw = os.path.join(CACHE, f"{bid}_{kind}.png")
        img.file_format = "PNG"
        img.save()
        img.pack()
        out[kind] = img
    for img in imgs.values():
        bpy.data.images.remove(img)
    m = bpy.data.materials.new("ambron_body")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = out["albedo"]
    tm = nt.nodes.new("ShaderNodeTexImage")
    tm.image = out["mr"]
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tc.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    return m


def finalize(bid, fast=False):
    root = join_parts(bid)
    culled = cull_hidden(root)
    print("[ambron] culled", culled, "hidden faces")
    floats = FLOATS.get(bid, {})
    if not fast:
        extras = separate_faces(root, lambda f, bm: not root.data.materials[f.material_index].name.startswith("src_"),
                                bid + "_extras")
        body_mat = bake_body(bid, root, TEX_RES.get(bid, 1024))
        me = root.data
        me.polygons.foreach_set("material_index", [0] * len(me.polygons))
        me.materials.clear()
        me.materials.append(body_mat)
        if extras:
            deselect_all()
            extras.select_set(True)
            root.select_set(True)
            bpy.context.view_layer.objects.active = root
            bpy.ops.object.join()
    out = [root]
    for k, name in floats.items():
        def pred(f, bm, k=k):
            return f[bm.faces.layers.int["fgroup"]] == k
        ob = separate_faces(root, pred, name)
        activate(ob)
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        out.append(ob)
    for ob in out:
        activate(ob)
        bpy.ops.object.material_slot_remove_unused()
        for m in ob.data.materials:
            m.use_backface_culling = True                       # single-sided in the GLB
        if "fgroup" in ob.data.attributes:
            ob.data.attributes.remove(ob.data.attributes["fgroup"])
    return out


def tri_count(objs):
    n = 0
    for ob in objs:
        ob.data.calc_loop_triangles()
        n += len(ob.data.loop_triangles)
    return n


def bounds(objs):
    pts = [ob.matrix_world @ v.co for ob in objs for v in ob.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi, pts


def export(bid, objs):
    os.makedirs(MODELS, exist_ok=True)
    deselect_all()
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = os.path.join(MODELS, bid + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False, export_animations=False,
                              export_image_format="AUTO", export_materials="EXPORT", export_normals=True,
                              export_texcoords=True, export_tangents=False, export_extras=False)
    return path


# --- rendering ---------------------------------------------------------------------------------------

def render_setup(res_x, res_y, transparent):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48
    sc.render.resolution_x, sc.render.resolution_y = res_x, res_y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = sc.world or bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.62, 0.74, 1)
    bg.inputs[1].default_value = 0.75


def lights():
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o)
    for name, frm, col, energy in (("key", (-0.55, -0.85, 1.05), (1.0, 0.9, 0.76), 3.4),
                                   ("rim", (0.75, 0.95, 0.55), (0.62, 0.82, 1.0), 2.6)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.color = col
        ld.angle = math.radians(6)
        ob = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.rotation_euler = (-Vector(frm)).to_track_quat("-Z", "Y").to_euler()


def camera(lens=50.0):
    cam = bpy.data.objects.get("cam")
    if cam is None:
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_end = 500
    bpy.context.scene.camera = cam
    return cam


def look(cam, target, az, el, dist):
    target = Vector(target)
    d = Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)),
                math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))))
    cam.location = target + d * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


def fit(cam, pts, margin):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    flat = [c for p in pts for c in p]
    loc, _ = cam.camera_fit_coords(dg, flat)
    fwd = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    cam.location = Vector(loc) - fwd * margin


def ground_mats():
    g = bpy.data.materials.get("review_ground") or bpy.data.materials.new("review_ground")
    g.use_nodes = True
    g.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*hex_lin("#5A6152"), 1)
    g.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    f = bpy.data.materials.get("review_footprint") or bpy.data.materials.new("review_footprint")
    f.use_nodes = True
    f.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*hex_lin("#737B69"), 1)
    f.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    return g, f


def render_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_building(bid, objs, round_dir, icon=True):
    lo, hi, pts = bounds(objs)
    centre = (lo + hi) / 2
    cam = camera(50)
    lights()
    # icon: transparent, front-left three-quarter, tight
    if icon:
        render_setup(256, 256, True)
        look(cam, centre, -125, 24, 20)
        fit(cam, pts, (hi - lo).length * 0.08)
        os.makedirs(ICONS, exist_ok=True)
        render_to(os.path.join(ICONS, bid + ".png"))
    # review: three-quarter on the ground with the footprint marked
    gmat, fmat = ground_mats()
    g = add_ground(80.0, gmat, 0.0, "review_ground")
    fp = add_ground(float(FOOTPRINT[bid]), fmat, 0.003, "review_footprint")
    render_setup(512, 512, False)
    look(cam, centre, -125, 26, 20)
    fit(cam, pts, (hi - lo).length * 0.2)
    render_to(os.path.join(round_dir, bid + "_three_quarter.png"))
    # review: the game camera, 55 degrees down from 25 m, vertical FOV 40
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle = math.radians(40)
    look(cam, (0, 0, 0.8), -90, 55, 25)
    render_to(os.path.join(round_dir, bid + "_game.png"))
    cam.data.sensor_fit = "AUTO"
    bpy.data.objects.remove(g)
    bpy.data.objects.remove(fp)


def render_lineup(round_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    x = 0.0
    placed = []
    for bid in BUILDINGS:
        path = os.path.join(MODELS, bid + ".glb")
        if not os.path.exists(path):
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        w = FOOTPRINT[bid]
        x += w / 2
        for o in new:
            if o.parent is None:
                o.location.x += x
        placed.append((bid, x))
        x += w / 2 + 1.2
    total = x - 1.2
    for o in bpy.data.objects:
        if o.parent is None and o.type in {"MESH", "EMPTY"}:
            o.location.x -= total / 2
    gmat, fmat = ground_mats()
    add_ground(200.0, gmat, 0.0, "review_ground")
    for bid, px in placed:
        f = add_ground(float(FOOTPRINT[bid]), fmat, 0.003, "fp_" + bid)
        f.location.x = px - total / 2
    lights()
    cam = camera(50)
    render_setup(1400, 520, False)
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(66)
    look(cam, (0, 0, 0.8), -90, 55, 28)
    render_to(os.path.join(round_dir, "lineup_game.png"))
    render_setup(1400, 520, False)
    cam.data.angle = math.radians(52)
    look(cam, (0, 0, 1.6), -96, 18, 36)
    render_to(os.path.join(round_dir, "lineup_side.png"))


# --- main --------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    fast = "--fast" in argv
    rnd = "latest"
    if "--round" in argv:
        rnd = argv[argv.index("--round") + 1]
    round_dir = os.path.join(REVIEW, "fast" if fast else rnd)
    targets = [a for a in argv if not a.startswith("--") and a != rnd]
    if "lineup" in targets:
        render_lineup(round_dir)
        return
    ids = BUILDINGS if (not targets or "all" in targets) else targets
    stats = {}
    if os.path.exists(STATS):
        with open(STATS, encoding="utf-8") as f:
            stats = json.load(f)
    for bid in ids:
        t0 = time.time()
        reset()
        BUILD[bid]()
        nparts = len(PARTS)
        objs = finalize(bid, fast)
        lo, hi, _ = bounds(objs)
        tris = tri_count(objs)
        info = {"parts": nparts, "triangles": tris,
                "size_m": [round(hi.x - lo.x, 3), round(hi.y - lo.y, 3), round(hi.z - lo.z, 3)],
                "min": [round(lo.x, 3), round(lo.y, 3), round(lo.z, 3)], "max": [round(hi.x, 3), round(hi.y, 3), round(hi.z, 3)],
                "objects": {o.name: {"triangles": tri_count([o]), "origin": [round(c, 3) for c in o.location],
                                     "materials": [m.name for m in o.data.materials]} for o in objs}}
        if not fast:
            path = export(bid, objs)
            info["glb_bytes"] = os.path.getsize(path)
        render_building(bid, objs, round_dir, icon=not fast)
        info["seconds"] = round(time.time() - t0, 1)
        print("[ambron]", bid, json.dumps(info))
        if not fast:
            stats[bid] = info
    if not fast:
        with open(STATS, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=1)


if __name__ == "__main__":
    main()
