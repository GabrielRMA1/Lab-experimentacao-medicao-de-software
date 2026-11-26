
import argparse
import json
import math
import os
import random
import sys
import tempfile
import time

import bpy
from mathutils import Vector


def parse_args(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--workload", choices=["diffuse", "glass"], required=True)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--res-x", type=int, default=640)
    ap.add_argument("--res-y", type=int, default=360)
    ap.add_argument("--png", default="", help="onde salvar a imagem renderizada (opcional)")
    return ap.parse_args(argv)


def set_input(node, names, value):
    """Os nomes dos sockets do Principled BSDF mudaram entre versões; tenta cada nome."""
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return True
    return False


def make_material(name, color, roughness, metallic=0.0, transmission=0.0):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True  
    except Exception:
        pass
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf, ["Base Color"], (*color, 1.0))
    set_input(bsdf, ["Roughness"], roughness)
    set_input(bsdf, ["Metallic"], metallic)
    set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
    set_input(bsdf, ["IOR"], 1.45)
    return mat


def build_scene(workload):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rng = random.Random(42) 


    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.data.materials.append(make_material("floor", (0.55, 0.55, 0.6), 0.35))

   
    for ix in range(6):
        for iy in range(5):
            x = (ix - 2.5) * 1.5
            y = (iy - 2.0) * 1.5
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=0.55, location=(x, y, 0.55))
            obj = bpy.context.active_object
            obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
            color = (rng.random() * 0.8 + 0.1, rng.random() * 0.8 + 0.1, rng.random() * 0.8 + 0.1)
            kind = (ix + iy) % 3
            if workload == "diffuse":
                mat = make_material(f"m{ix}{iy}", color, roughness=0.6 + 0.1 * kind)
            else:
                if kind == 0:
                    mat = make_material(f"m{ix}{iy}", (1, 1, 1), roughness=0.03, transmission=1.0)
                elif kind == 1:
                    mat = make_material(f"m{ix}{iy}", color, roughness=0.12, metallic=1.0)
                else:
                    mat = make_material(f"m{ix}{iy}", color, roughness=0.2)
            obj.data.materials.append(mat)

    bpy.ops.object.light_add(type="AREA", location=(4, -5, 9))
    key = bpy.context.active_object
    key.data.energy = 2500
    key.data.size = 6
    key.rotation_euler = (math.radians(25), math.radians(10), math.radians(15))
    bpy.ops.object.light_add(type="AREA", location=(-6, 5, 6))
    fill = bpy.context.active_object
    fill.data.energy = 800
    fill.data.size = 4
    fill.rotation_euler = (math.radians(-35), math.radians(-15), math.radians(-20))

    world = bpy.data.worlds.new("world")
    world.color = (0.05, 0.05, 0.07)
    scene.world = world

    bpy.ops.object.camera_add(location=(0, -13, 7))
    cam = bpy.context.active_object
    direction = Vector((0, 0, 0.5)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 40
    scene.camera = cam
    return scene


def configure_render(scene, workload, samples, threads, res_x, res_y):
    scene.render.engine = "CYCLES"
    cy = scene.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = False
    cy.use_denoising = False
    cy.seed = 0
    cy.use_animated_seed = False
    bounces = {"diffuse": (4, 2, 2, 2), "glass": (12, 4, 8, 8)}[workload]
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces, cy.transmission_bounces = bounces
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = threads
    scene.render.use_persistent_data = False
    scene.render.image_settings.file_format = "PNG"


def image_mean(path):
    import numpy as np 
    img = bpy.data.images.load(path)
    arr = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(arr)
    return float(arr.reshape(-1, 4)[:, :3].mean())


def main():
    args = parse_args(sys.argv)
    t_build = time.perf_counter()
    scene = build_scene(args.workload)
    configure_render(scene, args.workload, args.samples, args.threads, args.res_x, args.res_y)
    build_s = time.perf_counter() - t_build

    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=False)
    render_s = time.perf_counter() - t0

    png = args.png or os.path.join(tempfile.gettempdir(), f"lab05_{os.getpid()}.png")
    bpy.data.images["Render Result"].save_render(png)
    mean = image_mean(png)
    if not args.png:
        try:
            os.remove(png)
        except OSError:
            pass

    result = {
        "blender_version": bpy.app.version_string,
        "workload": args.workload,
        "samples": args.samples,
        "threads": args.threads,
        "resolution": f"{args.res_x}x{args.res_y}",
        "render_s": round(render_s, 4),
        "build_s": round(build_s, 4),
        "image_mean": round(mean, 5),
    }
    print("BENCH_RESULT " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
