"""Ambron units for Shardfall: rigged, animated robots built by script in the family of Alex's harvester drone
(art/ref/ambron_style_reference.png) and the finished Ambron machines (art/ambron_vehicles/build.py): chunky
rounded cream plates, gold trim, graphite joints, glowing cyan lenses, big soft bevels, toy-like.

    Blender --background --factory-startup --python-exit-code 1 --python art/ambron_units/build.py -- <id|all|lineup|refcompare> [--round N] [--no-render]

ids: ambron_lancer (ranged infantry, energy rifle), ambron_bulwark (heavy trooper, shield arm and arm cannon),
ambron_sovereign (four-legged walking titan with a beam cannon), ambron_worker (the Harvester drone, a fallback
rebuild of Alex's Tripo model). `lineup` renders every finished unit beside two Ambron vehicles under the game
camera; `refcompare` renders the drone beside the reference turnaround.

Each unit is one skinned mesh `body` (rigid weights: every part 100 % on one bone) under an armature object
`rig`, plus an Empty `muzzle` parented to the weapon bone. Actions `idle_loop`, `walk_loop` and `attack` are
baked per frame at 30 fps from a small forward-kinematics model with two-bone IK for planted feet and hands on
the rifle, all in place; loops end on their first pose and `attack` ends on the rest pose. They are exported as
separate glTF animations (export_animation_mode ACTIONS), then the GLB is re-imported into a fresh scene to
list the animations it really holds.

Writes assets/models/<id>.glb, assets/icons/<id>.png (256 px, transparent, three-quarter from the front-left),
review renders into art/ambron_units/review/round<N>/ (front and back three-quarters, the game camera at 55
degrees from 25 m, the same at twice the zoom, a contact sheet of animation frames) and
art/ambron_units/review/<id>_stats.json.

Contract (docs/ART_SPEC.md): metres, front -Y, lowest point z = 0 (bind pose), bounding box centred in X and Y,
materials `ambron_body` (the shared 64 px palette texture), `team`, `glow_cyan` and, on the drone's crystal
load, `glow_crystal`. Shared helpers come from art/ambron_vehicles/build.py, loaded as art/neutral/build.py
does; that file is not changed.
"""
import importlib.util
import json
import math
import os
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "icons")
CACHE = os.path.join(HERE, "cache")
REF = os.path.join(ROOT, "art", "ref", "ambron_style_reference.png")
sys.dont_write_bytecode = True                 # no __pycache__ beside the vehicle script
_spec = importlib.util.spec_from_file_location("ambron_vehicles_build",
                                               os.path.join(ROOT, "art", "ambron_vehicles", "build.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

IDS = ("ambron_lancer", "ambron_bulwark", "ambron_sovereign", "ambron_worker")
FPS = 30
CRYSTAL = ("#FFC93A", "#FFB020", 0.7)          # the drone's crystal load: base, emission, strength
I4 = Matrix.Identity(4)


# --- small maths ----------------------------------------------------------------------------------------

def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def quat(rot):
    """None, a Quaternion or Euler degrees (XYZ, world axes) to a Quaternion."""
    if rot is None:
        return Quaternion()
    if isinstance(rot, Quaternion):
        return rot.copy()
    return Euler([math.radians(a) for a in rot], "XYZ").to_quaternion()


def mirror_rot(rot):
    return None if rot is None else (rot[0], -rot[1], -rot[2])


def mirror_loc(loc):
    return None if loc is None else (-loc[0], loc[1], loc[2])


def flip(name):
    if name and name[-1] == "L":
        return name[:-1] + "R"
    if name and name[-1] == "R":
        return name[:-1] + "L"
    return name


# --- geometry helpers --------------------------------------------------------------------------------------

def seg_to(bm, p0, p1, spin=0.0):
    """Moves a part built along +Z (from z = 0) so that +Z runs from p0 towards p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    z = Vector((0, 0, 1))
    rq = Quaternion((1, 0, 0), math.pi) if d.dot(z) < -0.9999 else z.rotation_difference(d)
    M = Matrix.Translation(p0) @ rq.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(spin), 4, "Z")
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def limb_box(p0, p1, w, d, bev=0.03, e0=0.0, e1=0.0, top=(1.0, 1.0), seg=None, spin=0.0):
    """A rounded box from p0 to p1 (w across X, d across Y before orienting), extended by e0 / e1 at the ends."""
    L = (Vector(p1) - Vector(p0)).length
    h = L + e0 + e1
    bm = V.rbox(w, d, h, bev, seg, top)
    V.xf(bm, (0, 0, h / 2 - e0))
    return seg_to(bm, p0, p1, spin)


def limb_cyl(p0, p1, r, seg=12, r1=None, e0=0.0, e1=0.0):
    L = (Vector(p1) - Vector(p0)).length
    bm = V.lathe([(0, -e0), (r, -e0), (r if r1 is None else r1, L + e1), (0, L + e1)], seg)
    return seg_to(bm, p0, p1)


def ell(c, rx, ry, rz, seg=16, rings=8, h0=-1.0, h1=1.0):
    """An ellipsoid centred at c, optionally cut flat at h0 / h1 (fractions of rz)."""
    a0, a1 = math.asin(max(-1.0, h0)), math.asin(min(1.0, h1))
    prof = [(0.0, h0)] if h0 > -1 else []
    for i in range(rings + 1):
        a = a0 + (a1 - a0) * i / rings
        prof.append((math.cos(a), math.sin(a)))
    if h1 < 1:
        prof.append((0.0, h1))
    return V.xf(V.lathe(prof, seg), c, (0, 0, 0), (rx, ry, rz))


def ring(r0, r1, h, seg=16):
    """A flat-sided ring (washer) from z = 0 to h."""
    return V.lathe([(r0, 0), (r1, 0), (r1, h), (r0, h)], seg, closed=True)


def gore(prof, a0, a1, n=3, out=0.012, inn=0.03):
    """A panel lying on a lathe surface between azimuths a0..a1 (degrees) over the profile points (r, h),
    raised `out` above the surface and sunk `inn` below it."""
    bm = bmesh.new()
    m = len(prof)
    O, IN = [], []
    for i, (r, h) in enumerate(prof):
        pa, pb = prof[max(i - 1, 0)], prof[min(i + 1, m - 1)]
        tr, th = pb[0] - pa[0], pb[1] - pa[1]
        L = math.hypot(tr, th)
        nr, nh = th / L, -tr / L
        ro, ri = [], []
        for j in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * j / n)
            ca, sa = math.cos(a), math.sin(a)
            Ro, Ri = r + nr * out, max(0.002, r - nr * inn)
            ro.append(bm.verts.new((Ro * ca, Ro * sa, h + nh * out)))
            ri.append(bm.verts.new((Ri * ca, Ri * sa, h - nh * inn)))
        O.append(ro)
        IN.append(ri)
    for i in range(m - 1):
        for j in range(n):
            bm.faces.new((O[i][j], O[i][j + 1], O[i + 1][j + 1], O[i + 1][j]))
            bm.faces.new((IN[i][j], IN[i + 1][j], IN[i + 1][j + 1], IN[i][j + 1]))
        bm.faces.new((O[i][0], O[i + 1][0], IN[i + 1][0], IN[i][0]))
        bm.faces.new((O[i][n], IN[i][n], IN[i + 1][n], O[i + 1][n]))
    for i in (0, m - 1):
        for j in range(n):
            bm.faces.new((O[i][j], IN[i][j], IN[i][j + 1], O[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sphere_prof(lat0, lat1, n):
    """(r, h) points on a unit sphere between two latitudes (degrees)."""
    return [(math.cos(math.radians(lat0 + (lat1 - lat0) * i / n)), math.sin(math.radians(lat0 + (lat1 - lat0) * i / n)))
            for i in range(n + 1)]


def strap(cu, cv, ru, rv, a0, a1, w0, w1, axis="x", out=0.012, inn=0.025, n=10, bev=0.006):
    """A band lying on an ellipse (centre cu, cv; radii ru, rv in the plane across `axis`) from angle a0 to a1,
    extruded from w0 to w1 along `axis`."""
    outer, inner = [], []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        ca, sa = math.cos(a), math.sin(a)
        outer.append((cu + (ru + out) * ca, cv + (rv + out) * sa))
        inner.append((cu + (ru - inn) * ca, cv + (rv - inn) * sa))
    return V.prism(outer + inner[::-1], w0, w1, axis, bev, 1)


def crystal(base, h, r, tilt=(0, 0, 0)):
    """A hexagonal crystal with a pointed tip, standing on `base`."""
    return V.xf(V.lathe([(0, -0.02), (r, -0.02), (r * 1.06, h * 0.66), (0, h)], 6), base, tilt)


def disc(k, bone, loc, rot, r, rim="cream", depth=0.06, seg=16, stretch=1.0, bezel="graphite", mirror=False):
    """The drone's side disc (as V.disc_light: a rim cup, a graphite bezel, a domed cyan lens, facing local +Z),
    optionally stretched along local X."""
    sc = (stretch, 1.0, 1.0)
    rim_p = [(0, 0), (r, 0), (r, depth * 0.55), (r * 0.93, depth), (r * 0.76, depth), (0, depth * 0.85)]
    k.add(bone, V.xf(V.lathe(rim_p, seg), loc, rot, sc), rim, mirror)
    bez = [(0, depth * 0.8), (r * 0.74, depth * 0.8), (r * 0.72, depth * 1.08), (r * 0.6, depth * 1.12), (0, depth * 1.12)]
    k.add(bone, V.xf(V.lathe(bez, seg), loc, rot, sc), bezel, mirror)
    lens = [(0, depth * 1.05), (r * 0.54, depth * 1.05), (r * 0.48, depth * 1.25), (r * 0.26, depth * 1.36), (0, depth * 1.38)]
    k.add(bone, V.xf(V.lathe(lens, max(10, seg - 4)), loc, rot, sc), "glow_cyan", mirror)


# --- the kit: parts become one skinned mesh ------------------------------------------------------------------

class Kit:
    """Collects parts as objects, each with one vertex group (its bone) at weight 1."""

    def __init__(self, mats, uv):
        self.mats, self.uv, self.parts = mats, uv, []
        self.tris = {}                           # (bone, colour) -> triangles, for budget work

    def add(self, bone, bm, key, mirror=False):
        items = [(bone, bm)]
        if mirror:
            b2 = bm.copy()
            V.xf(b2, scale=(-1, 1, 1))
            items.append((flip(bone), b2))
        for name, b in items:
            if key in self.uv:
                mat, uv = self.mats["body"], self.uv[key]
            else:
                mat, uv = self.mats[key], (0.5, 0.5)
            lay = b.loops.layers.uv.get("UVMap") or b.loops.layers.uv.new("UVMap")
            for f in b.faces:
                for lp in f.loops:
                    lp[lay].uv = uv
            tk = (name, key)
            self.tris[tk] = self.tris.get(tk, 0) + sum(len(f.verts) - 2 for f in b.faces)
            me = bpy.data.meshes.new(name)
            b.to_mesh(me)
            b.free()
            me.materials.append(mat)
            ob = bpy.data.objects.new(name, me)
            bpy.context.scene.collection.objects.link(ob)
            vg = ob.vertex_groups.new(name=name)
            vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
            self.parts.append(ob)

    def join(self, name="body"):
        bpy.ops.object.select_all(action="DESELECT")
        for o in self.parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = self.parts[0]
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = ob.data.name = name
        me = ob.data
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(42))
        md = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        md.keep_sharp, md.weight, md.mode = True, 50, "FACE_AREA"
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.object.modifier_apply(modifier=md.name)
        return ob


class Skel:
    """Bone definitions (design coordinates); mirror=True adds the _R twin of an _L bone across X."""

    def __init__(self):
        self.defs = {}

    def bone(self, name, head, tail, parent=None, mirror=False):
        self.defs[name] = (Vector(head), Vector(tail), parent)
        if mirror:
            m = lambda v: Vector((-v[0], v[1], v[2]))
            self.defs[flip(name)] = (m(head), m(tail), flip(parent) if parent else None)


def make_rig(skel, off):
    arm = bpy.data.armatures.new("rig")
    rig = bpy.data.objects.new("rig", arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (h, t, _) in skel.defs.items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = h - off, t - off, 0.0
    for name, (_, _, p) in skel.defs.items():
        if p:
            eb = arm.edit_bones[name]
            eb.parent = arm.edit_bones[p]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    arm.display_type = "STICK"
    return rig


# --- posing: forward kinematics in world axes, two-bone IK, baking ------------------------------------------

class Pose:
    """Each bone gets a local delta L (a rigid transform in rest-world axes, applied in its parent's moved frame);
    D(bone) = D(parent) @ L(bone). The pose bone's basis is then rest^-1 @ L @ rest."""

    def __init__(self, rig):
        bones = rig.data.bones
        self.rest = {b.name: b.matrix_local.copy() for b in bones}
        self.irest = {n: m.inverted() for n, m in self.rest.items()}
        self.head = {b.name: b.head_local.copy() for b in bones}
        self.tail = {b.name: b.tail_local.copy() for b in bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.names = [b.name for b in bones]
        self.clear()

    def clear(self):
        self.L, self.D = {}, {}

    def d(self, n):
        if n is None:
            return I4
        if n not in self.D:
            self.D[n] = self.d(self.parent[n]) @ self.L.get(n, I4)
        return self.D[n]

    def set(self, n, rot=None, loc=None, about=None):
        """Rotate bone n (degrees XYZ in world axes, or a Quaternion) about its head (or `about`), then move it."""
        assert n not in self.D, "%s posed after it was used" % n
        h = self.head[n] if about is None else Vector(about)
        M = Matrix.Translation(h) @ quat(rot).to_matrix().to_4x4() @ Matrix.Translation(-h)
        if loc is not None:
            M = Matrix.Translation(Vector(loc)) @ M
        self.L[n] = M

    def sym(self, n, rot=None, loc=None):
        """Poses an _L bone and its _R twin with the mirrored motion."""
        self.set(n, rot, loc)
        self.set(flip(n), mirror_rot(rot), mirror_loc(loc))

    def lock(self, n, rot=None, loc=None):
        """Gives bone n this world rotation (identity: its rest orientation), whatever its parents do."""
        qp = self.d(self.parent[n]).to_quaternion()
        self.set(n, qp.inverted() @ quat(rot), loc)

    def ik(self, upper, lower, target, pole=None):
        """Two-bone IK: the tail of `lower` reaches `target` (world); the bend stays on the rest side."""
        Dp = self.d(self.parent[upper])
        P = Dp.inverted() @ Vector(target)
        H, K0, A0 = self.head[upper], self.head[lower], self.tail[lower]
        L1, L2 = (K0 - H).length, (A0 - K0).length
        v = P - H
        d = max(abs(L1 - L2) + 1e-4, min(L1 + L2 - 1e-4, v.length))
        u = v.normalized()
        if pole is None:
            ax = (A0 - H).normalized()
            pole = K0 + (K0 - (H + ax * (K0 - H).dot(ax)))
        pv = Vector(pole) - H
        pv = (pv - u * pv.dot(u)).normalized()
        a = math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
        K = H + (u * math.cos(a) + pv * math.sin(a)) * L1
        A = H + u * d
        q1 = (K0 - H).rotation_difference(K - H)
        q2 = (q1 @ (A0 - K0)).rotation_difference(A - K)
        self.set(upper, q1)
        self.set(lower, q1.inverted() @ q2 @ q1)


def channelbag(act, slot):
    from bpy_extras import anim_utils
    return anim_utils.action_get_channelbag_for_slot(act, slot)


def bake(rig, P, name, nframes, fn, loop):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad = rig.animation_data or rig.animation_data_create()
    ad.action = act
    prev = {}
    for f in range(nframes + 1):
        P.clear()
        fn(P, f / nframes)
        for b in P.names:
            pb = rig.pose.bones[b]
            M = P.irest[b] @ P.L.get(b, I4) @ P.rest[b]
            loc, rq, _ = M.decompose()
            if b in prev:
                rq.make_compatible(prev[b])
            prev[b] = rq
            pb.location, pb.rotation_quaternion, pb.scale = loc, rq, (1, 1, 1)
            pb.keyframe_insert("location", frame=f, group=b)
            pb.keyframe_insert("rotation_quaternion", frame=f, group=b)
    try:
        for fc in channelbag(act, ad.action_slot).fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    except Exception as e:                       # interpolation is cosmetic: the exporter samples every frame
        print("[shardfall] interpolation not set:", e)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, nframes
    act.use_cyclic = loop
    return act


def rest_pose(rig):
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    bpy.context.view_layer.update()


def use_action(rig, act, frame):
    rig.animation_data.action = act
    try:
        if rig.animation_data.action_slot is None and len(act.slots):
            rig.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


# --- gaits ---------------------------------------------------------------------------------------------------

def foot_path(p, stride, duty, lift):
    """Foot offset along Y and up, and a toe factor, at gait phase p: stance slides the foot from the front
    (-Y) to the back, the swing lifts it on a smooth arc back to the front."""
    p %= 1.0
    if p < duty:
        return -stride / 2 + stride * p / duty, 0.0, 0.0
    s = (p - duty) / (1 - duty)
    e = (1 - math.cos(math.pi * s)) / 2
    return stride / 2 - stride * e, lift * math.sin(math.pi * s), math.sin(2 * math.pi * s)


def bump(p, peak=0.3):
    """A periodic dip shape: 0 at p = 0 and 1, peaking near `peak`."""
    p %= 1.0
    return (1 - math.cos(2 * math.pi * p ** (math.log(0.5) / math.log(peak)))) / 2


def plant_legs(P, legs, offsets=None):
    """Two-bone IK keeps each foot at its rest place (plus an offset) with the sole flat."""
    for i, (th, sh, ft) in enumerate(legs):
        tgt = P.head[ft].copy()
        toe = 0.0
        if offsets:
            dy, dz, toe = offsets[i]
            tgt += Vector((0, dy, dz))
        P.ik(th, sh, tgt)
        P.lock(ft, (toe, 0, 0))


def biped_walk(P, t, c):
    """A biped gait cycle; c holds stride, duty, lift, bob, crouch, sway, roll, yaw, lean, toe, stomp."""
    w = 2 * math.pi * t
    z = -c["crouch"] - c["bob"] * math.cos(2 * w - 0.63) - c.get("stomp", 0.0) * bump(2 * t, 0.12)
    P.set("pelvis", (c["lean"] * 0.4, -c["roll"] * math.sin(w - 0.3), -c["yaw"] * math.cos(w)),
          (c["sway"] * math.sin(w - 0.3), 0, z))
    offs = []
    for ph in (0.0, 0.5):
        dy, dz, toe = foot_path(t + ph, c["stride"], c["duty"], c["lift"])
        a = math.radians(c["toe"] * toe)          # toe down lowers the toe tip, toe up the heel: lift to clear
        dz += c["toe_len"] * math.sin(max(0.0, a)) + c["heel_len"] * math.sin(max(0.0, -a))
        offs.append((dy, dz, c["toe"] * toe))
    plant_legs(P, [("thigh_L", "shin_L", "foot_L"), ("thigh_R", "shin_R", "foot_R")], offs)
    P.set("chest", (c["lean"] * 0.6 + c["bob_pitch"] * math.cos(2 * w), c["roll"] * 0.5 * math.sin(w - 0.3),
                    c["yaw"] * 1.6 * math.cos(w)))
    return w


# --- the units ---------------------------------------------------------------------------------------------
# Each builder fills the kit and the skeleton (design coordinates, ground z = 0, front -Y, the robot's left at
# +X) and returns a spec: muzzle (bone, point), animation functions and their lengths in frames.

def lancer(k, sk):
    HIP, KNEE, ANK, TOE = Vector((0.12, 0.02, 0.46)), Vector((0.12, -0.05, 0.27)), Vector((0.12, 0.02, 0.085)), Vector((0.12, -0.12, 0.05))
    SH = Vector((0.25, 0.03, 0.84))
    EL_L, HA_L = Vector((0.17, -0.17, 0.68)), Vector((-0.06, -0.37, 0.64))
    EL_R, HA_R = Vector((-0.25, -0.02, 0.66)), Vector((-0.06, -0.18, 0.63))
    RX, RZ = -0.06, 0.69                        # the rifle's centre line
    sk.bone("root", (0, 0, 0), (0, 0.2, 0))
    sk.bone("pelvis", (0, 0.02, 0.50), (0, 0.02, 0.60), "root")
    sk.bone("chest", (0, 0.03, 0.60), (0, 0.03, 0.90), "pelvis")
    sk.bone("head", (0, 0.0, 0.93), (0, 0.0, 1.08), "chest")
    sk.bone("thigh_L", HIP, KNEE, "pelvis", True)
    sk.bone("shin_L", KNEE, ANK, "thigh_L", True)
    sk.bone("foot_L", ANK, TOE, "shin_L", True)
    sk.bone("upperarm_L", SH, EL_L, "chest")
    sk.bone("forearm_L", EL_L, HA_L, "upperarm_L")
    sk.bone("upperarm_R", (-SH.x, SH.y, SH.z), EL_R, "chest")
    sk.bone("forearm_R", EL_R, HA_R, "upperarm_R")
    sk.bone("rifle", HA_R, (RX, -0.45, RZ), "chest")

    # legs: graphite joints, cream thigh and shin armour, gold knee caps, chunky feet
    k.add("foot_L", V.xf(V.rbox(0.15, 0.26, 0.045, 0.02), (0.12, -0.035, 0.0225)), "graphite", True)
    k.add("foot_L", V.xf(V.rbox(0.13, 0.19, 0.06, 0.03, top=(0.8, 0.75)), (0.12, -0.02, 0.07)), "cream", True)
    k.add("foot_L", V.xf(V.rbox(0.135, 0.06, 0.05, 0.02), (0.12, -0.145, 0.04)), "gold", True)
    k.add("foot_L", ell(ANK, 0.045, 0.045, 0.045, 12, 6), "graphite", True)
    k.add("shin_L", limb_box(KNEE, ANK, 0.115, 0.125, 0.04, -0.03, -0.035), "cream", True)
    k.add("shin_L", V.xf(V.rbox(0.10, 0.06, 0.09, 0.025), KNEE + Vector((0, -0.05, -0.01))), "gold", True)
    k.add("shin_L", V.xf(V.lathe([(0, -0.055), (0.045, -0.055), (0.045, 0.055), (0, 0.055)], 12), KNEE, (0, 90, 0)), "graphite", True)
    k.add("thigh_L", limb_cyl(HIP, KNEE, 0.04, 10), "graphite", True)
    k.add("thigh_L", limb_box(HIP + Vector((0.008, 0, 0)), KNEE + Vector((0.008, 0, 0)), 0.11, 0.11, 0.035, -0.035, -0.06), "cream", True)
    # pelvis and waist
    k.add("pelvis", ell(HIP, 0.055, 0.055, 0.055, 12, 6), "graphite", True)
    k.add("pelvis", V.xf(V.rbox(0.30, 0.18, 0.12, 0.045), (0, 0.02, 0.49)), "graphite")
    k.add("pelvis", V.xf(V.rbox(0.31, 0.19, 0.035, 0.015), (0, 0.02, 0.545)), "gold")
    k.add("pelvis", V.xf(V.rbox(0.12, 0.05, 0.10, 0.03, top=(1.0, 0.6)), (0, -0.08, 0.475)), "cream")
    k.add("pelvis", V.xf(V.lathe([(0, 0.52), (0.10, 0.52), (0.10, 0.63), (0, 0.63)], 14), (0, 0.03, 0)), "graphite")
    # chest: cream torso, gold collar and stripes, a cyan core, the team band, a backpack with glowing cells
    k.add("chest", V.xf(V.rbox(0.40, 0.30, 0.30, 0.10, top=(1.10, 1.0)), (0, 0.03, 0.76)), "cream")
    k.add("chest", V.xf(V.lathe([(0, 0), (0.11, 0), (0.12, 0.02), (0.11, 0.045), (0, 0.045)], 16), (0, 0.01, 0.895)), "gold")
    k.add("chest", V.xf(V.rbox(0.035, 0.03, 0.20, 0.012), (0.105, -0.115, 0.77)), "gold", True)
    disc(k, "chest", (0, -0.11, 0.77), (90, 0, 0), 0.05, "gold", 0.03, 14)
    k.add("chest", V.xf(V.rbox(0.34, 0.03, 0.045, 0.012), (0, -0.115, 0.655)), "team")
    k.add("chest", V.xf(V.rbox(0.28, 0.12, 0.24, 0.05), (0, 0.19, 0.78)), "graphite")
    k.add("chest", V.xf(V.rbox(0.30, 0.13, 0.04, 0.015), (0, 0.19, 0.905)), "gold")
    k.add("chest", V.xf(V.lathe(V.capsule(0.032, 0.17), 10), (0.075, 0.248, 0.68)), "glow_cyan", True)
    # shoulders: graphite balls, cream pauldrons with a gold rim and a team stripe
    k.add("chest", ell(SH, 0.055, 0.055, 0.055, 12, 6), "graphite", True)
    k.add("chest", V.xf(V.rbox(0.21, 0.24, 0.12, 0.05, top=(0.8, 0.85)), (0.33, 0.03, 0.885)), "cream", True)
    k.add("chest", V.xf(V.rbox(0.22, 0.25, 0.035, 0.015), (0.33, 0.03, 0.83)), "gold", True)
    k.add("chest", V.xf(V.rbox(0.06, 0.20, 0.03, 0.012), (0.33, 0.03, 0.94)), "team", True)
    # head: the drone's face on a helmet, gold ear fins and a crest strap
    k.add("head", V.xf(V.lathe([(0, 0.89), (0.05, 0.89), (0.05, 0.96), (0, 0.96)], 12), (0, 0.0, 0)), "graphite")
    k.add("head", ell((0, 0.0, 1.01), 0.12, 0.125, 0.10, 18, 9), "cream")
    k.add("head", V.xf(V.rbox(0.17, 0.06, 0.09, 0.03), (0, -0.10, 0.995)), "graphite")
    k.add("head", V.xf(V.rbox(0.13, 0.03, 0.035, 0.015), (0, -0.128, 1.0)), "glow_cyan")
    k.add("head", strap(0.0, 1.01, 0.125, 0.10, -10, 150, -0.018, 0.018, "x", 0.008, 0.02, 14), "gold")
    fin = [(-0.04, -0.01), (0.05, -0.01), (0.11, 0.14), (0.06, 0.145)]
    k.add("head", V.xf(V.prism(fin, -0.015, 0.015, "x", 0.012, 2), (0.112, 0.0, 1.01), (0, 12, 0)), "gold", True)
    # arms: graphite upper arms with cream sleeves, cream forearms with gold cuffs, graphite hands
    for ua, fa, s, e, hnd in (("upperarm_L", "forearm_L", SH, EL_L, HA_L), ("upperarm_R", "forearm_R", Vector((-SH.x, SH.y, SH.z)), EL_R, HA_R)):
        k.add(ua, limb_cyl(s, e, 0.036, 10), "graphite")
        k.add(ua, limb_box(s, e, 0.085, 0.085, 0.03, -0.06, -0.04), "cream")
        k.add(ua, ell(e, 0.045, 0.045, 0.045, 12, 6), "graphite")
        k.add(fa, limb_box(e, hnd, 0.085, 0.085, 0.03, -0.025, -0.045), "cream")
        k.add(fa, limb_box(e, hnd, 0.095, 0.095, 0.03, -((hnd - e).length - 0.085), -0.035), "gold")
        k.add(fa, V.xf(V.rbox(0.06, 0.07, 0.07, 0.025), hnd), "graphite")
    # the energy rifle
    R = "rifle"
    k.add(R, V.xf(V.rbox(0.075, 0.28, 0.10, 0.03), (RX, -0.265, RZ)), "graphite")
    k.add(R, V.xf(V.rbox(0.085, 0.25, 0.05, 0.022, top=(0.85, 0.95)), (RX, -0.27, RZ + 0.065)), "cream")
    k.add(R, V.xf(V.rbox(0.088, 0.035, 0.052, 0.012), (RX, -0.31, RZ + 0.066)), "gold")
    k.add(R, V.xf(V.rbox(0.065, 0.07, 0.11, 0.025), (RX, -0.15, RZ - 0.015)), "cream")
    k.add(R, V.xf(V.rbox(0.042, 0.045, 0.085, 0.015), (RX, -0.19, RZ - 0.075), (14, 0, 0)), "graphite")
    k.add(R, V.xf(V.rbox(0.045, 0.05, 0.06, 0.015), (RX, -0.37, RZ - 0.06)), "graphite")
    k.add(R, V.xf(V.rbox(0.083, 0.10, 0.026, 0.01), (RX, -0.245, RZ)), "glow_cyan")
    k.add(R, V.xf(V.lathe([(0, 0), (0.022, 0), (0.022, 0.17), (0, 0.17)], 10), (RX, -0.40, RZ), (90, 0, 0)), "graphite_lt")
    k.add(R, V.xf(V.lathe([(0, 0), (0.027, 0), (0.027, 0.125), (0, 0.125)], 12), (RX, -0.41, RZ), (90, 0, 0)), "gold")
    for y in (-0.43, -0.47, -0.51):
        k.add(R, V.xf(V.lathe([(0, 0), (0.036, 0), (0.036, 0.02), (0, 0.02)], 12), (RX, y, RZ), (90, 0, 0)), "glow_cyan")
    k.add(R, V.xf(V.lathe([(0, 0), (0.03, 0), (0.042, 0.03), (0.042, 0.045), (0, 0.045)], 12), (RX, -0.545, RZ), (90, 0, 0)), "gold")
    k.add(R, V.xf(V.lathe([(0, 0), (0.03, 0), (0.026, 0.015), (0.012, 0.026), (0, 0.028)], 10), (RX, -0.588, RZ), (90, 0, 0)), "glow_cyan")
    k.add(R, V.xf(V.rbox(0.03, 0.06, 0.035, 0.01), (RX, -0.25, RZ + 0.10)), "graphite")
    k.add(R, V.xf(V.lathe([(0, 0), (0.022, 0), (0.022, 0.14), (0, 0.14)], 10), (RX, -0.19, RZ + 0.125), (90, 0, 0)), "graphite")
    k.add(R, V.xf(V.lathe([(0, 0), (0.017, 0), (0.012, 0.01), (0, 0.012)], 8), (RX, -0.33, RZ + 0.125), (90, 0, 0)), "glow_cyan")

    legs = [("thigh_L", "shin_L", "foot_L"), ("thigh_R", "shin_R", "foot_R")]

    def arms_on_rifle(P):
        D = P.d("rifle")
        P.ik("upperarm_L", "forearm_L", D @ P.tail["forearm_L"])
        P.ik("upperarm_R", "forearm_R", D @ P.tail["forearm_R"])

    def idle(P, t):
        w = 2 * math.pi * t
        P.set("pelvis", (0, 0.8 * math.sin(w), 0.8 * math.sin(w + 0.4)), (0.007 * math.sin(w), 0, -0.005 - 0.004 * math.cos(2 * w)))
        plant_legs(P, legs)
        P.set("chest", (1.2 * math.sin(2 * w + 0.5), -0.6 * math.sin(w), 3.0 * math.sin(w + 0.9)))
        P.set("head", (3.0 * math.sin(2 * w + 1.2), 0, 26.0 * math.sin(w)))
        P.set("rifle", (1.5 * math.sin(2 * w + 1.0), 0, -2.0 * math.sin(w + 0.9)))
        arms_on_rifle(P)

    def walk(P, t):
        w = biped_walk(P, t, dict(stride=0.30, duty=0.58, lift=0.075, bob=0.012, crouch=0.028, sway=0.012, roll=2.5,
                                  yaw=4.0, lean=6.0, toe=16.0, bob_pitch=1.0, toe_len=0.19, heel_len=0.08))
        P.set("head", (-3.0, 0, -6.0 * math.cos(w)))
        P.set("rifle", (1.5 * math.sin(2 * w - 0.4), 0, -2.0 * math.cos(w)), (0, 0, 0.008 * math.sin(2 * w - 1.0)))
        arms_on_rifle(P)

    N_ATK, FIRE = 14, 3

    def attack(P, t):
        f = t * N_ATK
        aim = smooth(f / FIRE) * (1 - smooth((f - 7) / (N_ATK - 7)))
        k_ = 0.0 if f < FIRE else (1 - clamp01((f - FIRE) / (N_ATK - FIRE))) ** 3
        P.set("pelvis", (1.5 * aim, 0, 0), (0, 0.008 * k_, -0.012 * aim))
        plant_legs(P, legs)
        P.set("chest", (2.0 * aim - 4.0 * k_, 0, 0))
        P.set("head", (-1.0 * aim - 2.0 * k_, 0, 0))
        P.set("rifle", (1.0 * aim - 9.0 * k_, 0, 0), (0, 0.055 * k_, 0.012 * k_))
        arms_on_rifle(P)

    return {"muzzle": ("rifle", Vector((RX, -0.615, RZ))),
            "actions": [("idle_loop", 72, idle, True), ("walk_loop", 24, walk, True), ("attack", N_ATK, attack, False)],
            "attack_fire_frame": FIRE}


def bulwark(k, sk):
    HIP, KNEE, ANK, TOE = Vector((0.20, 0.03, 0.70)), Vector((0.21, -0.07, 0.42)), Vector((0.21, 0.03, 0.13)), Vector((0.21, -0.20, 0.06))
    SH, EL = Vector((0.40, 0.04, 1.24)), Vector((0.50, 0.02, 0.98))
    HA_L = Vector((0.49, -0.26, 0.98))
    CX, CZ = -0.50, 0.965                        # the arm cannon's bore
    sk.bone("root", (0, 0, 0), (0, 0.3, 0))
    sk.bone("pelvis", (0, 0.03, 0.76), (0, 0.03, 0.88), "root")
    sk.bone("chest", (0, 0.04, 0.88), (0, 0.04, 1.30), "pelvis")
    sk.bone("head", (0, -0.02, 1.36), (0, -0.02, 1.52), "chest")
    sk.bone("thigh_L", HIP, KNEE, "pelvis", True)
    sk.bone("shin_L", KNEE, ANK, "thigh_L", True)
    sk.bone("foot_L", ANK, TOE, "shin_L", True)
    sk.bone("upperarm_L", SH, EL, "chest", True)
    sk.bone("forearm_L", EL, HA_L, "upperarm_L")
    sk.bone("forearm_R", (-EL.x, EL.y, EL.z), (CX, -0.40, CZ), "upperarm_R")
    sk.bone("barrel_R", (CX, -0.40, CZ), (CX, -0.62, CZ), "forearm_R")

    # legs
    k.add("foot_L", V.xf(V.rbox(0.23, 0.38, 0.06, 0.025), (0.21, -0.045, 0.03)), "graphite", True)
    k.add("foot_L", V.xf(V.rbox(0.21, 0.28, 0.11, 0.045, top=(0.85, 0.75)), (0.21, -0.02, 0.105)), "cream", True)
    k.add("foot_L", V.xf(V.rbox(0.215, 0.09, 0.075, 0.03), (0.21, -0.205, 0.055)), "gold", True)
    k.add("foot_L", ell(ANK, 0.065, 0.065, 0.065, 12, 6), "graphite", True)
    k.add("shin_L", limb_box(KNEE + Vector((0, -0.015, 0)), ANK + Vector((0, -0.015, 0)), 0.20, 0.22, 0.06, -0.04, -0.05, top=(0.88, 0.9)), "cream", True)
    k.add("shin_L", V.xf(V.rbox(0.17, 0.09, 0.15, 0.04), KNEE + Vector((0, -0.09, 0.0))), "gold", True)
    k.add("shin_L", V.xf(V.lathe([(0, -0.085), (0.07, -0.085), (0.07, 0.085), (0, 0.085)], 14), KNEE, (0, 90, 0)), "graphite", True)
    k.add("thigh_L", limb_cyl(HIP, KNEE, 0.07, 12), "graphite", True)
    k.add("thigh_L", limb_box(HIP + Vector((0.02, 0, 0)), KNEE + Vector((0.02, 0, 0)), 0.17, 0.17, 0.05, -0.05, -0.08), "cream", True)
    # pelvis
    k.add("pelvis", ell(HIP, 0.085, 0.085, 0.085, 12, 6), "graphite", True)
    k.add("pelvis", V.xf(V.rbox(0.44, 0.28, 0.16, 0.06), (0, 0.03, 0.76)), "graphite")
    k.add("pelvis", V.xf(V.rbox(0.46, 0.30, 0.05, 0.02), (0, 0.03, 0.835)), "gold")
    k.add("pelvis", V.xf(V.rbox(0.24, 0.05, 0.17, 0.03, top=(1.0, 0.7)), (0, -0.13, 0.72), (-10, 0, 0)), "cream")
    k.add("pelvis", V.xf(V.lathe([(0, 0.80), (0.16, 0.80), (0.16, 0.94), (0, 0.94)], 16), (0, 0.04, 0)), "graphite")
    # chest: barrel torso, grille with cyan slits, gold collar and band, a big reactor backpack
    k.add("chest", V.xf(V.rbox(0.64, 0.48, 0.46, 0.14, top=(1.12, 1.0)), (0, 0.04, 1.13)), "cream")
    k.add("chest", V.xf(V.rbox(0.62, 0.47, 0.06, 0.03), (0, 0.04, 0.955)), "gold")
    k.add("chest", V.xf(V.rbox(0.34, 0.05, 0.15, 0.04), (0, -0.195, 1.19)), "graphite")
    for x in (-0.1, 0.0, 0.1):
        k.add("chest", V.xf(V.rbox(0.065, 0.03, 0.035, 0.014), (x, -0.22, 1.19)), "glow_cyan")
    k.add("chest", V.xf(V.lathe([(0.10, 0), (0.17, 0), (0.18, 0.03), (0.17, 0.06), (0.10, 0.06)], 18, closed=True), (0, 0.0, 1.33)), "gold")
    k.add("chest", V.xf(V.rbox(0.48, 0.22, 0.40, 0.07), (0, 0.33, 1.14)), "graphite")
    for x in (-0.15, 0.15):
        k.add("chest", V.xf(V.lathe([(0, 0), (0.055, 0), (0.055, 0.25), (0.045, 0.27), (0, 0.27)], 12), (x, 0.39, 1.20)), "gold")
        k.add("chest", V.xf(V.lathe([(0, 0), (0.042, 0), (0.038, 0.02), (0, 0.025)], 12), (x, 0.39, 1.465)), "glow_cyan")
    k.add("chest", V.xf(V.rbox(0.26, 0.03, 0.11, 0.02), (0, 0.445, 1.10)), "glow_cyan")
    # shoulders: graphite balls, huge pauldrons with gold rims and team stripes
    k.add("chest", ell(SH, 0.10, 0.10, 0.10, 14, 7), "graphite", True)
    k.add("chest", V.xf(V.rbox(0.30, 0.40, 0.22, 0.09, top=(0.78, 0.85)), (0.47, 0.04, 1.33)), "cream", True)
    k.add("chest", V.xf(V.rbox(0.31, 0.41, 0.05, 0.02), (0.47, 0.04, 1.235)), "gold", True)
    k.add("chest", V.xf(V.rbox(0.09, 0.34, 0.03, 0.012), (0.47, 0.04, 1.435)), "team", True)
    # head: small, sunk between the pauldrons, a slit visor and a gold crest
    k.add("head", V.xf(V.lathe([(0, 1.32), (0.08, 1.32), (0.08, 1.40), (0, 1.40)], 12), (0, -0.02, 0)), "graphite")
    k.add("head", ell((0, -0.02, 1.43), 0.14, 0.15, 0.11, 18, 9), "cream")
    k.add("head", V.xf(V.rbox(0.18, 0.06, 0.09, 0.03), (0, -0.15, 1.42)), "graphite")
    k.add("head", V.xf(V.rbox(0.14, 0.03, 0.03, 0.013), (0, -0.178, 1.425)), "glow_cyan")
    crest = [(-0.10, 1.47), (0.10, 1.49), (0.06, 1.60), (-0.03, 1.59)]
    k.add("head", V.prism(crest, -0.018, 0.018, "x", 0.012, 2), "gold")
    # upper arms (both sides alike)
    k.add("upperarm_L", limb_cyl(SH, EL, 0.065, 12), "graphite", True)
    k.add("upperarm_L", limb_box(SH, EL, 0.14, 0.14, 0.045, -0.08, -0.05), "cream", True)
    k.add("upperarm_L", ell(EL, 0.075, 0.075, 0.075, 12, 6), "graphite", True)
    # shield arm: cream gauntlet, a bracket, the curved tower shield facing front-left
    F = "forearm_L"
    k.add(F, limb_box(EL, HA_L, 0.15, 0.15, 0.05, 0.0, 0.0), "cream")
    k.add(F, limb_box(EL, HA_L, 0.16, 0.16, 0.04, -0.17, 0.01), "gold")
    k.add(F, V.xf(V.rbox(0.10, 0.12, 0.14, 0.03), (0.46, -0.33, 0.95)), "graphite")
    SC, SROT = Vector((0.37, -0.42, 0.90)), 20.0

    def shield_part(bm, key, bend=0.25):
        for v in bm.verts:
            v.co.y += bend * v.co.x * v.co.x
        k.add(F, V.xf(bm, SC, (0, 0, SROT)), key)
    outline = [(-0.28, -0.30), (-0.16, -0.44), (0.16, -0.44), (0.28, -0.30), (0.28, 0.40), (0.22, 0.44), (-0.22, 0.44), (-0.28, 0.40)]
    shield_part(V.prism(outline, -0.035, 0.035, "y", 0.03, 2), "cream")
    shield_part(V.prism(V.offset_poly(outline, 0.03), -0.02, 0.045, "y", 0.02, 2), "gold")
    shield_part(V.xf(V.rbox(0.20, 0.05, 0.28, 0.05), (0, -0.045, 0.02)), "graphite")
    for s in (-1, 1):
        shield_part(V.xf(V.rbox(0.11, 0.03, 0.03, 0.012), (s * 0.04, -0.075, 0.0), (0, s * 32, 0)), "glow_cyan")
    shield_part(V.xf(V.rbox(0.50, 0.03, 0.06, 0.015), (0, -0.045, 0.30)), "team")
    # cannon arm: housing, shroud, gold rings, glowing slots; the barrel slides on its own bone
    F = "forearm_R"
    k.add(F, V.xf(V.lathe([(0, 0), (0.12, 0), (0.13, 0.03), (0.13, 0.45), (0.12, 0.48), (0, 0.48)], 18), (CX, 0.08, CZ), (90, 0, 0)), "graphite")
    k.add(F, V.xf(V.rbox(0.24, 0.40, 0.10, 0.04, top=(0.8, 0.9)), (CX, -0.14, CZ + 0.11)), "cream")
    for y in (-0.03, -0.31):
        k.add(F, V.xf(V.lathe([(0, 0), (0.142, 0), (0.142, 0.045), (0, 0.045)], 18), (CX, y, CZ), (90, 0, 0)), "gold")
    for y in (-0.08, -0.15, -0.22):
        k.add(F, V.xf(V.rbox(0.12, 0.035, 0.02, 0.008), (CX, y, CZ + 0.165)), "glow_cyan")
    k.add(F, V.xf(V.rbox(0.03, 0.18, 0.06, 0.012), (CX - 0.13, -0.17, CZ)), "glow_cyan")
    B = "barrel_R"
    k.add(B, V.xf(V.lathe([(0, 0), (0.075, 0), (0.075, 0.20), (0, 0.20)], 14), (CX, -0.38, CZ), (90, 0, 0)), "graphite_lt")
    k.add(B, V.xf(V.lathe([(0, 0), (0.09, 0), (0.11, 0.05), (0.11, 0.08), (0.09, 0.09), (0, 0.09)], 16), (CX, -0.56, CZ), (90, 0, 0)), "gold")
    k.add(B, V.xf(V.lathe([(0, 0), (0.075, 0), (0.06, 0.02), (0.03, 0.03), (0, 0.032)], 14), (CX, -0.645, CZ), (90, 0, 0)), "glow_cyan")

    legs = [("thigh_L", "shin_L", "foot_L"), ("thigh_R", "shin_R", "foot_R")]

    def idle(P, t):
        w = 2 * math.pi * t
        P.set("pelvis", (0, 0.6 * math.sin(w), 0.6 * math.sin(w + 0.5)), (0.008 * math.sin(w), 0, -0.006 - 0.005 * math.cos(2 * w)))
        plant_legs(P, legs)
        P.set("chest", (1.5 * math.sin(2 * w + 0.4), -0.5 * math.sin(w), 2.5 * math.sin(w + 1.0)))
        P.set("head", (2.5 * math.sin(2 * w + 1.0), 0, 20.0 * math.sin(w)))
        P.set("upperarm_L", (2.0 * math.sin(2 * w + 0.8), 0, 0))
        P.set("forearm_L", (-1.5 * math.sin(2 * w + 1.2), 0, 1.5 * math.sin(w)))
        P.set("upperarm_R", (2.5 * math.sin(2 * w + 0.3), 0, 0))
        P.set("forearm_R", (-3.0 * math.sin(2 * w + 0.9), 0, -1.5 * math.sin(w + 0.5)))

    def walk(P, t):
        w = biped_walk(P, t, dict(stride=0.34, duty=0.60, lift=0.09, bob=0.018, crouch=0.04, sway=0.025, roll=3.0,
                                  yaw=4.0, lean=5.0, toe=14.0, bob_pitch=1.5, stomp=0.018, toe_len=0.27, heel_len=0.10))
        P.set("head", (-2.0, 0, -5.0 * math.cos(w)))
        P.set("upperarm_L", (6.0 * math.cos(w), 0, 0))
        P.set("forearm_L", (-2.0 * math.cos(w), 0, 0))
        P.set("upperarm_R", (-6.0 * math.cos(w), 0, 0))
        P.set("forearm_R", (2.0 * math.cos(w) + 1.5 * math.sin(2 * w), 0, 0))

    N_ATK, FIRE = 16, 4

    def attack(P, t):
        f = t * N_ATK
        b = smooth(f / FIRE) * (1 - smooth((f - 9) / (N_ATK - 9)))
        u = clamp01((f - FIRE) / (N_ATK - FIRE))
        k_ = 0.0 if f < FIRE else (1 - u) ** 3
        kf = 0.0 if f < FIRE else (1 - clamp01(u * 1.6)) ** 2
        P.set("pelvis", (3.0 * b, 0, 0), (0, 0.015 * k_, -0.04 * b))
        plant_legs(P, legs)
        P.set("chest", (3.0 * b - 6.0 * k_, 0, -3.0 * b))
        P.set("head", (-2.0 * b - 2.0 * k_, 0, 3.0 * b))
        P.set("upperarm_L", (-12.0 * b, 0, 0))
        P.set("forearm_L", (8.0 * b, 0, 0))
        P.set("upperarm_R", (-3.0 * b + 9.0 * k_, 0, 0))
        P.set("forearm_R", (2.0 * b - 14.0 * k_, 0, 0))
        P.set("barrel_R", None, (0, 0.11 * kf, 0))

    return {"muzzle": ("barrel_R", Vector((CX, -0.68, CZ))),
            "actions": [("idle_loop", 84, idle, True), ("walk_loop", 28, walk, True), ("attack", N_ATK, attack, False)],
            "attack_fire_frame": FIRE}


def sovereign(k, sk):
    BZ = 2.62                                    # hull centre height
    RXH, RYH, RZH = 1.15, 1.30, 0.80             # hull radii
    sk.bone("root", (0, 0, 0), (0, 0.6, 0))
    sk.bone("body", (0, 0, BZ), (0, 0, BZ + 0.6), "root")
    sk.bone("head", (0, -0.05, 3.30), (0, -0.05, 3.80), "body")
    sk.bone("cannon", (0, -0.55, 3.55), (0, -1.40, 3.55), "head")
    sk.bone("coil", (0, -1.62, 3.55), (0, -1.80, 3.55), "cannon")

    # --- hull: graphite chassis, cream dome with gold and team gores, the drone face, a rear reactor ---
    B = "body"
    k.add(B, ell((0, 0, BZ), 1.04, 1.16, 0.56, 28, 6, -1.0, 0.05), "graphite")
    k.add(B, V.xf(V.lathe([(0, 0), (0.30, 0), (0.24, 0.05), (0, 0.06)], 16), (0, 0, BZ - 0.60)), "glow_cyan")
    k.add(B, ell((0, 0, BZ), RXH, RYH, RZH, 32, 10, -0.16, 1.0), "cream")
    band = [(1.10, -0.13), (1.175, -0.11), (1.185, -0.02), (1.15, 0.02), (1.10, 0.02)]
    k.add(B, V.xf(V.lathe(band, 32, closed=True), (0, 0, BZ), (0, 0, 0), (1.0, RYH / RXH, 1.0)), "gold")
    prof = [(math.cos(math.radians(a)) * RXH, math.sin(math.radians(a)) * RZH) for a in range(4, 83, 8)]
    for az, key, wdt in ((-50, "gold", 9), (-130, "gold", 9), (50, "gold", 9), (130, "gold", 9), (0, "team", 12), (180, "team", 12)):
        k.add(B, V.xf(gore(prof, az - wdt / 2, az + wdt / 2, 3, 0.014, 0.04), (0, 0, BZ), (0, 0, 0), (1.0, RYH / RXH, 1.0)), key)
    k.add(B, V.xf(V.rbox(0.84, 0.18, 0.36, 0.08), (0, -1.255, 2.74), (-14, 0, 0)), "graphite")
    k.add(B, V.xf(V.rbox(0.60, 0.06, 0.10, 0.04), (0, -1.345, 2.765), (-14, 0, 0)), "glow_cyan")
    for s in (-1, 1):
        k.add(B, V.xf(V.rbox(0.08, 0.06, 0.30, 0.025), (s * 0.48, -1.25, 2.74), (-14, 0, s * -18)), "gold")
    k.add(B, V.xf(V.rbox(0.72, 0.34, 0.42, 0.10), (0, 1.22, 2.80)), "graphite")
    k.add(B, V.xf(V.rbox(0.78, 0.30, 0.06, 0.03), (0, 1.22, 3.03)), "gold")
    for x in (-0.20, 0.0, 0.20):
        k.add(B, V.xf(V.rbox(0.09, 0.04, 0.26, 0.03), (x, 1.40, 2.80)), "glow_cyan")

    # --- head (turret): ring, cream block, gold trims, glowing reactor orb, tall ear fins, team stripes ---
    T = "head"
    k.add(T, V.xf(V.lathe([(0, 0), (0.62, 0), (0.64, 0.03), (0.64, 0.10), (0, 0.10)], 28), (0, -0.05, 3.22)), "graphite")
    k.add(T, V.xf(V.rbox(1.05, 1.25, 0.46, 0.18, top=(0.86, 0.88)), (0, 0.0, 3.56)), "cream")
    k.add(T, V.xf(V.rbox(0.06, 0.95, 0.16, 0.03), (0.52, 0.02, 3.50)), "gold", True)
    k.add(T, V.xf(V.rbox(0.08, 0.70, 0.03, 0.012), (0.20, 0.05, 3.79)), "team", True)
    k.add(T, V.xf(V.lathe([(0, 0), (0.30, 0), (0.30, 0.06), (0.25, 0.12), (0, 0.12)], 20), (0, 0.42, 3.74)), "graphite")
    k.add(T, ell((0, 0.42, 3.92), 0.20, 0.20, 0.20, 16, 8), "glow_cyan")
    k.add(T, V.xf(ring(0.20, 0.25, 0.05, 20), (0, 0.42, 3.86)), "gold")
    fin = [(-0.25, -0.07), (0.30, -0.07), (0.64, 0.98), (0.44, 1.00)]
    k.add(T, V.xf(V.prism(fin, -0.045, 0.045, "x", 0.025, 2), (0.47, 0.0, 3.62), (0, 10, 0)), "gold", True)
    finglow = [(-0.04, 0.10), (0.20, 0.10), (0.49, 0.86), (0.41, 0.87)]
    k.add(T, V.xf(V.prism(finglow, -0.058, -0.04, "x", 0.008, 1), (0.47, 0.0, 3.62), (0, 10, 0)), "glow_cyan", True)

    # --- the beam cannon: mantlet, cream housing, barrel with glowing coils, spinning coil collar, emitter ---
    C = "cannon"
    CY, CZ = -0.55, 3.55
    k.add(C, V.xf(V.rbox(0.62, 0.40, 0.50, 0.12), (0, -0.62, CZ)), "graphite")
    k.add(C, V.xf(V.rbox(0.52, 0.72, 0.40, 0.12, top=(0.85, 0.95)), (0, -1.02, CZ + 0.03)), "cream")
    k.add(C, V.xf(V.rbox(0.56, 0.08, 0.44, 0.12), (0, -0.84, CZ + 0.03)), "team")
    k.add(C, V.xf(V.rbox(0.56, 0.10, 0.44, 0.12), (0, -1.33, CZ + 0.02)), "gold")
    k.add(C, V.xf(V.lathe([(0, 0), (0.16, 0), (0.16, 0.86), (0, 0.86)], 20), (0, -1.30, CZ), (90, 0, 0)), "graphite_lt")
    for y in (-1.42, -1.88, -2.00):
        k.add(C, V.xf(V.lathe([(0, 0), (0.20, 0), (0.20, 0.06), (0, 0.06)], 20), (0, y, CZ), (90, 0, 0)), "glow_cyan")
    k.add(C, V.xf(V.lathe([(0, 0), (0.20, 0), (0.26, 0.10), (0.27, 0.18), (0.24, 0.22), (0, 0.22)], 24), (0, -2.08, CZ), (90, 0, 0)), "gold")
    k.add(C, V.xf(V.lathe([(0, 0), (0.18, 0), (0.15, 0.05), (0.08, 0.08), (0, 0.085)], 18), (0, -2.29, CZ), (90, 0, 0)), "glow_cyan")
    G = "coil"
    k.add(G, V.xf(V.lathe([(0.15, 0), (0.25, 0), (0.25, 0.16), (0.15, 0.16)], 24, closed=True), (0, -1.54, CZ), (90, 0, 0)), "gold")
    for a in (45, 135, 225, 315):
        r = math.radians(a)
        k.add(G, V.xf(V.rbox(0.10, 0.12, 0.07, 0.025), (0.27 * math.cos(r), -1.62, CZ + 0.27 * math.sin(r)), (0, -a + 90, 0)), "glow_cyan")

    # --- legs: hip housing (yaw), thigh up to a raised knee, a long shin down to a big round foot ---
    legs = []
    for tag, ang in (("FL", -40.0), ("BL", 40.0)):
        r = math.radians(ang)
        dr = Vector((math.cos(r), math.sin(r), 0))      # outward, in the leg's plane
        nrm = Vector((-dr.y, dr.x, 0))                    # the knee axis
        up = Vector((0, 0, 1))
        H = dr * 0.88 + Vector((0, 0, 2.40))
        K = H + dr * 0.62 + up * 0.62
        A = H + dr * 1.30
        A.z = 0.30
        hip, th, sh, ft = "hip_" + tag, "thigh_" + tag, "shin_" + tag, "foot_" + tag
        sk.bone(hip, H, H + up * 0.4, "body", True)
        sk.bone(th, H, K, hip, True)
        sk.bone(sh, K, A, th, True)
        sk.bone(ft, A, A + dr * 0.4, sh, True)
        legs.append((hip, th, sh, ft))
        legs.append((flip(hip), flip(th), flip(sh), flip(ft)))
        # hip housing: a graphite drum with a gold cap and a drone disc facing out
        k.add(hip, V.xf(V.lathe([(0, 0), (0.30, 0), (0.32, 0.04), (0.32, 0.40), (0.28, 0.46), (0, 0.46)], 20), H - up * 0.28), "graphite", True)
        k.add(hip, V.xf(ring(0.24, 0.335, 0.06, 20), H + up * 0.06), "gold", True)
        dq = Vector((0, 0, 1)).rotation_difference(dr).to_euler()
        disc(k, hip, H + dr * 0.28 - up * 0.10, [math.degrees(a) for a in dq], 0.17, "cream", 0.07, 18, mirror=True)
        # thigh: cream armour with a gold spine, a graphite piston underneath
        tn = (up - dr).normalized()                       # the thigh's upper face normal
        k.add(th, limb_box(H, K, 0.40, 0.44, 0.10, -0.05, -0.10), "cream", True)
        k.add(th, limb_box(H + tn * 0.21, K + tn * 0.21, 0.13, 0.08, 0.03, -0.10, -0.22), "gold", True)
        k.add(th, limb_cyl(H - tn * 0.18, K - tn * 0.20, 0.07, 10, e0=-0.15, e1=-0.20), "graphite_lt", True)
        # knee: a graphite drum across the leg with drone discs on both sides, a gold cap with a glowing eye on top
        kq = Vector((0, 0, 1)).rotation_difference(nrm).to_euler()
        k.add(th, V.xf(V.lathe([(0, -0.25), (0.26, -0.25), (0.28, -0.22), (0.28, 0.22), (0.26, 0.25), (0, 0.25)], 22), K, [math.degrees(a) for a in kq]), "graphite", True)
        for s in (1, -1):
            sq = Vector((0, 0, 1)).rotation_difference(nrm * s).to_euler()
            disc(k, th, K + nrm * s * 0.22, [math.degrees(a) for a in sq], 0.19, "gold", 0.06, 18, mirror=True)
        k.add(th, V.xf(V.rbox(0.36, 0.34, 0.14, 0.06, top=(0.8, 0.8)), K + up * 0.27, (0, 0, ang)), "gold", True)
        k.add(th, V.xf(V.lathe([(0, 0), (0.09, 0), (0.08, 0.04), (0.04, 0.07), (0, 0.075)], 14), K + up * 0.33), "glow_cyan", True)
        # shin: long tapered cream armour, a gold front plate, a team band, a graphite strut behind
        k.add(sh, limb_box(K, A, 0.38, 0.40, 0.10, -0.22, -0.18, top=(0.72, 0.72)), "cream", True)
        sd = (A - K).normalized()
        so = (dr - sd * dr.dot(sd)).normalized()
        k.add(sh, limb_box(K + so * 0.20, A + so * 0.145, 0.16, 0.06, 0.025, -0.42, -0.55, top=(0.8, 1.0)), "gold", True)
        mid = K + (A - K) * 0.36
        k.add(sh, limb_box(mid - sd * 0.06, mid + sd * 0.06, 0.37, 0.39, 0.03, 0.0, 0.0), "team", True)
        k.add(sh, limb_cyl(K - so * 0.16 + sd * 0.3, A - so * 0.10 - sd * 0.2, 0.06, 10), "graphite_lt", True)
        # foot: graphite ankle ball, gold pad on a graphite sole, a glowing band, three gold toes
        k.add(ft, ell(A, 0.17, 0.17, 0.17, 16, 8), "graphite", True)
        G0 = Vector((A.x, A.y, 0.0))
        k.add(ft, V.xf(V.lathe([(0, 0), (0.32, 0), (0.33, 0.04), (0.32, 0.06), (0, 0.06)], 24), G0), "graphite", True)
        k.add(ft, V.xf(V.lathe([(0, 0.06), (0.30, 0.06), (0.31, 0.12), (0.27, 0.19), (0.18, 0.23), (0, 0.24)], 24), G0), "gold", True)
        k.add(ft, V.xf(ring(0.20, 0.305, 0.025, 24), G0 + up * 0.095), "glow_cyan", True)
        for da in (-35, 0, 35):
            ta = math.radians(ang + da)
            tdir = Vector((math.cos(ta), math.sin(ta), 0))
            k.add(ft, V.xf(V.rbox(0.13, 0.18, 0.10, 0.04, top=(0.7, 0.6)), G0 + tdir * 0.28 + up * 0.05, (0, 0, math.degrees(ta) - 90)), "gold", True)

    def legs_ik(P, offs=None):
        for i, (hip, th, sh, ft) in enumerate(legs):
            tgt = P.head[ft].copy()
            toe = 0.0
            if offs:
                dy, dz, toe = offs[i]
                tgt += Vector((0, dy, dz))
            Pb = P.d("body").inverted() @ tgt
            H = P.head[hip]
            a0 = math.atan2(P.head[ft].y - H.y, P.head[ft].x - H.x)
            a1 = math.atan2(Pb.y - H.y, Pb.x - H.x)
            P.set(hip, (0, 0, math.degrees(a1 - a0)))
            P.ik(th, sh, tgt)
            P.lock(ft, (toe, 0, 0))

    def idle(P, t):
        w = 2 * math.pi * t
        P.set("body", (0.8 * math.sin(2 * w + 0.5), 1.0 * math.sin(w), 1.2 * math.sin(w + 1.0)),
              (0.02 * math.sin(w), 0, -0.02 - 0.025 * math.cos(2 * w)))
        legs_ik(P)
        P.set("head", (0.5 * math.sin(2 * w), 0, 20.0 * math.sin(w)))
        P.set("cannon", (-3.0 * math.sin(w + 0.7) - 1.0, 0, 0))
        P.set("coil", (0, 15.0 * math.sin(2 * w), 0))

    STRIDE, DUTY, LIFT = 1.0, 0.75, 0.42
    PHASE = {"BL": 0.0, "FL": 0.25, "BR": 0.5, "FR": 0.75}

    def walk(P, t):
        w = 2 * math.pi * t
        dip = bump(4 * t, 0.3)
        P.set("body", (1.0 * math.sin(4 * w - 0.6), 2.2 * math.sin(w), 1.5 * math.sin(w + 0.4)),
              (0.06 * math.sin(w), 0.02 * math.cos(4 * w), -0.10 - 0.07 * dip))
        offs = []
        for hip, th, sh, ft in legs:
            dy, dz, toe = foot_path(t + PHASE[hip[-2:]], STRIDE, DUTY, LIFT)
            dz += 0.42 * math.sin(math.radians(10.0 * abs(toe)))
            offs.append((dy, dz, 10.0 * toe))
        legs_ik(P, offs)
        P.set("head", (-1.0 * math.sin(4 * w - 1.2), -1.5 * math.sin(w), -3.0 * math.sin(w + 0.4)))
        P.set("cannon", (2.0 * math.sin(4 * w - 1.6), 0, 0))
        P.set("coil", (0, 6.0 * math.sin(2 * w), 0))

    N_ATK, FIRE = 18, 10

    def attack(P, t):
        f = t * N_ATK
        c = smooth(f / FIRE) * (1 - smooth((f - FIRE) / (N_ATK - FIRE)))
        u = clamp01((f - FIRE) / (N_ATK - FIRE))
        k_ = 0.0 if f < FIRE else (1 - u) ** 3
        P.set("body", (2.5 * c - 3.0 * k_, 0, 0), (0, 0.14 * k_, -0.10 * c + 0.02 * k_))
        legs_ik(P)
        P.set("head", (2.0 * c - 4.0 * k_, 0, 0))
        P.set("cannon", (-6.0 * k_, 0, 0), (0, 0.10 * c + 0.32 * k_, 0))
        P.set("coil", (0, 360.0 * smooth(f / N_ATK), 0))

    return {"muzzle": ("cannon", Vector((0, -2.40, CZ))),
            "actions": [("idle_loop", 90, idle, True), ("walk_loop", 42, walk, True), ("attack", N_ATK, attack, False)],
            "attack_fire_frame": FIRE}


def worker(k, sk):
    BC = Vector((0, 0, 0.50))                    # body centre
    BRX, BRY, BRZ = 0.205, 0.215, 0.245          # body radii
    S, E = Vector((0.215, -0.02, 0.36)), Vector((0.31, -0.06, 0.20))
    HD = Vector((0.20, -0.26, 0.17))             # where each forearm meets the tray
    sk.bone("root", (0, 0, 0), (0, 0.15, 0))
    sk.bone("body", (0, 0, 0.45), (0, 0, 0.70), "root")
    sk.bone("lens", (0, -0.24, 0.47), (0, -0.30, 0.47), "body")
    sk.bone("fin_L", (0.10, 0.0, 0.66), (0.12, 0.05, 0.92), "body", True)
    sk.bone("disc_L", (0.25, 0.0, 0.50), (0.40, 0.0, 0.50), "body", True)
    sk.bone("arm_L", S, E, "body", True)
    sk.bone("scoop", (0, -0.06, 0.20), (0, -0.30, 0.20), "arm_L")
    sk.bone("cargo", (0, -0.27, 0.19), (0, -0.27, 0.36), "scoop")

    B = "body"
    # the egg body, with the gold top strap, gold side panels and a back hatch in a gold arch
    k.add(B, ell(BC, BRX, BRY, BRZ, 28, 12), "cream")
    k.add(B, strap(0.0, BC.z, BRY, BRZ, 25, 158, -0.04, 0.04, "x", 0.008, 0.03, 16, 0.008), "gold")
    side = [(math.cos(math.radians(a)) * BRX, math.sin(math.radians(a)) * BRZ) for a in range(-34, 47, 8)]
    for az in (0, 180):
        k.add(B, V.xf(gore(side, az - 52, az + 52, 12, 0.008, 0.03), BC, (0, 0, 0), (1.0, BRY / BRX, 1.0)), "gold")
    back = [(math.cos(math.radians(a)) * BRX, math.sin(math.radians(a)) * BRZ) for a in range(-40, 31, 7)]
    k.add(B, V.xf(gore(back, 66, 114, 6, 0.006, 0.03), BC, (0, 0, 0), (1.0, BRY / BRX, 1.0)), "gold")
    k.add(B, V.xf(gore(back[1:-2], 74, 106, 5, 0.012, 0.02), BC, (0, 0, 0), (1.0, BRY / BRX, 1.0)), "graphite")
    # the face: a graphite plate with a cream bezel and the vertical cyan pill lens (own bone, it scans)
    k.add(B, V.xf(V.rbox(0.22, 0.09, 0.25, 0.06), (0, -0.175, 0.47)), "cream_dk")
    k.add(B, V.xf(V.rbox(0.18, 0.08, 0.21, 0.05), (0, -0.192, 0.47)), "graphite")
    k.add("lens", V.xf(V.rbox(0.058, 0.03, 0.15, 0.028), (0, -0.226, 0.47)), "glow_cyan")
    # lower housing: gold skirt, graphite band with a cyan strip, the cyan hover dome at the bottom
    k.add(B, V.xf(V.lathe([(0, 0.15), (0.12, 0.15), (0.15, 0.20), (0.16, 0.27), (0.13, 0.32), (0, 0.32)], 22), (0, 0.01, 0)), "gold")
    k.add(B, V.xf(V.lathe([(0, 0.07), (0.11, 0.07), (0.125, 0.10), (0.125, 0.155), (0, 0.155)], 22), (0, 0.01, 0)), "graphite")
    k.add(B, V.xf(V.rbox(0.10, 0.03, 0.025, 0.01), (0, 0.135, 0.12)), "glow_cyan")
    k.add(B, ell((0, 0.01, 0.075), 0.085, 0.085, 0.075, 18, 6, -1.0, 0.0), "glow_cyan")
    # shoulders: graphite sockets under the discs
    k.add(B, ell(S, 0.05, 0.05, 0.05, 12, 6), "graphite", True)
    # side discs (own bones): graphite axle, gold ring, a big cream cup with a domed lens, stretched upright
    D = "disc_L"
    k.add(D, V.xf(V.lathe([(0, 0), (0.07, 0), (0.07, 0.08), (0, 0.08)], 16), (0.19, 0, 0.50), (0, 90, 0)), "graphite", True)
    k.add(D, V.xf(ring(0.085, 0.125, 0.03, 22), (0.245, 0, 0.50), (0, 90, 0), (1.12, 1.0, 1.0)), "gold", True)
    disc(k, D, (0.27, 0.0, 0.50), (0, 90, 0), 0.128, "cream", 0.10, 22, 1.12, mirror=True)
    # ear fins (own bones): tall gold blades with a cyan inner strip
    F = "fin_L"
    fin = [(-0.065, -0.07), (0.075, -0.09), (0.11, 0.27), (0.05, 0.29)]
    k.add(F, V.xf(V.prism(fin, -0.018, 0.018, "x", 0.012, 2), (0.10, 0.0, 0.66), (0, 8, 0)), "gold", True)
    fg = [(-0.02, 0.0), (0.05, 0.0), (0.075, 0.20), (0.05, 0.21)]
    k.add(F, V.xf(V.prism(fg, -0.024, -0.016, "x", 0.004, 1), (0.10, 0.0, 0.66), (0, 8, 0)), "glow_cyan", True)
    # arms: cream upper arms with a gold strip, graphite elbow drums with a cyan lens outside
    A = "arm_L"
    k.add(A, limb_box(S, E, 0.075, 0.085, 0.03, 0.0, -0.01), "cream", True)
    k.add(A, limb_box(S + Vector((0.035, 0, 0)), E + Vector((0.035, 0, 0)), 0.02, 0.05, 0.008, -0.03, -0.05), "gold", True)
    k.add(A, V.xf(V.lathe([(0, -0.045), (0.055, -0.045), (0.06, -0.03), (0.06, 0.03), (0.055, 0.045), (0, 0.045)], 16), E, (0, 90, 0)), "graphite", True)
    disc(k, A, E + Vector((0.035, 0, 0)), (0, 90, 0), 0.05, "gold", 0.025, 14, mirror=True)
    # the scoop (arms' forearms and the tray, pivoting on the elbow axis), then the crystal load
    C = "scoop"
    for s in (1, -1):
        e = Vector((s * E.x, E.y, E.z))
        h = Vector((s * HD.x, HD.y, HD.z))
        k.add(C, limb_box(e, h, 0.08, 0.09, 0.03, 0.02, 0.0), "cream")
        k.add(C, limb_box(e, h, 0.088, 0.098, 0.03, -((h - e).length - 0.05), 0.01), "gold")
    k.add(C, V.xf(V.rbox(0.42, 0.21, 0.11, 0.035, top=(1.08, 1.12)), (0, -0.28, 0.135)), "graphite")
    k.add(C, V.xf(V.rbox(0.36, 0.16, 0.02, 0.008), (0, -0.28, 0.192)), "dark")
    for s in (1, -1):
        k.add(C, V.xf(V.rbox(0.03, 0.03, 0.045, 0.012), (s * 0.14, -0.392, 0.13)), "glow_cyan")
    for base, h, r, tilt in (((0.0, -0.28, 0.19), 0.17, 0.045, (8, -4, 0)), ((-0.08, -0.25, 0.19), 0.13, 0.04, (4, -20, 0)),
                             ((0.08, -0.26, 0.19), 0.14, 0.04, (-6, 18, 0)), ((-0.04, -0.33, 0.19), 0.10, 0.035, (22, -8, 0)),
                             ((0.05, -0.33, 0.19), 0.11, 0.035, (20, 12, 0)), ((0.13, -0.30, 0.19), 0.08, 0.03, (10, 30, 0)),
                             ((-0.13, -0.31, 0.19), 0.085, 0.03, (12, -30, 0))):
        k.add("cargo", crystal(base, h, r, tilt), "glow_crystal")

    def idle(P, t):
        w = 2 * math.pi * t
        P.set("body", (2.0 * math.sin(2 * w + 0.4), 1.5 * math.sin(w), 4.0 * math.sin(w + 0.7)), (0, 0, 0.022 * (1 - math.cos(w))))
        P.set("lens", None, (0.03 * math.sin(w), 0, 0))
        P.sym("fin_L", (-3.0 * math.sin(w - 0.8), 2.0 * math.sin(2 * w), 0))
        P.sym("disc_L", (0, 0, 5.0 * math.sin(w + 0.3)))
        P.sym("arm_L", (4.0 * math.sin(2 * w), 0, 0))
        P.set("scoop", (-7.0 * math.sin(2 * w + 0.6), 0, 0))

    def walk(P, t):
        w = 2 * math.pi * t
        P.set("body", (14.0 + 2.0 * math.sin(2 * w), 2.0 * math.sin(w), 2.0 * math.sin(w + 0.5)),
              (0, 0, 0.055 + 0.012 * math.sin(2 * w)))
        P.set("lens", None, (0.006 * math.sin(w), 0, 0))
        P.sym("fin_L", (-16.0 + 3.0 * math.sin(4 * w), 0, 0))
        P.sym("disc_L", (0, 0, 22.0 + 3.0 * math.sin(2 * w + 1.0)))
        P.sym("arm_L", (12.0 + 3.0 * math.sin(2 * w + 1.0), 0, 0))
        P.set("scoop", (-10.0 + 4.0 * math.sin(2 * w + 1.6), 0, 0))

    N_ATK = 15

    def attack(P, t):
        f = t * N_ATK
        a = smooth(f / 5.0) if f <= 5 else 1.0 - smooth((f - 5.0) / 2.0)
        b = 0.0 if f <= 5 else (smooth((f - 5.0) / 2.0) if f <= 7 else 1.0 - smooth((f - 7.0) / 8.0))
        P.set("body", (8.0 * a - 6.0 * b, 0, 0), (0, 0, 0.02 * a + 0.035 * b))
        P.sym("fin_L", (6.0 * a - 12.0 * b, 0, 0))
        P.sym("disc_L", (0, 0, -6.0 * a + 10.0 * b))
        P.sym("arm_L", (-12.0 * a - 4.0 * b, 0, 0))
        P.set("scoop", (22.0 * a - 30.0 * b, 0, 0))

    return {"muzzle": ("scoop", Vector((0, -0.40, 0.18))),
            "actions": [("idle_loop", 72, idle, True), ("walk_loop", 24, walk, True), ("attack", N_ATK, attack, False)],
            "attack_fire_frame": 6}


BUILDERS = {"ambron_lancer": lancer, "ambron_bulwark": bulwark, "ambron_sovereign": sovereign, "ambron_worker": worker}


# --- checks ------------------------------------------------------------------------------------------------

def mesh_coords(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.data
    a = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3) @ np.array(ob.matrix_world.to_3x3()).T + np.array(ob.matrix_world.translation)


def motion_checks(rig, body, acts):
    """Per action: the lowest point over the frames, how far the last frame is from the first (loops) or from the
    rest pose (attack), and how far any vertex travels from rest."""
    rest_pose(rig)
    rest = mesh_coords(body)
    out = {}
    for act, n, loop in acts:
        lows, first, last, travel = [], None, None, 0.0
        for f in range(n + 1):
            use_action(rig, act, f)
            c = mesh_coords(body)
            lows.append(float(c[:, 2].min()))
            travel = max(travel, float(np.abs(c - rest).max()))
            if f == 0:
                first = c
            last = c
        out[act.name] = {"frames": n, "seconds": round(n / FPS, 3), "loop": loop,
                         "lowest_z_min": round(min(lows), 4), "lowest_z_max": round(max(lows), 4),
                         "end_vs_start_m": round(float(np.abs(last - first).max()), 6),
                         "end_vs_rest_m": round(float(np.abs(last - rest).max()), 6),
                         "max_travel_m": round(travel, 3)}
    rest_pose(rig)
    return out


def glb_json(path):
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + n])


def glb_summary(path):
    js = glb_json(path)
    acc = js["accessors"]
    tris = 0
    for m in js.get("meshes", []):
        for p in m["primitives"]:
            tris += acc[p["indices"]]["count"] // 3
    anims = []
    for a in js.get("animations", []):
        tmax = max(acc[s["input"]]["max"][0] for s in a["samplers"])
        anims.append({"name": a["name"], "channels": len(a["channels"]), "seconds": round(tmax, 3)})
    return {"triangles": tris, "animations": anims,
            "skins": [{"joints": len(s["joints"])} for s in js.get("skins", [])],
            "nodes": [n.get("name") for n in js["nodes"]],
            "materials": [m["name"] for m in js.get("materials", [])],
            "meshes": len(js.get("meshes", []))}


def reimport(path):
    """Imports the GLB into a fresh scene and lists what came back."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    bpy.ops.import_scene.gltf(filepath=path)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.users_collection]
    meshes = [o for o in meshes if o.data.materials] or meshes
    lo = min((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)
    return {"actions": sorted([(a.name, [round(x, 1) for x in a.frame_range], round((a.frame_range[1] - a.frame_range[0]) / FPS, 3)) for a in bpy.data.actions]),
            "armatures": [(o.name, len(o.data.bones)) for o in arms],
            "meshes": [(o.name, len(o.data.polygons), [m.name for m in o.data.materials]) for o in meshes],
            "empties": [(o.name, o.parent.name if o.parent else None, o.parent_bone) for o in bpy.data.objects if o.type == "EMPTY"],
            "lowest_z": round(lo, 4)}


# --- renders -------------------------------------------------------------------------------------------------

def load_rgba(path):
    return V.load_px(path)


def save_rgba(arr, path):
    img = bpy.data.images.new("out", arr.shape[1], arr.shape[0], alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def tile(a, cell, bgc=(0.2, 0.21, 0.23)):
    """Fits an RGBA array into a cell x cell tile (nearest-neighbour scale, centred, flattened on bgc)."""
    h, w = a.shape[:2]
    s = min(cell / w, cell / h)
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    ys = np.minimum((np.arange(nh) / s).astype(int), h - 1)
    xs = np.minimum((np.arange(nw) / s).astype(int), w - 1)
    a = a[ys][:, xs]
    t = np.zeros((cell, cell, 4), np.float32)
    t[..., :3] = bgc
    t[..., 3] = 1
    y0, x0 = (cell - nh) // 2, (cell - nw) // 2
    al = a[..., 3:4]
    t[y0:y0 + nh, x0:x0 + nw, :3] = a[..., :3] * al + t[y0:y0 + nh, x0:x0 + nw, :3] * (1 - al)
    return t


def grid(rows, out, cell=256):
    """rows: lists of image paths (top row first); written as one PNG."""
    ncol = max(len(r) for r in rows)
    lines = []
    for r in rows:
        tiles = [tile(load_rgba(p), cell) for p in r]
        while len(tiles) < ncol:
            tiles.append(tile(np.zeros((4, 4, 4), np.float32), cell))
        lines.append(np.concatenate(tiles, axis=1))
    save_rgba(np.concatenate(lines[::-1], axis=0), out)


def game_camera(cam, lift=0.0, zoom=1.0, dist=25.0, target=None):
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
    cam.data.angle = 2 * math.atan(math.tan(math.radians(22.5)) / zoom)
    cam.data.shift_x = cam.data.shift_y = 0.0
    tgt = target if target is not None else Vector((0, 0, 0.5 + lift))
    cam.location = tgt + V.view_dir(-25, 55) * dist
    V.look(cam, tgt)


def review(uid, rig, body, muzzle, spec, acts, rnd):
    cam, ground, bg = V.stage()
    rest_pose(rig)
    pts = V.world_points([body], 4000)
    out = os.path.join(HERE, "review", "round%d" % rnd)
    shots = []
    ground.hide_render = True
    V.fit(cam, pts, 35, 24, 0.04)
    icon = os.path.join(ICONS, uid + ".png")
    V.render(icon, (256, 256), True)
    V.fit(cam, pts, 35, 22, 0.08)
    shots.append(os.path.join(out, uid + "_front.png"))
    V.render(shots[-1], (512, 512), False)
    V.fit(cam, pts, -140, 26, 0.08)
    shots.append(os.path.join(out, uid + "_back.png"))
    V.render(shots[-1], (512, 512), False)
    ground.hide_render = False
    game_camera(cam)
    shots.append(os.path.join(out, uid + "_game.png"))
    V.render(shots[-1], (512, 512), False)
    game_camera(cam, zoom=2.0)
    zoomed = os.path.join(out, uid + "_game_x2.png")
    V.render(zoomed, (512, 512), False)
    V.sheet(shots + [icon], os.path.join(out, uid + "_sheet.png"))
    # animation contact sheet: one row per action, six frames each, side three-quarter view on the ground
    V.fit(cam, pts, 62, 12, 0.17)
    tmp = os.path.join(CACHE, "frames")
    rows = []
    for act, n, loop in acts:
        if loop:
            frames = [round(n * i / 6) for i in range(6)]
        else:
            fire = spec["attack_fire_frame"]
            frames = sorted({0, max(0, fire - 2), fire, min(n, fire + 1), min(n, fire + 4), n})
        row = []
        for f in frames:
            use_action(rig, act, f)
            p = os.path.join(tmp, "%s_%s_%02d.png" % (uid, act.name, f))
            V.render(p, (256, 256), False)
            row.append(p)
        rows.append(row)
    rest_pose(rig)
    grid(rows, os.path.join(out, uid + "_anim.png"), 256)
    return shots + [zoomed, icon]


# --- main ----------------------------------------------------------------------------------------------------

def make_materials():
    mats, uv = V.make_materials()
    mats["glow_crystal"] = V.flat("glow_crystal", CRYSTAL[0], 0.3, 0.0, CRYSTAL[1], CRYSTAL[2])
    return mats, uv


def build(uid, rnd, do_render):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    mats, uv = make_materials()
    k, sk = Kit(mats, uv), Skel()
    spec = BUILDERS[uid](k, sk)
    body = k.join("body")
    # settle: lowest point to z = 0 and the bounding box centred in X and Y (mesh and bones alike)
    co = np.array([v.co[:] for v in body.data.vertices])
    lo, hi = co.min(0), co.max(0)
    off = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    body.data.transform(Matrix.Translation(-off))
    dims = Vector(hi - lo)
    rig = make_rig(sk, off)
    body.parent = rig
    md = body.modifiers.new("rig", "ARMATURE")
    md.object = rig
    unknown = [g.name for g in body.vertex_groups if g.name not in rig.data.bones]
    assert not unknown, "vertex groups without bones: %s" % unknown
    # the muzzle empty rides on the weapon bone
    mb, mp = spec["muzzle"]
    muz = bpy.data.objects.new("muzzle", None)
    muz.empty_display_type, muz.empty_display_size = "ARROWS", 0.15
    bpy.context.scene.collection.objects.link(muz)
    muz.parent, muz.parent_type, muz.parent_bone = rig, "BONE", mb
    bpy.context.view_layer.update()
    muz.matrix_world = Matrix.Translation(mp - off)
    # animation
    P = Pose(rig)
    acts = []
    for name, n, fn, loop in spec["actions"]:
        acts.append((bake(rig, P, name, n, fn, loop), n, loop))
    rest_pose(rig)
    checks = motion_checks(rig, body, acts)
    # export
    path = os.path.join(MODELS, uid + ".glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in (rig, body, muz):
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False,
                              export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
                              export_frame_range=False, export_anim_slide_to_zero=False, export_def_bones=False,
                              export_skins=True, export_all_influences=False, export_rest_position_armature=True,
                              export_reset_pose_bones=True, export_optimize_animation_size=True,
                              export_optimize_animation_keep_anim_armature=True)
    body.data.calc_loop_triangles()
    weights = [len(v.groups) for v in body.data.vertices]
    info = {
        "id": uid,
        "triangles": len(body.data.loop_triangles),
        "size_m": [round(v, 3) for v in dims],
        "glb_bytes": os.path.getsize(path),
        "bones": len(rig.data.bones),
        "bone_names": [b.name for b in rig.data.bones],
        "vertices": len(body.data.vertices),
        "verts_with_one_weight": sum(1 for w in weights if w == 1),
        "verts_without_weight": sum(1 for w in weights if w == 0),
        "materials": [m.name for m in body.data.materials],
        "tris_by_bone": {b: sum(v for (bb, _), v in k.tris.items() if bb == b) for b in sorted({bb for bb, _ in k.tris})},
        "muzzle": {"bone": mb, "rest_world": [round(v, 3) for v in muz.matrix_world.translation]},
        "motion": checks,
        "glb": glb_summary(path),
    }
    shots = review(uid, rig, body, muz, spec, acts, rnd) if do_render else []
    info["reimport"] = reimport(path)
    print("[shardfall]", json.dumps({k_: info[k_] for k_ in ("id", "triangles", "size_m", "glb_bytes", "bones")}))
    os.makedirs(os.path.join(HERE, "review"), exist_ok=True)
    with open(os.path.join(HERE, "review", uid + "_stats.json"), "w") as f:
        json.dump(info, f, indent=1)
    return info


def lineup(rnd):
    """Every finished unit beside two Ambron vehicles, under the game camera at 25 and 45 m."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cam, ground, bg = V.stage()
    place = [("ambron_scorcher", -7.2, 0.0), ("ambron_worker", -4.6, 0.0), ("ambron_lancer", -3.3, 0.0),
             ("ambron_bulwark", -1.7, 0.0), ("ambron_sovereign", 1.6, 0.0), ("ambron_hailfire", 5.4, 0.0)]
    for uid, x, y in place:
        path = os.path.join(MODELS, uid + ".glb")
        if not os.path.exists(path):
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        for o in set(bpy.data.objects) - before:
            if o.parent is None:
                o.location.x += x
                o.location.y += y
            if o.type == "EMPTY" and o.name.startswith("muzzle"):
                o.hide_render = True
    out = os.path.join(HERE, "review", "round%d" % rnd)
    tgt = Vector((-0.6, 0, 0.8))
    for dist, zoom, name in ((25, 1.0, "lineup_game25"), (25, 2.0, "lineup_game25_x2"), (45, 1.0, "lineup_game45"), (45, 2.0, "lineup_game45_x2")):
        game_camera(cam, zoom=zoom, dist=dist, target=tgt)
        V.render(os.path.join(out, name + ".png"), (1024, 576), False)
    ground.hide_render = True
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "AUTO"
    cam.data.angle = math.radians(30)
    cam.data.shift_x = cam.data.shift_y = 0
    cam.location = tgt + V.view_dir(30, 16) * 30
    V.look(cam, tgt + Vector((0, 0, 0.8)))
    V.render(os.path.join(out, "lineup_front.png"), (1600, 600), False)


def refcompare(rnd):
    """The drone rendered at the reference's front and side angles, beside crops of the reference turnaround."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cam, ground, bg = V.stage()
    ground.hide_render = True
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, "ambron_worker.glb"))
    for o in bpy.data.objects:
        if o.type == "EMPTY":
            o.hide_render = True
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name != "ground"]
    pts = V.world_points(meshes, 3000)
    bg.inputs[0].default_value = (0.045, 0.048, 0.052, 1)
    tmp = os.path.join(CACHE, "ref")
    shots = []
    for az, el, name in ((0, 14, "front"), (-58, 14, "side"), (180, 14, "back")):
        V.fit(cam, pts, az, el, 0.1)
        p = os.path.join(tmp, "drone_%s.png" % name)
        V.render(p, (400, 400), False)
        shots.append(p)
    ref = load_rgba(REF)
    H = ref.shape[0]

    def crop(x0, y0, x1, y1):          # in top-left pixel coordinates of the reference
        return ref[H - y1:H - y0, x0:x1]
    tiles = [tile(crop(80, 90, 290, 320), 400), tile(load_rgba(shots[0]), 400),
             tile(crop(620, 90, 860, 320), 400), tile(load_rgba(shots[1]), 400),
             tile(crop(340, 350, 560, 600), 400), tile(load_rgba(shots[2]), 400)]
    rows = [np.concatenate(tiles[:2] + tiles[2:4], axis=1), np.concatenate(tiles[4:] + [tile(np.zeros((4, 4, 4), np.float32), 400)] * 2, axis=1)]
    save_rgba(np.concatenate(rows[::-1], axis=0), os.path.join(HERE, "review", "round%d" % rnd, "ambron_worker_vs_reference.png"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = argv[0] if argv else "all"
    rnd = int(argv[argv.index("--round") + 1]) if "--round" in argv else 1
    if which == "lineup":
        return lineup(rnd)
    if which == "refcompare":
        return refcompare(rnd)
    ids = IDS if which == "all" else [which]
    for uid in ids:
        if uid not in BUILDERS:
            raise SystemExit("unknown id " + uid)
        build(uid, rnd, "--no-render" not in argv)


if __name__ == "__main__":
    main()
