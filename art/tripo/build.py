"""Shardfall core units from Tripo: fit, material split, auto-rig, animate, export, review.

    Blender --background --factory-startup --python-exit-code 1 --python art/tripo/build.py -- <id|all> [--round N] [--inspect]

Pipeline (concept image in ChatGPT -> Tripo image-to-3D -> this script):
  1. Import the raw Tripo GLB from art/tripo/raw/<id>.glb (gitignored; Tripo exports are large).
  2. Optionally crop one copy out of a multi-view grid (the harvester was generated from a 3 x 3 turnaround).
  3. Turn it to face Blender -Y, scale to the unit's height, lowest point to z = 0, centred in X and Y.
  4. Decimate to the triangle budget (UV seams kept) and shrink the textures to 1024 px.
  5. Split faces into materials by the colour of their texture: `team` (flat, recoloured in game) and
     `glow_*` (emissive). Ambron: the cyan lights become team colour. Void: the acid-green sacs glow, the
     crimson flesh in the gaps takes the team colour.
  6. Auto-rig by body plan (hover, biped, legs, wings) with weights computed from the geometry, then key
     idle_loop, walk_loop or fly_loop, and attack.
  7. Export assets/models/<id>.glb, render assets/icons/<id>.png and review sheets into art/tripo/review/.

--inspect renders four orthogonal views of the raw model (after crop) to find its facing, and stops.
"""
import json
import math
import os
import struct
import sys

import bmesh
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "icons")
RAW = os.path.join(HERE, "raw")
FPS = 24

# yaw: degrees to turn the raw model about Z so its front faces -Y (found with --inspect).
# h: model height in metres (ART_SPEC sizes). tris: triangle budget.
# rig: hover | biped | legs | wings. Rig parameters are fractions of the model's height (H) or half-width.
UNITS = {
    "ambron_worker": dict(race="ambron", rig="hover", h=0.95, tris=4000, yaw=90.0, bake=True, cargo=True,
                          crop=dict(x=(-0.49, -0.163), z=(0.0, 0.31))),
    "ambron_lancer": dict(race="ambron", rig="biped", h=1.15, tris=5000, yaw=0.0, hip=0.47),
    "ambron_bulwark": dict(race="ambron", rig="biped", h=1.6, tris=5000, yaw=0.0, hip=0.36),
    "ambron_sovereign": dict(race="ambron", rig="legs", h=4.6, tris=14000, yaw=0.0, legs=2, leg_top=0.42, core=0.38,
                             attack="recoil"),
    "ambron_scorcher": dict(race="ambron", rig="hover", h=1.3, tris=7000, yaw=0.0),
    "ambron_hailfire": dict(race="ambron", rig="biped", h=1.6, tris=7000, yaw=0.0, hip=0.45, attack="recoil"),
    "ambron_dart": dict(race="ambron", rig="hover", h=0.6, tris=6000, yaw=0.0, air=3.5),
    "ambron_monolith": dict(race="ambron", rig="hover", h=1.2, tris=8000, yaw=0.0, air=3.5),
    "void_drudge": dict(race="void", rig="legs", h=0.7, tris=4000, yaw=0.0, legs=3, leg_top=0.45, core=0.42),
    "void_spitter": dict(race="void", rig="biped", h=1.15, tris=5000, yaw=-90.0, hip=0.45),
    "void_mauler": dict(race="void", rig="biped", h=1.6, tris=5000, yaw=180.0, hip=0.36, attack="lunge"),
    "void_acidback": dict(race="void", rig="legs", h=1.35, tris=8000, yaw=0.0, legs=3, leg_top=0.4, core=0.45),
    "void_spinefiend": dict(race="void", rig="legs", h=1.5, tris=8000, yaw=0.0, legs=2, leg_top=0.42, core=0.4,
                            attack="recoil", bone_sat=0.62),
    "void_skitter": dict(race="void", rig="wings", h=0.8, tris=6000, yaw=0.0, core=0.3, air=3.5),
    "void_gorgon": dict(race="void", rig="hover", h=1.4, tris=8000, yaw=0.0, air=3.5, bone_sat=0.62),
    "void_leviathan": dict(race="void", rig="legs", h=2.6, tris=14000, yaw=0.0, legs=3, leg_top=0.4, core=0.42,
                           attack="lunge", bone_sat=0.62),
}
AIR_RIGS = {"wings"}

TEAM_GREY = (0.62, 0.64, 0.67, 1.0)


def argv_after():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def smooth(e0, e1, x):
    """Vectorised smoothstep from e0 to e1 (either order)."""
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# --- import, crop, fit ------------------------------------------------------------------------------------

def import_raw(uid):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = os.path.join(RAW, uid + ".glb")
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    # bake every transform into the mesh data, drop the empties
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = uid
    ob.data.name = uid
    # glTF brings custom split normals and splits vertices along UV seams: both wreck decimation
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except RuntimeError:
        pass
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def shade(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    except (AttributeError, RuntimeError, TypeError):
        for p in ob.data.polygons:
            p.use_smooth = True


def crop(ob, box):
    me = ob.data
    n = len(me.polygons)
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(n, 3)
    keep = np.ones(n, bool)
    for ax, k in (("x", 0), ("y", 1), ("z", 2)):
        if ax in box:
            lo, hi = box[ax]
            keep &= (c[:, k] >= lo) & (c[:, k] <= hi)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    dead = [f for f, k in zip(bm.faces, keep) if not k]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()


def verts_np(ob):
    me = ob.data
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", v)
    return v.reshape(-1, 3)


def fit(ob, cfg):
    me = ob.data
    me.transform(Matrix.Rotation(math.radians(cfg["yaw"]), 4, "Z"))
    v = verts_np(ob)
    lo, hi = v.min(0), v.max(0)
    s = cfg["h"] / max(1e-6, hi[2] - lo[2])
    me.transform(Matrix.Scale(s, 4))
    v = verts_np(ob)
    lo, hi = v.min(0), v.max(0)
    me.transform(Matrix.Translation(Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))))
    me.update()
    v = verts_np(ob)
    return v.min(0), v.max(0)


def tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def decimate(ob, target):
    t0 = tri_count(ob)
    if t0 <= target:
        return t0, t0
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = target / t0
    mod.delimit = {"UV"}
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    t1 = tri_count(ob)
    for k in range(4):                         # UV delimit can stall short of the target: finish without it
        if t1 <= target * 1.08:
            break
        mod = ob.modifiers.new("dec%d" % k, "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = target / t1
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        t1 = tri_count(ob)
    return t0, t1


def rebake(hi, cfg):
    """A low-poly copy with fresh UVs, its colour baked from the high-poly in Cycles. For sources whose
    UVs are too fragmented to survive decimation (the harvester came from a 2M-triangle grid)."""
    lo = hi.copy()
    lo.data = hi.data.copy()
    lo.name = hi.name + "_lo"
    bpy.context.scene.collection.objects.link(lo)
    t0 = tri_count(hi)
    t1 = t0
    bpy.context.view_layer.objects.active = lo
    for k in range(6):
        if t1 <= cfg["tris"] * 1.08:
            break
        mod = lo.modifiers.new("dec%d" % k, "DECIMATE")
        mod.ratio = cfg["tris"] / t1
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        t1 = tri_count(lo)
    me = lo.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action="DESELECT")
    lo.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new(hi.name + "_col", 1024, 1024)
    m = bpy.data.materials.new(hi.name + "_baked")
    m.use_nodes = True
    b = principled(m)
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Metallic"].default_value = 0.1
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    m.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    m.node_tree.nodes.active = tex
    me.materials.clear()
    me.materials.append(m)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 8
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = 0.02 * cfg["h"]
    sc.render.bake.max_ray_distance = 0.08 * cfg["h"]
    sc.render.bake.margin = 6
    hi.select_set(True)
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
    img.pack()
    bpy.data.objects.remove(hi)
    lo.name = cfg["id"]
    sc.render.engine = "BLENDER_EEVEE"
    return lo, t0, t1


# --- textures and material split ------------------------------------------------------------------------

def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def linked_image(sock):
    """The image feeding a socket, through normal-map or separate nodes."""
    if not sock.is_linked:
        return None
    n = sock.links[0].from_node
    for _ in range(4):
        if n.type == "TEX_IMAGE":
            return n.image
        ins = [i for i in n.inputs if i.is_linked]
        if not ins:
            return None
        n = ins[0].links[0].from_node
    return None


def shrink_images(uid, size=1024):
    """Scale textures down to `size` and name them <uid>_<map>, whatever the Tripo export was called."""
    out = []
    for img in bpy.data.images:
        if img.size[0] > size:
            img.scale(size, size)
        stem = img.name.rsplit(".", 1)[0]
        for suffix in ("basecolor", "normal", "rm"):
            if stem.endswith("_" + suffix):
                img.name = uid + "_" + suffix
        out.append((img.name, list(img.size)))
    return out


def base_image(ob):
    m = ob.data.materials[0]
    return linked_image(principled(m).inputs["Base Color"])


def face_colours(ob, img):
    """Mean sRGB colour of the texture under each face (its loops and centre)."""
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[..., :3]
    me = ob.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    starts = np.empty(len(me.polygons), np.int32)
    counts = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_start", starts)
    me.polygons.foreach_get("loop_total", counts)
    cols = np.zeros((len(me.polygons), 3), np.float32)
    for k in range(3):                                   # the three loops of every (triangulated) face
        idx = starts + np.minimum(k, counts - 1)
        u = uv[idx]
        cols += sample(px, u)
    cen = np.zeros((len(me.polygons), 2), np.float32)
    for k in range(3):
        cen += uv[starts + np.minimum(k, counts - 1)]
    cols += 2 * sample(px, cen / 3)
    return cols / 5


def sample(px, u):
    h, w = px.shape[:2]
    x = np.clip((u[:, 0] % 1.0) * (w - 1), 0, w - 1).astype(np.int32)
    y = np.clip((u[:, 1] % 1.0) * (h - 1), 0, h - 1).astype(np.int32)
    return px[y, x]


def hsv(c):
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    mx = c.max(1)
    mn = c.min(1)
    d = mx - mn + 1e-6
    hue = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = (mx - mn) / (mx + 1e-6)
    return hue, sat, mx


def classify(ob, img, race, bone_sat=0.42):
    """Per-face material slot: 0 body, 1 team, 2 glow.
    bone_sat lets a unit with warmer, peach-toned bone (the Spinefiend's spines) take more of it as team."""
    hue, sat, val = hsv(face_colours(ob, img))
    slot = np.zeros(len(hue), np.int32)
    if race == "ambron":
        cyan = (hue > 165) & (hue < 215) & (sat > 0.35) & (val > 0.55)
        slot[cyan] = 1
    else:
        # the pale bone spikes, blades and claws take the team tint; the acid-green sacs and eyes glow
        green = (hue > 65) & (hue < 150) & (sat > 0.45) & (val > 0.45)
        peach = (hue > 12) & (hue < 45) & (sat < bone_sat)
        bone = ((sat < 0.42) | peach) & (val > 0.62) & ~green
        slot[bone] = 1
        slot[green] = 2
    return slot


def cargo_faces(ob, img):
    """The crystals a worker carries: the brightest gold faces mark the cluster, then every gold-toned
    face inside that box joins it. The game shows this part only while the worker carries crystals."""
    hue, sat, val = hsv(face_colours(ob, img))
    fc = np.empty(len(ob.data.polygons) * 3, np.float32)
    ob.data.polygons.foreach_get("center", fc)
    fc = fc.reshape(-1, 3)
    core = (hue > 36) & (hue < 60) & (sat > 0.72) & (val > 0.78)
    if core.sum() < 10:
        return np.zeros(len(hue), bool)
    lo = np.percentile(fc[core], 3, axis=0) - 0.07
    hi = np.percentile(fc[core], 97, axis=0) + 0.07
    lo[0] += 0.04
    gold = (hue > 22) & (hue < 64) & (sat > 0.4) & (val > 0.45)
    return gold & np.all((fc >= lo) & (fc <= hi), axis=1)


def split_cargo(ob, mask):
    """Move the masked faces into their own object named cargo (it keeps the rig)."""
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.select_set(False)
    for i in np.nonzero(mask)[0]:
        bm.faces[int(i)].select_set(True)
    bmesh.update_edit_mesh(ob.data)
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    new = [o for o in bpy.context.selected_objects if o != ob][0]
    new.name = "cargo"
    new.data.name = "cargo"
    return new


def make_materials(ob, race):
    body = ob.data.materials[0]
    body.name = race + "_" + ob.name + "_body"
    if race == "ambron":
        # flat light grey: the cyan lights become solid, glowing team colour
        team = bpy.data.materials.new("team")
        team.use_nodes = True
        b = principled(team)
        b.inputs["Base Color"].default_value = TEAM_GREY
        b.inputs["Roughness"].default_value = 0.4
    else:
        # keeps the bone texture: the game multiplies it by the team colour, so detail survives
        team = body.copy()
        team.name = "team"
    glow = body.copy()
    glow.name = "glow_" + ("cyan" if race == "ambron" else "acid")
    gb = principled(glow)
    img = linked_image(gb.inputs["Base Color"])
    tex = next(n for n in glow.node_tree.nodes if n.type == "TEX_IMAGE" and n.image == img)
    glow.node_tree.links.new(tex.outputs["Color"], gb.inputs["Emission Color"])
    gb.inputs["Emission Strength"].default_value = 1.6
    me = ob.data
    me.materials.clear()
    for m in (body, team, glow):
        me.materials.append(m)


def assign(ob, slot):
    ob.data.polygons.foreach_set("material_index", slot)
    ob.data.update()
    used = sorted(set(slot.tolist()))
    # drop unused slots (keeps the GLB to the materials it needs)
    me = ob.data
    for i in reversed(range(len(me.materials))):
        if i not in used and i != 0:
            me.materials.pop(index=i)
            idx = np.empty(len(me.polygons), np.int32)
            me.polygons.foreach_get("material_index", idx)
            idx[idx > i] -= 1
            me.polygons.foreach_set("material_index", idx)
    me.update()
    return {m: int((slot == k).sum()) for k, m in enumerate(["body", "team", "glow"]) if (slot == k).any()}


# --- rigging ---------------------------------------------------------------------------------------------

class Rig:
    def __init__(self, ob):
        self.ob = ob
        ad = bpy.data.armatures.new(ob.name + "_rig")
        self.arm = bpy.data.objects.new(ob.name + "_rig", ad)
        bpy.context.scene.collection.objects.link(self.arm)
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode="EDIT")
        self.eb = ad.edit_bones
        self.weights = {}

    def bone(self, name, head, tail, parent=None):
        b = self.eb.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0, 0.05))
        b.roll = 0.0
        if parent:
            b.parent = self.eb[parent]
        b.use_deform = parent is not None or name != "root"
        return b

    def finish(self, weights):
        bpy.ops.object.mode_set(mode="OBJECT")
        ob = self.ob
        tot = np.zeros(len(ob.data.vertices), np.float32)
        for w in weights.values():
            tot += w
        tot = np.maximum(tot, 1e-6)
        for name, w in weights.items():
            vg = ob.vertex_groups.new(name=name)
            w = w / tot
            for i in np.nonzero(w > 0.002)[0]:
                vg.add([int(i)], float(w[i]), "REPLACE")
        ob.parent = self.arm
        mod = ob.modifiers.new("rig", "ARMATURE")
        mod.object = self.arm
        for pb in self.arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
        return self.arm


def rig_hover(ob, lo, hi):
    H = hi[2] - lo[2]
    r = Rig(ob)
    r.bone("root", (0, 0, 0), (0, 0, 0.2 * H))
    r.bone("body", (0, 0, 0.35 * H), (0, 0, 0.8 * H), "root")
    v = verts_np(ob)
    return r.finish({"body": np.ones(len(v), np.float32)}), {"H": H}


def leg_columns(v, hip_z, cx):
    """Centre and radius of the two leg columns from the lowest vertices on each side."""
    out = {}
    low = v[v[:, 2] < 0.3 * hip_z]
    for side, sgn in (("L", 1), ("R", -1)):
        s = low[(low[:, 0] - cx) * sgn > 0]
        if len(s) < 8:
            s = low
        c = np.median(s[:, :2], 0)
        d = np.linalg.norm(s[:, :2] - c, axis=1)
        out[side] = (c, float(np.percentile(d, 92)) * 1.25 + 0.02)
    return out


def rig_biped(ob, lo, hi, cfg):
    H = hi[2] - lo[2]
    v = verts_np(ob)
    hz = cfg["hip"] * H
    cx = float(np.median(v[:, 0]))
    cols = leg_columns(v, hz, cx)
    knee = 0.5 * hz
    r = Rig(ob)
    r.bone("root", (0, 0, 0), (0, 0, 0.15 * H))
    r.bone("hips", (cx, 0, hz), (cx, 0, hz + 0.12 * H), "root")
    r.bone("torso", (cx, 0, hz + 0.12 * H), (cx, 0, 0.85 * H), "hips")
    w = {}
    leg_sum = np.zeros(len(v), np.float32)
    for side in ("L", "R"):
        c, rad = cols[side]
        r.bone("thigh_" + side, (c[0], c[1], hz), (c[0], c[1], knee), "hips")
        r.bone("shin_" + side, (c[0], c[1], knee), (c[0], c[1], 0.04 * H), "thigh_" + side)
        d = np.linalg.norm(v[:, :2] - c, axis=1)
        inside = smooth(rad * 1.25, rad * 0.85, d)
        sidew = smooth(-0.02 * H, 0.03 * H, (v[:, 0] - cx) * (1 if side == "L" else -1))
        leg = inside * sidew * smooth(hz + 0.06 * H, hz - 0.08 * H, v[:, 2])
        shin = smooth(knee + 0.08 * H, knee - 0.08 * H, v[:, 2])
        w["thigh_" + side] = leg * (1 - shin)
        w["shin_" + side] = leg * shin
        leg_sum += leg
    rest = np.clip(1 - leg_sum, 0, 1)
    up = smooth(hz, hz + 0.2 * H, v[:, 2])
    w["torso"] = rest * up
    w["hips"] = rest * (1 - up)
    return r.finish(w), {"H": H, "hz": hz}


def rig_legs(ob, lo, hi, cfg):
    """Body plus n legs per side; legs are the low vertices outside the body core."""
    H = hi[2] - lo[2]
    v = verts_np(ob)
    top = cfg["leg_top"] * H
    halfw = max(1e-3, (hi[0] - lo[0]) / 2)
    core = cfg["core"] * halfw
    n = cfg["legs"]
    r = Rig(ob)
    r.bone("root", (0, 0, 0), (0, 0, 0.15 * H))
    r.bone("body", (0, 0.25 * (hi[1] - lo[1]) / 2, top), (0, -0.25 * (hi[1] - lo[1]) / 2, top), "root")
    w = {}
    leg_sum = np.zeros(len(v), np.float32)
    low = v[(v[:, 2] < 0.35 * top) & (np.abs(v[:, 0]) > core * 0.6)]
    if len(low) < 10:
        low = v[v[:, 2] < 0.35 * top]
    y0, y1 = float(low[:, 1].min()), float(low[:, 1].max())
    feet = {}
    for side, sgn in (("L", 1), ("R", -1)):
        s = low[low[:, 0] * sgn > 0]
        for k in range(n):
            a, b = y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
            band = s[(s[:, 1] >= a) & (s[:, 1] <= b)]
            foot = np.median(band, 0) if len(band) else np.array([sgn * core * 1.5, (a + b) / 2, 0])
            feet[(side, k)] = (foot, a, b)
    for (side, k), (foot, a, b) in feet.items():
        sgn = 1 if side == "L" else -1
        name = "leg_%s%d" % (side, k)
        hip = (sgn * core * 0.8, (a + b) / 2, top)
        r.bone(name, hip, (foot[0], foot[1], 0.03 * H), "body")
        pad = 0.15 * (b - a)
        band = smooth(a - pad, a + pad, v[:, 1]) * smooth(b + pad, b - pad, v[:, 1])
        if k == 0:
            band = smooth(b + pad, b - pad, v[:, 1])                       # the front-most band runs to the end
        if k == n - 1:
            band = smooth(a - pad, a + pad, v[:, 1]) if n > 1 else np.ones(len(v), np.float32)
        side_w = smooth(core * 0.6, core * 1.05, v[:, 0] * sgn)
        leg = band * side_w * smooth(top + 0.03 * H, top - 0.12 * H, v[:, 2])
        w[name] = leg
        leg_sum += leg
    w["body"] = np.clip(1 - leg_sum, 0, 1)
    return r.finish(w), {"H": H, "n": n, "L": hi[1] - lo[1]}


def rig_wings(ob, lo, hi, cfg):
    H = hi[2] - lo[2]
    v = verts_np(ob)
    halfw = max(1e-3, (hi[0] - lo[0]) / 2)
    core = cfg["core"] * halfw
    cz = float(np.median(v[:, 2]))
    r = Rig(ob)
    r.bone("root", (0, 0, 0), (0, 0, 0.15 * H))
    r.bone("body", (0, 0.2, cz), (0, -0.2, cz), "root")
    w = {}
    tot = np.zeros(len(v), np.float32)
    for side, sgn in (("L", 1), ("R", -1)):
        r.bone("wing_" + side, (sgn * core, 0, cz), (sgn * halfw, 0, cz), "body")
        wg = smooth(core * 0.7, core * 1.3, v[:, 0] * sgn)
        w["wing_" + side] = wg
        tot += wg
    w["body"] = np.clip(1 - tot, 0, 1)
    return r.finish(w), {"H": H}


# --- animation -------------------------------------------------------------------------------------------

def rest_rot(pb):
    return pb.bone.matrix_local.to_3x3()


def pose(pb, rot_world=None, loc_world=None):
    """Set a pose bone from a rotation and offset given in armature (world) axes."""
    R = rest_rot(pb)
    Ri = R.inverted()
    if rot_world is not None:
        q = (Ri @ rot_world.to_matrix() @ R).to_quaternion()
    else:
        q = Quaternion()
    pb.rotation_quaternion = q
    pb.location = Ri @ (loc_world if loc_world is not None else Vector())


def rx(deg):
    return Quaternion((1, 0, 0), math.radians(deg))


def ry(deg):
    return Quaternion((0, 1, 0), math.radians(deg))


def rz(deg):
    return Quaternion((0, 0, 1), math.radians(deg))


def key_all(arm, frame):
    for pb in arm.pose.bones:
        for path in ("location", "rotation_quaternion"):
            pb.keyframe_insert(path, frame=frame, group=pb.name)


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)


def bump(t, c, w):
    """A smooth bump in [0, 1] of half-width w centred at c (t, c in cycle fractions)."""
    d = abs(((t - c + 0.5) % 1.0) - 0.5)
    return 0.5 + 0.5 * math.cos(math.pi * min(1.0, d / w)) if d < w else 0.0


def env(t, a, peak, b):
    """Attack envelope: 0 at t=a, 1 at peak, back to 0 at b (ease in-out)."""
    if t <= a or t >= b:
        return 0.0
    if t < peak:
        x = (t - a) / (peak - a)
    else:
        x = 1 - (t - peak) / (b - peak)
    return x * x * (3 - 2 * x)


def anim_hover(arm, clip, t, P):
    H = P["H"]
    body = arm.pose.bones["body"]
    s = math.sin(2 * math.pi * t)
    c = math.cos(2 * math.pi * t)
    if clip == "idle_loop":
        pose(body, rx(1.5 * s) @ ry(1.2 * c), Vector((0, 0, 0.03 * H * s)))
    elif clip in ("walk_loop", "fly_loop"):
        pose(body, rx(-9 + 1.5 * math.sin(4 * math.pi * t)) @ ry(2.5 * s), Vector((0, 0, 0.02 * H * math.sin(4 * math.pi * t))))
    else:
        e = env(t, 0.0, 0.3, 0.95)
        pose(body, rx(-14 * e), Vector((0, -0.08 * H * e, -0.03 * H * e)))


def anim_biped(arm, clip, t, P, cfg):
    H = P["H"]
    pb = arm.pose.bones
    if clip == "walk_loop":
        a = 2 * math.pi * t
        for side, ph in (("L", 0.0), ("R", math.pi)):
            sw = math.sin(a + ph)                      # +1: leg forward
            lift = max(0.0, math.cos(a + ph))          # recovery half: knee bends
            pose(pb["thigh_" + side], rx(-30 * sw - 10 * lift))
            pose(pb["shin_" + side], rx(38 * lift))
        bob = abs(math.cos(a)) * 0.03 * H
        pose(pb["hips"], rz(5 * math.sin(a)), Vector((0, 0, bob - 0.015 * H)))
        pose(pb["torso"], rz(-7 * math.sin(a)) @ rx(-4))
    elif clip == "idle_loop":
        s = math.sin(2 * math.pi * t)
        pose(pb["hips"], None, Vector((0, 0, -0.006 * H * (1 + s))))
        pose(pb["torso"], rx(1.6 * s) @ rz(1.2 * math.cos(2 * math.pi * t)))
        for side in ("L", "R"):
            pose(pb["thigh_" + side])
            pose(pb["shin_" + side])
    else:
        if cfg.get("attack") == "lunge":
            e = env(t, 0.0, 0.3, 0.95)
            pose(pb["torso"], rx(-24 * e) @ rz(10 * e))
            pose(pb["hips"], rx(-6 * e), Vector((0, -0.07 * H * e, -0.03 * H * e)))
        else:
            e = env(t, 0.0, 0.12, 0.8)
            pose(pb["torso"], rx(11 * e))
            pose(pb["hips"], None, Vector((0, 0.04 * H * e, 0)))
        for side in ("L", "R"):
            pose(pb["thigh_" + side])
            pose(pb["shin_" + side])


def anim_legs(arm, clip, t, P, cfg):
    H, n = P["H"], P["n"]
    pb = arm.pose.bones
    body = pb["body"]
    a = 2 * math.pi * t
    if clip == "walk_loop":
        for side, sp in (("L", 0.0), ("R", math.pi)):
            for k in range(n):
                ph = sp + k * math.pi                  # alternate tripod / diagonal gait
                sw = math.sin(a + ph)
                lift = max(0.0, math.cos(a + ph))
                out = 1 if side == "L" else -1
                pose(pb["leg_%s%d" % (side, k)], rx(-22 * sw) @ ry(out * 14 * lift))
        pose(body, ry(2.0 * math.sin(a)) @ rx(1.0 * math.sin(2 * a)),
             Vector((0, 0, 0.022 * H * abs(math.sin(a)) - 0.011 * H)))
    elif clip == "idle_loop":
        s = math.sin(a)
        pose(body, rx(1.2 * s), Vector((0, 0, -0.008 * H * (1 + s))))
        for b in pb:
            if b.name.startswith("leg_"):
                pose(b)
    else:
        if cfg.get("attack") == "recoil":
            e = env(t, 0.0, 0.1, 0.75)
            pose(body, rx(8 * e), Vector((0, 0.05 * P["L"] * e, -0.02 * H * e)))
        else:
            e = env(t, 0.0, 0.3, 0.95)
            pose(body, rx(-9 * e), Vector((0, -0.08 * P["L"] * e, -0.03 * H * e)))
        for b in pb:
            if b.name.startswith("leg_"):
                pose(b)


def anim_wings(arm, clip, t, P):
    H = P["H"]
    pb = arm.pose.bones
    a = 2 * math.pi * t
    beats = 1 if clip == "idle_loop" else 2
    flap = math.sin(beats * a)
    for side, sgn in (("L", 1), ("R", -1)):
        pose(pb["wing_" + side], ry(-sgn * (8 + 34 * flap)))
    if clip == "attack":
        e = env(t, 0.0, 0.3, 0.9)
        pose(pb["body"], rx(-16 * e), Vector((0, -0.12 * H * e, -0.05 * H * e)))
    else:
        pose(pb["body"], rx(-6 if clip == "fly_loop" else 0), Vector((0, 0, -0.05 * H * flap)))


CLIPS = {
    "hover": {"idle_loop": 2.0, "walk_loop": 1.0, "attack": 0.6},
    "biped": {"idle_loop": 2.0, "walk_loop": 0.9, "attack": 0.6},
    "legs": {"idle_loop": 2.0, "walk_loop": 1.0, "attack": 0.7},
    "wings": {"idle_loop": 0.8, "fly_loop": 0.5, "attack": 0.6},
}


def bake(arm, cfg, P):
    scn = bpy.context.scene
    scn.render.fps = FPS
    arm.animation_data_create()
    rig = cfg["rig"]
    clips = dict(CLIPS[rig])
    if cfg.get("air") and rig == "hover":
        clips = {"idle_loop": 2.4, "fly_loop": 1.6, "attack": 0.7}
    acts = {}
    for clip, secs in clips.items():
        frames = max(2, int(round(secs * FPS)))
        act = bpy.data.actions.new(clip)
        act.use_fake_user = True
        arm.animation_data.action = act
        for f in range(frames + 1):
            t = f / frames
            if rig == "hover":
                anim_hover(arm, clip, t, P)
            elif rig == "biped":
                anim_biped(arm, clip, t, P, cfg)
            elif rig == "legs":
                anim_legs(arm, clip, t, P, cfg)
            else:
                anim_wings(arm, clip, t, P)
            key_all(arm, f)
        acts[clip] = (act, frames)
    arm.animation_data.action = None
    clear_pose(arm)
    return acts


# --- export and checks ------------------------------------------------------------------------------------

def export(arm, ob, path, extra=()):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    ob.select_set(True)
    for e in extra:
        e.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False, export_animations=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                              export_image_format="JPEG", export_jpeg_quality=88)


def glb_report(path):
    with open(path, "rb") as fh:
        data = fh.read()
    ln = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + ln])
    acc = js.get("accessors", [])
    anims = []
    for a in js.get("animations", []):
        dur = max(acc[s["input"]]["max"][0] for s in a["samplers"])
        anims.append({"name": a["name"], "seconds": round(dur, 3), "channels": len(a["channels"])})
    tris = 0
    for m in js.get("meshes", []):
        for pr in m["primitives"]:
            tris += acc[pr["indices"]]["count"] // 3
    return {"animations": anims, "triangles": tris, "materials": [m["name"] for m in js.get("materials", [])],
            "images": len(js.get("images", [])), "joints": [len(s["joints"]) for s in js.get("skins", [])],
            "bytes": len(data)}


# --- review renders ---------------------------------------------------------------------------------------

def stage(dark=True):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 32
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("studio")
    sc.world = w
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.05, 0.053, 0.06, 1) if dark else (0.6, 0.6, 0.62, 1)
    bg.inputs[1].default_value = 1.0
    for name, col, energy, d in (("key", (1.0, 0.9, 0.78), 3.4, (-0.9, -1.3, 1.5)),
                                 ("rim", (0.55, 0.75, 1.0), 2.6, (1.3, 1.6, 0.9)),
                                 ("fill", (0.85, 0.9, 1.0), 0.8, (1.2, -1.0, 0.3))):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy, ld.color, ld.angle = energy, col, math.radians(8)
        o = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(o)
        o.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()
        ld.use_shadow = name == "key"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    principled(gm).inputs["Base Color"].default_value = (0.11, 0.1, 0.075, 1)
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


def world_pts(ob, limit=3000):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    mw = ob.matrix_world
    pts = [mw @ v.co for v in ev.data.vertices]
    return pts[::max(1, len(pts) // limit)]


def frame_cam(cam, pts, az, el, margin, ortho=False):
    sc = bpy.context.scene
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    cam.data.type = "ORTHO" if ortho else "PERSP"
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "AUTO"
    cam.data.angle = math.radians(30)
    cam.data.shift_x = cam.data.shift_y = 0.0
    dist = 12.0
    if ortho:
        cam.location = c + view_dir(az, el) * 30
        look(cam, c)
        cam.data.ortho_scale = max((hi - lo).length, 0.1) * 1.05
        return
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


def sheet(paths, out, cell=384, cols=4, bgc=(0.2, 0.21, 0.23)):
    tiles = []
    for p in paths:
        a = load_px(p)
        t = np.zeros((cell, cell, 4), np.float32)
        t[..., :3] = bgc
        t[..., 3] = 1
        h, w = a.shape[:2]
        if h > cell or w > cell:
            step = int(math.ceil(max(h, w) / cell))
            a = a[::step, ::step]
            h, w = a.shape[:2]
        y0, x0 = (cell - h) // 2, (cell - w) // 2
        al = a[..., 3:4]
        t[y0:y0 + h, x0:x0 + w, :3] = a[..., :3] * al + t[y0:y0 + h, x0:x0 + w, :3] * (1 - al)
        tiles.append(t)
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.concatenate(tiles[i:i + cols], axis=1) for i in range(0, len(tiles), cols)]
    s = np.concatenate(rows[::-1], axis=0)
    img = bpy.data.images.new("sheet", s.shape[1], s.shape[0], alpha=True)
    img.pixels.foreach_set(s.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def inspect(uid, ob):
    cam, ground, bg = stage(dark=False)
    ground.hide_render = True
    pts = world_pts(ob)
    out = os.path.join(HERE, "review", "inspect")
    shots = []
    for name, az, el in (("front_negY", 0, 5), ("right_posX", -90, 5), ("back_posY", 180, 5), ("top", 0, 89)):
        frame_cam(cam, pts, az, el, 0.05)
        shots.append(os.path.join(out, "%s_%s.png" % (uid, name)))
        render(shots[-1], (384, 384), False)
    sheet(shots, os.path.join(out, uid + "_inspect.png"))


def review(uid, ob, arm, acts, cfg, rnd):
    cam, ground, bg = stage()
    out = os.path.join(HERE, "review", "round%d" % rnd)
    shots = []
    lift = cfg.get("air", 0.0)
    ground.hide_render = True
    pts = world_pts(ob)
    frame_cam(cam, pts, 35, 24, 0.04)
    icon = os.path.join(ICONS, uid + ".png")
    render(icon, (256, 256), True)
    frame_cam(cam, pts, 35, 20, 0.08)
    shots.append(os.path.join(out, uid + "_front.png"))
    render(shots[-1], (512, 512), False)
    frame_cam(cam, pts, -140, 24, 0.08)
    shots.append(os.path.join(out, uid + "_back.png"))
    render(shots[-1], (512, 512), False)
    # animation frames, side-on: walk at two phases and the attack's peak
    move = "fly_loop" if "fly_loop" in acts else "walk_loop"
    for clip, frac in ((move, 0.25), (move, 0.75), ("attack", 0.3)):
        act, frames = acts[clip]
        arm.animation_data.action = act
        bpy.context.scene.frame_set(int(round(frac * frames)))
        bpy.context.view_layer.update()
        frame_cam(cam, world_pts(ob), 70, 12, 0.08)
        shots.append(os.path.join(out, "%s_%s_%02d.png" % (uid, clip, int(frac * 100))))
        render(shots[-1], (512, 512), False)
    arm.animation_data.action = None
    clear_pose(arm)
    bpy.context.view_layer.update()
    # the game camera: 55 degrees down from 25 m, 45 degree vertical field of view
    ground.hide_render = False
    cam.data.type = "PERSP"
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
    cam.data.angle = math.radians(45)
    cam.data.shift_x = cam.data.shift_y = 0.0
    arm.location.z += lift
    tgt = Vector((0, 0, 0.5 + lift))
    cam.location = tgt + view_dir(-25, 55) * 25
    look(cam, tgt)
    shots.append(os.path.join(out, uid + "_game.png"))
    render(shots[-1], (512, 512), False)
    arm.location.z -= lift
    sheet(shots + [icon], os.path.join(out, uid + "_sheet.png"))


# --- main ------------------------------------------------------------------------------------------------

def build(uid, rnd, only_inspect):
    cfg = UNITS[uid]
    ob = import_raw(uid)
    raw_tris = tri_count(ob)
    if "crop" in cfg:
        crop(ob, cfg["crop"])
    if only_inspect:
        fit(ob, dict(cfg, yaw=0.0))
        inspect(uid, ob)
        print("[tripo] inspect", uid, json.dumps({"raw_tris": raw_tris, "tris": tri_count(ob),
                                                  "materials": [m.name for m in ob.data.materials],
                                                  "images": [(i.name, list(i.size)) for i in bpy.data.images]}))
        return
    lo, hi = fit(ob, cfg)
    if cfg.get("bake"):
        ob, t0, t1 = rebake(ob, dict(cfg, id=uid))
    else:
        t0, t1 = decimate(ob, cfg["tris"])
    imgs = shrink_images(uid, 1024)
    img = base_image(ob)
    slot = classify(ob, img, cfg["race"], cfg.get("bone_sat", 0.42))
    cargo_mask = cargo_faces(ob, img) & (slot == 0) if cfg.get("cargo") else None
    make_materials(ob, cfg["race"])
    counts = assign(ob, slot)
    shade(ob)
    lo, hi = verts_np(ob).min(0), verts_np(ob).max(0)
    rig = cfg["rig"]
    if rig == "hover":
        arm, P = rig_hover(ob, lo, hi)
    elif rig == "biped":
        arm, P = rig_biped(ob, lo, hi, cfg)
    elif rig == "legs":
        arm, P = rig_legs(ob, lo, hi, cfg)
    else:
        arm, P = rig_wings(ob, lo, hi, cfg)
    acts = bake(arm, cfg, P)
    extra = []
    if cargo_mask is not None and cargo_mask.any():
        extra.append(split_cargo(ob, cargo_mask))
        counts["cargo"] = int(cargo_mask.sum())
    path = os.path.join(MODELS, uid + ".glb")
    export(arm, ob, path, extra)
    rep = glb_report(path)
    info = {"id": uid, "raw_tris": raw_tris, "decimated": [t0, t1], "size_m": [round(float(x), 3) for x in hi - lo],
            "faces_by_material": counts, "images": imgs, "bones": [b.name for b in arm.data.bones], "glb": rep}
    print("[tripo]", json.dumps(info))
    os.makedirs(os.path.join(HERE, "review"), exist_ok=True)
    with open(os.path.join(HERE, "review", uid + "_stats.json"), "w") as f:
        json.dump(info, f, indent=1)
    review(uid, ob, arm, acts, cfg, rnd)


def main():
    argv = argv_after()
    which = argv[0] if argv else "all"
    rnd = int(argv[argv.index("--round") + 1]) if "--round" in argv else 1
    ids = [u for u in UNITS if os.path.exists(os.path.join(RAW, u + ".glb"))] if which == "all" else which.split(",")
    for uid in ids:
        if uid not in UNITS:
            raise SystemExit("unknown id " + uid)
        build(uid, rnd, "--inspect" in argv)


if __name__ == "__main__":
    main()
