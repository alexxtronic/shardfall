"""Blender finishing pass for Kiln building GLBs.

Kiln exports every part as its own mesh, which costs one draw call per part per
material. This merges a model into one body mesh (one draw per material) and
keeps the nodes the game animates as their own small meshes:
  float*   bobs up and down (Models.attach_building)
  turret*  turns toward the target

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python art/kiln/finish.py -- IN.glb OUT.glb
"""
import sys

import bpy

SPECIAL = ("float", "turret")


def is_special(ob):
    n = ob.name.lower()
    return ob.type == "EMPTY" and any(n.startswith(s) or ("_" + s) in n for s in SPECIAL)


def special_owner(ob):
    p = ob.parent
    while p:
        if is_special(p):
            return p
        p = p.parent
    return None


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, dst = argv[0], argv[1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    groups = {}
    for m in meshes:
        groups.setdefault(special_owner(m), []).append(m)
    # detach every mesh into world space first, so joins keep their placement
    for m in meshes:
        mw = m.matrix_world.copy()
        m.parent = None
        m.matrix_world = mw
    for owner, objs in groups.items():
        if owner is None:
            continue
        ob = join(objs, owner.name + "_mesh")
        # bake world transform into the mesh, then hang it under the special node
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        inv = owner.matrix_world.inverted()
        ob.data.transform(inv)
        ob.parent = owner
        ob.matrix_parent_inverse.identity()
        ob.matrix_basis.identity()
    body = groups.get(None, [])
    if body:
        ob = join(body, "body")
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # specials to the top level, other empties go
    for o in list(bpy.context.scene.objects):
        if is_special(o):
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    for o in list(bpy.context.scene.objects):
        if o.type == "EMPTY" and not is_special(o):
            bpy.data.objects.remove(o, do_unlink=True)
    tris = sum(len(p.vertices) - 2 for o in bpy.context.scene.objects if o.type == "MESH" for p in o.data.polygons)
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_apply=True, export_yup=True)
    print("FINISH", dst, "objects", [o.name for o in bpy.context.scene.objects], "tris", tris)


main()
