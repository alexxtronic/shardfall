"""Render build-menu icons for finished GLBs.

Usage:
  Blender --background --factory-startup --python art/kiln/icons.py -- <project root> <id> [<id> ...]

For each id, imports assets/models/<id>.glb into an empty scene and renders
assets/icons/<id>.png: 256 x 256, transparent, front-left three-quarter view from slightly
above, framed tight, warm key and cool rim light (the same look as the older icons, see
docs/ART_SPEC.md).
"""
import math
import os
import sys

import bpy
from mathutils import Vector


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras):
        for d in list(coll):
            coll.remove(d)


def setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48
    sc.render.resolution_x = sc.render.resolution_y = 256
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = sc.world or bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.62, 0.74, 1)
    bg.inputs[1].default_value = 0.75


def lights():
    for name, frm, col, energy in (("key", (-0.55, -0.85, 1.05), (1.0, 0.9, 0.76), 3.4),
                                   ("rim", (0.75, 0.95, 0.55), (0.62, 0.82, 1.0), 2.6)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.color = col
        ld.angle = math.radians(6)
        ob = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.rotation_euler = (-Vector(frm)).to_track_quat("-Z", "Y").to_euler()


def render_icon(root, bid):
    clear()
    setup()
    bpy.ops.import_scene.gltf(filepath=os.path.join(root, "assets", "models", bid + ".glb"))
    bpy.context.view_layer.update()
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre = (lo + hi) / 2
    lights()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = 50
    cam.data.clip_end = 500
    bpy.context.scene.camera = cam
    az, el = math.radians(-125), math.radians(24)
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    cam.location = centre + d * 20
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    loc, _ = cam.camera_fit_coords(dg, [c for p in pts for c in p])
    fwd = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    cam.location = Vector(loc) - fwd * (hi - lo).length * 0.08
    out = os.path.join(root, "assets", "icons", bid + ".png")
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("ICON", bid, out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    root, ids = argv[0], argv[1:]
    for bid in ids:
        render_icon(root, bid)


main()
