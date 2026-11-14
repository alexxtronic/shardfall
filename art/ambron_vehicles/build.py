"""Ambron war machines for Shardfall, built by script in the family of Alex's harvester drone
(art/ref/ambron_style_reference.png): chunky rounded cream plates, gold trim, graphite mechanics, glowing
cyan lenses, big soft bevels, toy-like.

    Blender --background --factory-startup --python-exit-code 1 --python art/ambron_vehicles/build.py -- <id|all> [--round N] [--no-render]

ids: ambron_scorcher (hover flame tank), ambron_hailfire (tracked missile launcher), ambron_dart (light
interceptor), ambron_monolith (heavy gunship).

Writes assets/models/<id>.glb and assets/icons/<id>.png (256 px, transparent, three-quarter from the
front-left), review renders into art/ambron_vehicles/review/round<N>/ (front three-quarter, back
three-quarter, the game camera at 55 degrees from 25 m, and a sheet of all four) and <id>_stats.json.

Contract (docs/ART_SPEC.md): metres, front -Y, lowest point z = 0, centred in X and Y. Four materials at
most: `ambron_body` (a 64 px palette texture for colour, with a matching metallic/roughness texture),
`team` (light grey, recoloured in game), `glow_cyan` and, on the Scorcher, `glow_fire`. Ground units have a
separate `turret` object whose origin is its turning axis; every unit has an Empty `muzzle` at the weapon
tip (a child of the turret on ground units).
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "icons")
IDS = ("ambron_scorcher", "ambron_hailfire", "ambron_dart", "ambron_monolith")
AIR = {"ambron_dart": 3.5, "ambron_monolith": 3.5}     # flight height in the game view

# --- palette (ART_SPEC Ambron look) -------------------------------------------------------------------
# name: (sRGB hex, roughness, metallic). One 16 px cell each in a 64 px texture, UVs at the cell's centre.
PALETTE = {
    "cream":       ("#EDE3CF", 0.45, 0.0),
    "cream_dk":    ("#D6C9AE", 0.50, 0.0),
    "gold":        ("#E0A33A", 0.38, 0.30),
    "gold_dk":     ("#B9771E", 0.42, 0.30),
    "graphite":    ("#2B2F36", 0.50, 0.20),
    "graphite_lt": ("#474D57", 0.48, 0.20),
    "dark":        ("#17191E", 0.42, 0.10),
    "steel":       ("#9AA1AB", 0.35, 0.30),
}
TEAM = "#C9CDD3"
CYAN = "#5FE3FF"
FIRE = ("#FF6A1F", "#FF4A0C")          # base, emission: orange-hot metal
GLOW_CYAN_STRENGTH = 2.2
GLOW_FIRE_STRENGTH = 2.2


def lin(h):
    """sRGB hex to linear RGBA."""
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def srgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


# --- materials ----------------------------------------------------------------------------------------

def principled(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.use_backface_culling = True          # exported single-sided: closed meshes, cheaper on mobile
    p = m.node_tree.nodes.get("Principled BSDF")
    return m, m.node_tree, p


def palette_images():
    keys = list(PALETTE)
    n, cell = 4, 16
    col = np.zeros((n * cell, n * cell, 4), np.float32)
    mr = np.zeros((n * cell, n * cell, 4), np.float32)
    col[..., 3] = mr[..., 3] = 1.0
    uv = {}
    for i, k in enumerate(keys):
        cx, cy = i % n, i // n
        hexc, rough, metal = PALETTE[k]
        col[cy * cell:(cy + 1) * cell, cx * cell:(cx + 1) * cell, :3] = srgb(hexc)
        mr[cy * cell:(cy + 1) * cell, cx * cell:(cx + 1) * cell, :3] = (1.0, rough, metal)
        uv[k] = ((cx + 0.5) / n, (cy + 0.5) / n)
    imgs = []
    for name, px, cs in (("ambron_palette", col, "sRGB"), ("ambron_palette_mr", mr, "Non-Color")):
        img = bpy.data.images.new(name, n * cell, n * cell, alpha=False)
        img.colorspace_settings.name = cs
        img.pixels.foreach_set(px.ravel())
        img.pack()
        imgs.append(img)
    return imgs, uv


def make_materials():
    (col, mr), uv = palette_images()
    body, nt, p = principled("ambron_body")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image, t.interpolation = col, "Closest"
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    t2 = nt.nodes.new("ShaderNodeTexImage")
    t2.image, t2.interpolation = mr, "Closest"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t2.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    mats = {"body": body}
    mats["team"] = flat("team", TEAM, 0.45, 0.1)
    mats["glow_cyan"] = flat("glow_cyan", CYAN, 0.3, 0.0, CYAN, GLOW_CYAN_STRENGTH)
    mats["glow_fire"] = flat("glow_fire", FIRE[0], 0.35, 0.0, FIRE[1], GLOW_FIRE_STRENGTH)
    return mats, uv


def flat(name, hexc, rough, metal, emit=None, strength=0.0):
    m, nt, p = principled(name)
    p.inputs["Base Color"].default_value = lin(hexc)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = lin(emit)
        p.inputs["Emission Strength"].default_value = strength
    return m


# --- geometry helpers (bmesh) -------------------------------------------------------------------------

def bevel(bm, w, seg=3, edges=None, profile=0.5):
    if w <= 0:
        return bm
    edges = list(bm.edges) if edges is None else list(edges)
    verts = list({v for e in edges for v in e.verts})
    bmesh.ops.bevel(bm, geom=edges + verts, offset=w, offset_type="OFFSET", profile_type="SUPERELLIPSE",
                    segments=seg, profile=profile, affect="EDGES", clamp_overlap=True)
    return bm


def rbox(sx, sy, sz, bev=0.04, seg=None, top=(1.0, 1.0), shift=(0.0, 0.0)):
    """A rounded box, centred; the top face scaled by `top` (x, y) and moved by `shift` (x, y). Three
    bevel segments on big roundings, two on small ones."""
    seg = seg or (3 if bev >= 0.05 else 2)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
        if v.co.z > 0:
            v.co.x = v.co.x * top[0] + shift[0]
            v.co.y = v.co.y * top[1] + shift[1]
    return bevel(bm, bev, seg)


AXES = {"x": lambda a, u, v: (a, u, v), "y": lambda a, u, v: (u, a, v), "z": lambda a, u, v: (u, v, a)}


def prism(pts, a0, a1, axis="x", bev=0.04, seg=3, bev_cap=None):
    """A 2D outline extruded from a0 to a1 along `axis` (x: points are (y, z); y: (x, z); z: (x, y)).
    `bev` rounds every edge; with `bev_cap` the outline's corners get `bev` and the cap rims `bev_cap`."""
    bm = bmesh.new()
    f = AXES[axis]
    r0 = [bm.verts.new(f(a0, u, v)) for u, v in pts]
    r1 = [bm.verts.new(f(a1, u, v)) for u, v in pts]
    bm.faces.new(r0)
    bm.faces.new(r1[::-1])
    n = len(pts)
    longs = []
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.edges.ensure_lookup_table()
    for i in range(n):
        longs.append(bm.edges.get((r0[i], r1[i])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bev_cap is None:
        return bevel(bm, bev, seg)
    bevel(bm, bev, seg, edges=longs)
    i = "xyz".index(axis)
    caps = [e for e in bm.edges
            if any(all(abs(v.co[i] - a) < 1e-6 for v in e.verts) for a in (a0, a1))]
    return bevel(bm, bev_cap, 2, edges=caps)


def lathe(profile, seg=16, closed=False):
    """Revolves (r, h) points around +Z. Trace them counter-clockwise in the (r, h) plane (out along the
    bottom, up the outside, in across the top) and the faces point outward; r = 0 is a pole; closed=True
    joins the last point back to the first (a ring)."""
    bm = bmesh.new()
    rings = []
    for r, h in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, h))] * seg)
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), h))
                          for j in range(seg)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        for j in range(seg):
            k = (j + 1) % seg
            vs = []
            for v in (a[j], a[k], b[k], b[j]):
                if v not in vs:
                    vs.append(v)
            if len(vs) >= 3:
                bm.faces.new(vs)
    return bm


def rounded(pts, r, steps=2, closed=False):
    """Fillets the corners of a polyline (or closed polygon) with radius about r."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        if not closed and (i == 0 or i == n - 1):
            out.append(p)
            continue
        a, c = pts[i - 1], pts[(i + 1) % n]
        pa = (a[0] - p[0], a[1] - p[1])
        pc = (c[0] - p[0], c[1] - p[1])
        la, lc = math.hypot(*pa), math.hypot(*pc)
        d = min(r, la * 0.45, lc * 0.45)
        s = (p[0] + pa[0] / la * d, p[1] + pa[1] / la * d)
        e = (p[0] + pc[0] / lc * d, p[1] + pc[1] / lc * d)
        for t in range(steps + 1):
            t /= steps
            out.append(((1 - t) ** 2 * s[0] + 2 * (1 - t) * t * p[0] + t * t * e[0],
                        (1 - t) ** 2 * s[1] + 2 * (1 - t) * t * p[1] + t * t * e[1]))
    return out


def hull2d(pts):
    """Convex hull, counter-clockwise."""
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def clip_x(poly, x0, x1):
    """The part of a polygon (x, y) between x0 and x1 (Sutherland-Hodgman against two vertical lines)."""
    def cut(pts, inside, at):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q):
                    out.append(at(q, p))
                out.append(p)
            elif inside(q):
                out.append(at(q, p))
        return out

    def at_x(x):
        return lambda q, p: (x, q[1] + (p[1] - q[1]) * (x - q[0]) / (p[0] - q[0]))
    pts = cut(list(poly), lambda p: p[0] >= x0, at_x(x0))
    return cut(pts, lambda p: p[0] <= x1, at_x(x1))


def circle(cu, cv, r, n=12, a0=0.0):
    return [(cu + r * math.cos(a0 + 2 * math.pi * i / n), cv + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def offset_poly(pts, d):
    """Grows a convex polygon outward by d."""
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    sgn = 1 if area > 0 else -1
    lines = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        nx, ny = sgn * dy / L, -sgn * dx / L
        lines.append(((a[0] + nx * d, a[1] + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            out.append(p2)
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def xf(bm, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """Scale, then rotate (degrees, XYZ), then move."""
    M = (Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()
         @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0)))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    if scale[0] * scale[1] * scale[2] < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def on_slope(p0, p1, t=0.5):
    """A point on a front slope of a prism drawn in (y, z), the X rotation that lays a part's thin -Y
    face onto it, and the slope's outward normal (y, z)."""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dy, dz)
    mid = (p0[0] + dy * t, p0[1] + dz * t)
    return mid, math.degrees(math.atan2(-dy, dz)), (-dz / L, dy / L)


def along(rot, d):
    """The vector d along a part's local -Y after rotation `rot`."""
    return Euler([math.radians(a) for a in rot], "XYZ").to_matrix() @ Vector((0, -d, 0))


# --- assembling -------------------------------------------------------------------------------------

class Kit:
    def __init__(self, mats, uv):
        self.mats, self.uv, self.groups = mats, uv, {}

    def add(self, group, bm, key, mirror=False):
        bms = [bm]
        if mirror:
            b2 = bm.copy()
            xf(b2, scale=(-1, 1, 1))
            bms.append(b2)
        for b in bms:
            if key in self.uv:
                mat, uv = self.mats["body"], self.uv[key]
            else:
                mat, uv = self.mats[key], (0.5, 0.5)
            lay = b.loops.layers.uv.get("UVMap") or b.loops.layers.uv.new("UVMap")
            for f in b.faces:
                for lp in f.loops:
                    lp[lay].uv = uv
            me = bpy.data.meshes.new(group)
            b.to_mesh(me)
            b.free()
            me.materials.append(mat)
            ob = bpy.data.objects.new(group, me)
            bpy.context.scene.collection.objects.link(ob)
            self.groups.setdefault(group, []).append(ob)

    def join(self, group, name, origin=(0, 0, 0)):
        obs = self.groups[group]
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = ob.data.name = name
        me = ob.data
        if Vector(origin).length > 0:
            me.transform(Matrix.Translation(-Vector(origin)))
            ob.location = origin
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(42))
        md = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        md.keep_sharp, md.weight, md.mode = True, 50, "FACE_AREA"
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.object.modifier_apply(modifier=md.name)
        return ob


def empty(name, parent, loc, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = "ARROWS", 0.25
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    e.rotation_euler = [math.radians(a) for a in rot]
    return e


def disc_light(k, group, loc, rot, r, mirror=False, rim="cream", depth=0.06, seg=16):
    """The drone's side disc: a rim, a graphite bezel and a domed cyan lens, facing local +Z."""
    rim_p = [(0, 0), (r, 0), (r, depth * 0.55), (r * 0.93, depth), (r * 0.76, depth), (0, depth * 0.85)]
    k.add(group, xf(lathe(rim_p, seg), loc, rot), rim, mirror)
    bez = [(0, depth * 0.8), (r * 0.74, depth * 0.8), (r * 0.72, depth * 1.08), (r * 0.6, depth * 1.12), (0, depth * 1.12)]
    k.add(group, xf(lathe(bez, seg), loc, rot), "graphite", mirror)
    lens = [(0, depth * 1.05), (r * 0.54, depth * 1.05), (r * 0.48, depth * 1.25), (r * 0.26, depth * 1.36), (0, depth * 1.38)]
    k.add(group, xf(lathe(lens, max(10, seg - 4)), loc, rot), "glow_cyan", mirror)


def visor(k, group, x, p0, p1, w, h, gw, gh, mirror=False, t=0.5, frame="graphite"):
    """A graphite face plate laid on a prism's front slope with a cyan pill lens on it (the drone's face)."""
    (y, z), rot, n = on_slope(p0, p1, t)
    k.add(group, xf(rbox(w, 0.05, h, min(0.03, h * 0.3), 2), (x, y, z), (rot, 0, 0)), frame, mirror)
    off = along((rot, 0, 0), 0.024)
    k.add(group, xf(rbox(gw, 0.04, gh, min(gw, gh) * 0.45, 2), (x + off.x, y + off.y, z + off.z), (rot, 0, 0)),
          "glow_cyan", mirror)


def capsule(r, length, seg=14, rings=3):
    """A capsule's (r, h) profile along +Z from 0 to length."""
    pts = [(0.0, 0.0)]
    for i in range(1, rings + 1):
        a = math.pi / 2 * i / rings
        pts.append((r * math.sin(a), r * (1 - math.cos(a))))
    for i in range(rings - 1, -1, -1):
        a = math.pi / 2 * i / rings
        pts.append((r * math.sin(a), length - r * (1 - math.cos(a))))
    return pts


# --- the machines ---------------------------------------------------------------------------------------
# Each builder fills the kit and returns (objects to export, info). Measures in metres, front -Y.

def scorcher(k):
    H, T = "hull", "turret"
    SX = 0.56                                   # sponson centre lines
    # hover sponsons: graphite pods, cream armour, gold nose, cyan vents, hover pads underneath
    k.add(H, xf(rbox(0.40, 1.94, 0.28, 0.12), (SX, 0, 0.25)), "graphite", True)
    k.add(H, xf(rbox(0.48, 1.76, 0.16, 0.07, top=(0.84, 0.95)), (SX, 0.0, 0.44)), "cream", True)
    k.add(H, xf(rbox(0.50, 0.12, 0.172, 0.07, top=(0.85, 0.95)), (SX, -0.50, 0.44)), "team", True)
    k.add(H, xf(rbox(0.36, 0.18, 0.25, 0.08), (SX, -0.92, 0.27)), "gold", True)
    k.add(H, xf(rbox(0.04, 1.30, 0.06, 0.02, 2), (SX + 0.236, 0.05, 0.395)), "gold", True)
    k.add(H, xf(rbox(0.03, 0.56, 0.05, 0.015, 2), (SX + 0.196, -0.40, 0.25)), "glow_cyan", True)
    disc_light(k, H, (SX + 0.19, 0.42, 0.25), (0, 90, 0), 0.135, True)
    for y in (-0.56, 0.56):
        k.add(H, xf(lathe([(0, 0.04), (0.15, 0.04), (0.16, 0.07), (0.16, 0.13), (0, 0.13)], 12), (SX, y, 0)), "graphite", True)
        k.add(H, xf(lathe([(0, 0), (0.11, 0), (0.12, 0.02), (0.12, 0.05), (0, 0.05)], 12), (SX, y, 0)), "glow_cyan", True)
    # centre hull: cream, sloped glacis with the face visor, graphite belly
    hull = [(-1.00, 0.22), (-1.03, 0.36), (-0.72, 0.62), (0.74, 0.64), (1.02, 0.52), (1.02, 0.22)]
    k.add(H, prism(hull, -0.42, 0.42, "x", 0.06, 3), "cream")
    k.add(H, xf(rbox(0.72, 1.86, 0.16, 0.05), (0, 0, 0.22)), "graphite")
    visor(k, H, 0.0, hull[1], hull[2], 0.50, 0.17, 0.36, 0.06)
    (y, z), rot, _ = on_slope(hull[1], hull[2])
    k.add(H, xf(rbox(0.07, 0.05, 0.36, 0.02, 2), (0.36, y, z), (rot, 0, 0)), "gold", True)
    # rear: exhaust lenses, fuel tanks on a saddle, a glowing fuel window on each
    for x in (0.24,):
        k.add(H, xf(lathe([(0, 0), (0.09, 0), (0.09, 0.04), (0, 0.04)], 14), (x, 1.01, 0.38), (-90, 0, 0)), "graphite", True)
        k.add(H, xf(lathe([(0, 0.03), (0.06, 0.03), (0.05, 0.06), (0, 0.065)], 12), (x, 1.01, 0.38), (-90, 0, 0)), "glow_cyan", True)
    k.add(H, xf(rbox(0.92, 0.26, 0.08, 0.03, 2), (0, 0.76, 0.645)), "graphite")
    for x0 in (0.04,):
        k.add(H, xf(lathe(capsule(0.15, 0.42), 14), (x0, 0.76, 0.79), (0, 90, 0)), "gold", True)
        for h in (0.10, 0.32):
            k.add(H, xf(lathe([(0, 0), (0.158, 0), (0.158, 0.035), (0, 0.035)], 14), (x0 + h - 0.017, 0.76, 0.79), (0, 90, 0)), "graphite", True)
        # the fuel window: a glowing slot on the tank's upper back, where the game camera sees it
        c = 0.152 * math.cos(math.radians(45))
        k.add(H, xf(rbox(0.24, 0.04, 0.07, 0.018, 2), (x0 + 0.21, 0.76 + c, 0.79 + c), (45, 0, 0)), "glow_fire", True)
    # turret: squat cream dome-box on a graphite ring, origin on its turning axis
    AX = Vector((0, 0.02, 0.62))

    def tadd(bm, key, mirror=False):
        k.add(T, xf(bm, AX), key, mirror)
    tadd(lathe([(0, 0), (0.42, 0), (0.43, 0.03), (0.43, 0.09), (0, 0.09)], 24), "graphite")
    tur = [(-0.36, 0.06), (-0.45, 0.17), (-0.32, 0.37), (0.24, 0.40), (0.44, 0.30), (0.42, 0.06)]
    tadd(prism(tur, -0.40, 0.40, "x", 0.08, 3), "cream")
    tadd(prism(offset_poly(tur, 0.012), 0.12, 0.20, "x", 0.02, 2), "team", True)
    tadd(xf(rbox(0.06, 0.56, 0.20, 0.03, 2), (0.40, 0.04, 0.20)), "gold", True)
    (y, z), rot, _ = on_slope(tur[1], tur[2])
    tadd(xf(rbox(0.22, 0.05, 0.13, 0.03, 2), (0, y, z), (rot, 0, 0)), "graphite")
    off = along((rot, 0, 0), 0.024)
    tadd(xf(rbox(0.14, 0.04, 0.05, 0.022, 2), (off.x, y + off.y, z + off.z), (rot, 0, 0)), "glow_cyan")
    tadd(xf(lathe([(0, 0), (0.14, 0), (0.14, 0.035), (0, 0.035)], 18), (0, 0.10, 0.372)), "gold")
    tadd(xf(lathe([(0, 0), (0.115, 0), (0.11, 0.03), (0.07, 0.06), (0, 0.068)], 16), (0, 0.10, 0.40)), "cream")
    fin = [(0.06, 0.30), (0.24, 0.30), (0.40, 0.66), (0.33, 0.68)]
    tadd(xf(prism(fin, -0.025, 0.025, "x", 0.02, 2), (0.25, 0, 0), (0, 12, 0)), "gold", True)
    # twin flamer nozzles, glowing orange-hot at the tips
    NZ, NY = 0.16, -0.30
    for piece, h0, key, seg in (
            ([(0, 0), (0.075, 0), (0.075, 0.54), (0, 0.54)], 0.0, "graphite", 14),
            ([(0, 0), (0.115, 0), (0.125, 0.025), (0.125, 0.13), (0.11, 0.15), (0, 0.15)], 0.04, "gold", 16),
            ([(0, 0), (0.092, 0), (0.092, 0.045), (0, 0.045)], 0.33, "gold", 14),
            ([(0, 0), (0.075, 0), (0.11, 0.09), (0.122, 0.12), (0, 0.12)], 0.52, "graphite", 16),
            ([(0, 0), (0.122, 0), (0.128, 0.03), (0.112, 0.055), (0.07, 0.05), (0, 0.045)], 0.64, "glow_fire", 16)):
        tadd(xf(lathe(piece, seg), (0.22, NY - h0, NZ), (90, 0, 0)), key, True)
    hull_ob = k.join(H, "hull")
    tur_ob = k.join(T, "turret", AX)
    muz = empty("muzzle", tur_ob, (0, NY - 0.70, NZ))
    return [hull_ob, tur_ob, muz]


def hailfire(k):
    H, T = "hull", "turret"
    TX0, TX1 = 0.39, 0.73                       # track inner and outer faces
    track = hull2d(circle(-0.84, 0.25, 0.22, 10) + circle(0.86, 0.23, 0.22, 10) + [(-0.55, 0.0), (0.55, 0.0)])
    k.add(H, prism(track, TX0, TX1, "x", 0.035, 2), "dark", True)
    # road wheels and the drone-disc sprockets on the outer faces
    for y in (-0.48, -0.16, 0.16, 0.48):
        k.add(H, xf(lathe([(0, 0), (0.13, 0), (0.13, 0.025), (0.105, 0.045), (0, 0.045)], 10), (TX1, y, 0.15), (0, 90, 0)), "graphite_lt", True)
        k.add(H, xf(lathe([(0, 0), (0.065, 0), (0.06, 0.02), (0, 0.03)], 8), (TX1 + 0.04, y, 0.15), (0, 90, 0)), "cream", True)
    for y, z in ((-0.84, 0.25), (0.86, 0.23)):
        disc_light(k, H, (TX1, y, z), (0, 90, 0), 0.17, True, depth=0.05, seg=12)
    # fenders and side skirts over the tracks
    k.add(H, xf(rbox(0.40, 1.96, 0.10, 0.045, 3), (0.56, -0.03, 0.53)), "cream", True)
    k.add(H, xf(rbox(0.065, 1.24, 0.17, 0.03, 2), (0.757, 0.0, 0.40)), "cream", True)
    k.add(H, xf(rbox(0.075, 1.20, 0.035, 0.015, 2), (0.76, 0.0, 0.318)), "gold", True)
    k.add(H, xf(rbox(0.072, 0.11, 0.18, 0.03, 2), (0.757, -0.42, 0.40)), "team", True)
    k.add(H, xf(rbox(0.405, 0.12, 0.105, 0.045, 3), (0.56, -0.80, 0.53)), "gold", True)
    # chassis: cream deck with the face visor on the glacis, graphite belly, rear vents
    hull = [(-1.00, 0.20), (-1.04, 0.33), (-0.80, 0.60), (0.78, 0.64), (1.02, 0.54), (1.02, 0.20)]
    k.add(H, prism(hull, -0.40, 0.40, "x", 0.06, 3), "cream")
    k.add(H, xf(rbox(0.78, 1.90, 0.22, 0.05), (0, 0, 0.26)), "graphite")
    visor(k, H, 0.0, hull[1], hull[2], 0.46, 0.15, 0.32, 0.055)
    (y, z), rot, _ = on_slope(hull[1], hull[2])
    k.add(H, xf(rbox(0.07, 0.05, 0.33, 0.02, 2), (0.33, y, z), (rot, 0, 0)), "gold", True)
    k.add(H, xf(rbox(0.52, 0.05, 0.16, 0.03, 2), (0, 1.03, 0.38)), "graphite")
    for x in (-0.16, 0.0, 0.16):
        k.add(H, xf(rbox(0.10, 0.03, 0.06, 0.02, 2), (x, 1.055, 0.38)), "glow_cyan")
    # turret: cream base on a ring, gold yoke arms, a tilted box launcher with 4 x 3 cyan-tipped missiles
    AX = Vector((0, 0.12, 0.62))

    def tadd(bm, key, mirror=False):
        k.add(T, xf(bm, AX), key, mirror)
    tadd(lathe([(0, 0), (0.42, 0), (0.43, 0.03), (0.43, 0.08), (0, 0.08)], 20), "graphite")
    tb = [(-0.38, 0.05), (-0.42, 0.13), (-0.30, 0.24), (0.32, 0.25), (0.44, 0.15), (0.42, 0.05)]
    tadd(prism(tb, -0.38, 0.38, "x", 0.05, 3), "cream")
    yoke = [(-0.17, 0.10), (0.18, 0.10), (0.13, 0.50), (-0.11, 0.50)]
    tadd(prism(yoke, 0.37, 0.45, "x", 0.03, 2), "gold", True)
    PIV, TILT = Vector((0, 0.0, 0.47)), -24.0

    def ladd(bm, key, mirror=False):
        tadd(xf(bm, PIV, (TILT, 0, 0)), key, mirror)
    ladd(xf(rbox(0.72, 0.90, 0.46, 0.07), (0, -0.10, 0.06)), "cream")
    ladd(xf(rbox(0.76, 0.10, 0.50, 0.07), (0, -0.50, 0.06)), "gold")
    ladd(xf(rbox(0.735, 0.10, 0.475, 0.07), (0, 0.12, 0.06)), "team")
    ladd(xf(rbox(0.62, 0.05, 0.38, 0.03, 2), (0, -0.555, 0.06)), "graphite")
    ladd(xf(rbox(0.60, 0.04, 0.34, 0.03, 2), (0, 0.36, 0.06)), "graphite")
    for x in (-0.21, -0.07, 0.07, 0.21):
        for z in (-0.06, 0.06, 0.18):
            ladd(xf(lathe([(0, 0.0), (0.055, 0), (0.055, 0.025), (0, 0.025)], 8), (x, -0.575, z), (90, 0, 0)), "dark")
            ladd(xf(lathe([(0, 0), (0.036, 0), (0.034, 0.02), (0.018, 0.055), (0, 0.066)], 8), (x, -0.59, z), (90, 0, 0)), "glow_cyan")
    disc_light(k, T, AX + Vector((0.45, PIV.y, PIV.z)), (0, 90, 0), 0.105, True, depth=0.045, seg=12)
    hull_ob = k.join(H, "hull")
    tur_ob = k.join(T, "turret", AX)
    tip = PIV + Euler((math.radians(TILT), 0, 0)).to_matrix() @ Vector((0, -0.70, 0.06))
    muz = empty("muzzle", tur_ob, tip, (TILT, 0, 0))
    return [hull_ob, tur_ob, muz]


def dart(k):
    B = "body"
    Z = 0.26                                     # the fuselage's centre line
    fus = [(0, 0), (0.06, 0), (0.11, 0.03), (0.145, 0.09), (0.172, 0.20), (0.186, 0.34), (0.188, 0.48), (0.178, 0.62),
           (0.158, 0.75), (0.128, 0.88), (0.088, 0.99), (0.045, 1.07), (0, 1.11)]
    k.add(B, xf(lathe(fus, 24), (0, 0.55, Z), (90, 0, 0), (1.0, 1.0, 1.0)), "cream")
    ob = k.groups[B][-1]                         # flatten the fuselage a little about its centre line
    ob.data.transform(Matrix.Translation((0, 0, Z)) @ Matrix.Diagonal((1, 1, 0.84, 1)) @ Matrix.Translation((0, 0, -Z)))
    # canopy: a graphite frame with a cyan glass dome on top of the nose (the drone's face)
    k.add(B, xf(lathe([(0, 0), (1.0, 0), (0.95, 0.3), (0.75, 0.62), (0.4, 0.85), (0, 0.92)], 18), (0, -0.17, Z + 0.10),
                (0, 0, 0), (0.12, 0.30, 0.10)), "graphite")
    k.add(B, xf(lathe([(0, 0), (1.0, 0), (0.93, 0.36), (0.72, 0.7), (0.38, 0.9), (0, 0.97)], 18), (0, -0.19, Z + 0.115),
                (0, 0, 0), (0.085, 0.22, 0.09)), "glow_cyan")
    k.add(B, xf(rbox(0.07, 0.36, 0.05, 0.02), (0, 0.24, Z + 0.15)), "gold")
    # forward-swept wings: cream, a team band, gold tips with a cyan running light
    wing = [(0.10, -0.02), (0.60, -0.24), (0.645, -0.20), (0.645, -0.10), (0.10, 0.28)]
    WR = (0, -7, 0)
    k.add(B, xf(prism(wing, -0.028, 0.028, "z", 0.024, 2), (0, 0, Z - 0.03), WR), "cream", True)
    k.add(B, xf(prism(clip_x(wing, 0.42, 0.49), -0.031, 0.031, "z", 0.012, 2), (0, 0, Z - 0.03), WR), "team", True)
    k.add(B, xf(prism(clip_x(wing, 0.565, 0.70), -0.032, 0.032, "z", 0.02, 2), (0, 0, Z - 0.03), WR), "gold", True)
    k.add(B, xf(xf(lathe([(0, 0), (0.024, 0), (0.022, 0.014), (0, 0.018)], 8), (0.615, -0.228, 0), (90, 0, -24)), (0, 0, Z - 0.03), WR), "glow_cyan", True)
    # gold canards by the nose
    can = [(0.06, -0.33), (0.22, -0.46), (0.235, -0.42), (0.06, -0.22)]
    k.add(B, xf(prism(can, -0.016, 0.016, "z", 0.012, 2), (0, 0, Z - 0.01), (0, -10, 0)), "gold", True)
    # twin engine pods: cream, gold band, graphite intake, glowing exhaust, the drone's gold ear fins on top
    PX, PZ = 0.25, Z - 0.02
    pod = [(0, 0), (0.06, 0), (0.088, 0.02), (0.104, 0.07), (0.114, 0.16), (0.116, 0.28), (0.112, 0.40), (0.10, 0.50),
           (0.08, 0.545), (0, 0.55)]
    k.add(B, xf(lathe(pod, 20), (PX, 0.50, PZ), (90, 0, 0)), "cream", True)
    k.add(B, xf(lathe([(0, 0), (0.12, 0), (0.12, 0.07), (0, 0.07)], 20), (PX, 0.30, PZ), (90, 0, 0)), "gold", True)
    k.add(B, xf(lathe([(0, 0), (0.096, 0), (0.096, 0.05), (0.078, 0.05), (0.072, 0.02), (0, 0.02)], 20), (PX, 0.56, PZ), (90, 0, 0)), "graphite", True)
    k.add(B, xf(lathe([(0, 0), (0.072, 0), (0.072, 0.03), (0, 0.03)], 16), (PX, 0.56, PZ), (90, 0, 0)), "glow_cyan", True)
    k.add(B, xf(lathe([(0, 0), (0.092, 0), (0.092, 0.03), (0.062, 0.036), (0.04, 0.02), (0, 0.02)], 20), (PX, -0.03, PZ), (90, 0, 0)), "graphite", True)
    fin = [(0.16, 0.06), (0.40, 0.06), (0.53, 0.36), (0.46, 0.37)]
    k.add(B, xf(prism(fin, -0.02, 0.02, "x", 0.015, 2), (PX, 0, PZ), (0, 16, 0)), "gold", True)
    # the tail: a graphite cone with a glowing core between the pods
    k.add(B, xf(lathe([(0, 0), (0.06, 0), (0.062, 0.03), (0, 0.03)], 14), (0, 0.545, Z), (-90, 0, 0)), "glow_cyan")
    # twin nose cannons under the chin, a graphite keel
    CX, CZ = 0.10, Z - 0.10
    k.add(B, xf(rbox(0.30, 0.24, 0.08, 0.03), (0, -0.30, CZ + 0.02)), "graphite")
    k.add(B, xf(rbox(0.10, 0.50, 0.08, 0.035), (0, 0.10, Z - 0.15)), "graphite")
    for piece, h0, key in (([(0, 0), (0.03, 0), (0.03, 0.44), (0, 0.44)], 0.0, "graphite"),
                           ([(0, 0), (0.042, 0), (0.042, 0.05), (0, 0.05)], 0.12, "gold"),
                           ([(0, 0), (0.038, 0), (0.038, 0.035), (0, 0.035)], 0.26, "gold"),
                           ([(0, 0), (0.04, 0), (0.04, 0.035), (0, 0.035)], 0.42, "glow_cyan")):
        k.add(B, xf(lathe(piece, 12), (CX, -0.30 - h0, CZ), (90, 0, 0)), key, True)
    body = k.join(B, "body")
    muz = empty("muzzle", None, (0, -0.30 - 0.47, CZ))
    return [body, muz]


def monolith(k):
    B = "body"
    hull = [(-1.04, 0.45), (-1.10, 0.62), (-0.86, 0.92), (0.74, 0.98), (1.00, 0.84), (1.00, 0.45)]
    k.add(B, prism(hull, -0.62, 0.62, "x", 0.10, 3), "cream")
    k.add(B, xf(rbox(1.10, 1.86, 0.26, 0.08), (0, 0, 0.47)), "graphite")
    visor(k, B, 0.0, hull[1], hull[2], 0.84, 0.21, 0.62, 0.075)
    (y, z), rot, _ = on_slope(hull[1], hull[2])
    k.add(B, xf(rbox(0.10, 0.05, 0.40, 0.025), (0.53, y, z), (rot, 0, 0)), "gold", True)
    # top: two team stripes running front to back, a raised bridge with its own eye, a gold spine behind it
    top = offset_poly(hull, 0.012)
    k.add(B, prism(top, 0.24, 0.34, "x", 0.10, 3, bev_cap=0.01), "team", True)
    bridge = [(-0.62, 0.90), (-0.50, 1.07), (-0.12, 1.08), (0.02, 0.92)]
    k.add(B, prism(bridge, -0.18, 0.18, "x", 0.05, 3), "cream")
    visor(k, B, 0.0, bridge[0], bridge[1], 0.26, 0.11, 0.18, 0.045, t=0.55)
    k.add(B, xf(rbox(0.16, 0.66, 0.07, 0.03), (0, 0.36, 0.975)), "gold")
    # side discs and gold side plates
    k.add(B, xf(rbox(0.06, 1.20, 0.26, 0.04), (0.62, 0.05, 0.70)), "gold", True)
    disc_light(k, B, (0.64, 0.05, 0.70), (0, 90, 0), 0.15, True)
    # four ducted fans on graphite pylons, cyan glow inside
    FX, FY, FZ = 0.84, 0.60, 0.80
    for y in (-FY, FY):
        k.add(B, xf(rbox(0.40, 0.24, 0.13, 0.05, 2), (0.66, y, FZ - 0.02)), "graphite", True)
        duct = rounded([(0.27, -0.12), (0.37, -0.12), (0.37, 0.10), (0.27, 0.10)], 0.035, 1, closed=True)
        k.add(B, xf(lathe(duct, 20, closed=True), (FX, y, FZ)), "cream", True)
        lip = [(0.29, 0.085), (0.378, 0.085), (0.378, 0.13), (0.29, 0.13)]
        k.add(B, xf(lathe(lip, 20, closed=True), (FX, y, FZ)), "gold", True)
        k.add(B, xf(lathe([(0, -0.03), (0.275, -0.03), (0.275, 0.0), (0, 0.0)], 20), (FX, y, FZ)), "glow_cyan", True)
        k.add(B, xf(lathe([(0, -0.05), (0.08, -0.05), (0.08, 0.02), (0.05, 0.05), (0, 0.055)], 12), (FX, y, FZ)), "graphite", True)
        for a in (0, 120, 240):
            bl = xf(rbox(0.20, 0.05, 0.015, 0.006, 1), (0.14, 0, 0.012), (14, 0, 0))
            k.add(B, xf(bl, (FX, y, FZ), (0, 0, a)), "graphite", True)
    # the gold ear fins, rear exhausts
    fin = [(0.30, 0.90), (0.62, 0.86), (0.78, 1.22), (0.70, 1.24)]
    k.add(B, xf(prism(fin, -0.03, 0.03, "x", 0.02, 2), (0.30, 0, 0), (0, 12, 0)), "gold", True)
    k.add(B, xf(lathe([(0, 0), (0.11, 0), (0.11, 0.05), (0, 0.05)], 16), (0.30, 1.0, 0.66), (-90, 0, 0)), "graphite", True)
    k.add(B, xf(lathe([(0, 0.04), (0.08, 0.04), (0.07, 0.07), (0, 0.075)], 14), (0.30, 1.0, 0.66), (-90, 0, 0)), "glow_cyan", True)
    # the big underslung cannon: a graphite housing, a gold collar, an energy barrel with glowing coils
    k.add(B, xf(rbox(0.50, 0.80, 0.32, 0.10), (0, -0.30, 0.30)), "graphite")
    k.add(B, xf(rbox(0.54, 0.20, 0.34, 0.10), (0, -0.60, 0.30)), "gold")
    CY, CZ = -0.66, 0.28
    for piece, h0, key, seg in (
            ([(0, 0), (0.115, 0), (0.115, 0.70), (0, 0.70)], 0.0, "graphite_lt", 16),
            ([(0, 0), (0.14, 0), (0.14, 0.06), (0, 0.06)], 0.08, "glow_cyan", 16),
            ([(0, 0), (0.14, 0), (0.14, 0.06), (0, 0.06)], 0.22, "glow_cyan", 16),
            ([(0, 0), (0.14, 0), (0.14, 0.06), (0, 0.06)], 0.36, "glow_cyan", 16),
            ([(0, 0), (0.13, 0), (0.13, 0.05), (0, 0.05)], 0.50, "gold", 16),
            ([(0, 0), (0.15, 0), (0.17, 0.03), (0.17, 0.17), (0.15, 0.19), (0.10, 0.19), (0, 0.17)], 0.62, "graphite", 18),
            ([(0, 0), (0.10, 0), (0.095, 0.02), (0, 0.025)], 0.80, "glow_cyan", 14)):
        k.add(B, xf(lathe(piece, seg), (0, CY - h0, CZ), (90, 0, 0)), key)
    body = k.join(B, "body")
    muz = empty("muzzle", None, (0, CY - 0.85, CZ))
    return [body, muz]


BUILDERS = {"ambron_scorcher": scorcher, "ambron_hailfire": hailfire, "ambron_dart": dart, "ambron_monolith": monolith}


# --- checks, export -------------------------------------------------------------------------------------

def world_points(objs, limit=None):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        mw = o.matrix_world
        pts += [mw @ v.co for v in ev.data.vertices]
    if limit and len(pts) > limit:
        pts = pts[::max(1, len(pts) // limit)]
    return pts


def settle(objs):
    """Lowest point to z = 0, bounding box centred in X and Y."""
    bpy.context.view_layer.update()
    pts = world_points(objs)
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    d = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in objs:
        if o.parent is None:
            if o.type == "MESH" and o.location.length < 1e-9:
                o.data.transform(Matrix.Translation(-d))     # hull / body: origin stays at ground centre
            else:
                o.location -= d                              # turret axis, air-unit muzzle
    bpy.context.view_layer.update()
    return hi - lo


def tris(ob):
    me = ob.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False, export_animations=False)


# --- review and icon renders ---------------------------------------------------------------------------

def stage():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("studio")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.045, 0.05, 0.06, 1)
    bg.inputs[1].default_value = 1.0
    for name, col, energy, d in (("key", (1.0, 0.88, 0.74), 3.4, (-0.9, -1.3, 1.5)),
                                 ("rim", (0.55, 0.75, 1.0), 2.8, (1.3, 1.6, 0.9)),
                                 ("fill", (0.85, 0.9, 1.0), 0.6, (1.2, -1.0, 0.3))):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy, ld.color, ld.angle = energy, col, math.radians(8)
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()
        ld.use_shadow = name == "key"
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    gm = flat("ground", "#5E5A4C", 0.9, 0.0)
    me = bpy.data.meshes.new("ground")
    me.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(gm)
    ground = bpy.data.objects.new("ground", me)
    sc.collection.objects.link(ground)
    return cam, ground, bg


def view_dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def look(cam, target):
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


def fit(cam, pts, az, el, margin):
    sc = bpy.context.scene
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "AUTO"
    cam.data.angle = math.radians(30)
    cam.data.shift_x = cam.data.shift_y = 0.0
    dist = 12.0
    for _ in range(6):
        cam.location = c + view_dir(az, el) * dist
        look(cam, c)
        bpy.context.view_layer.update()
        ndc = [world_to_camera_view(sc, cam, p) for p in pts]
        xs, ys = [p.x for p in ndc], [p.y for p in ndc]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        dist *= span / (1 - 2 * margin)
    cam.data.shift_x = (min(xs) + max(xs)) / 2 - 0.5
    cam.data.shift_y = (min(ys) + max(ys)) / 2 - 0.5


def render(path, res, transparent):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.render.render(write_still=True)


def load_px(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def sheet(paths, out, cell=512, bgc=(0.2, 0.21, 0.23)):
    tiles = []
    for p in paths:
        a = load_px(p)
        t = np.zeros((cell, cell, 4), np.float32)
        t[..., :3] = bgc
        t[..., 3] = 1
        h, w = a.shape[:2]
        y0, x0 = (cell - h) // 2, (cell - w) // 2
        al = a[..., 3:4]
        t[y0:y0 + h, x0:x0 + w, :3] = a[..., :3] * al + t[y0:y0 + h, x0:x0 + w, :3] * (1 - al)
        tiles.append(t)
    s = np.concatenate(tiles, axis=1)
    img = bpy.data.images.new("sheet", s.shape[1], s.shape[0], alpha=True)
    img.pixels.foreach_set(s.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def review(uid, objs, rnd):
    cam, ground, bg = stage()
    pts = world_points(objs, 3000)
    out = os.path.join(HERE, "review", "round%d" % rnd)
    shots = []
    # the icon: three-quarter from the front-left, a little above, tight, transparent
    ground.hide_render = True
    fit(cam, pts, 35, 24, 0.04)
    icon = os.path.join(ICONS, uid + ".png")
    render(icon, (256, 256), True)
    # front and back three-quarters on the studio grey
    bg.inputs[0].default_value = (0.05, 0.053, 0.06, 1)
    fit(cam, pts, 35, 22, 0.08)
    shots.append(os.path.join(out, uid + "_front.png"))
    render(shots[-1], (512, 512), False)
    fit(cam, pts, -140, 26, 0.08)
    shots.append(os.path.join(out, uid + "_back.png"))
    render(shots[-1], (512, 512), False)
    # the game camera: 55 degrees down from 25 m, 45 degree vertical field of view, on the ground
    ground.hide_render = False
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
    cam.data.angle = math.radians(45)
    cam.data.shift_x = cam.data.shift_y = 0.0
    lift = AIR.get(uid, 0.0)
    for o in objs:
        if o.parent is None:
            o.location.z += lift
    tgt = Vector((0, 0, 0.5 + lift))
    cam.location = tgt + view_dir(-25, 55) * 25
    look(cam, tgt)
    shots.append(os.path.join(out, uid + "_game.png"))
    render(shots[-1], (512, 512), False)
    sheet(shots + [icon], os.path.join(out, uid + "_sheet.png"))


# --- main ------------------------------------------------------------------------------------------------

def build(uid, rnd, do_render):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats, uv = make_materials()
    k = Kit(mats, uv)
    objs = BUILDERS[uid](k)
    dims = settle(objs)
    meshes = [o for o in objs if o.type == "MESH"]
    path = os.path.join(MODELS, uid + ".glb")
    export(objs, path)
    info = {
        "id": uid,
        "triangles": sum(tris(o) for o in meshes),
        "per_object": {o.name: tris(o) for o in meshes},
        "size_m": [round(v, 3) for v in dims],
        "glb_bytes": os.path.getsize(path),
        "materials": sorted({m.name for o in meshes for m in o.data.materials}),
        "objects": {o.name: {"world": [round(v, 3) for v in o.matrix_world.translation],
                             "local": [round(v, 3) for v in o.location],
                             "parent": o.parent.name if o.parent else None} for o in objs},
    }
    print("[shardfall]", json.dumps(info))
    os.makedirs(os.path.join(HERE, "review"), exist_ok=True)
    with open(os.path.join(HERE, "review", uid + "_stats.json"), "w") as f:
        json.dump(info, f, indent=1)
    if do_render:
        review(uid, objs, rnd)
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = argv[0] if argv else "all"
    rnd = int(argv[argv.index("--round") + 1]) if "--round" in argv else 1
    ids = IDS if which == "all" else [which]
    for uid in ids:
        if uid not in BUILDERS:
            raise SystemExit("unknown id " + uid)
        build(uid, rnd, "--no-render" not in argv)


if __name__ == "__main__":
    main()
