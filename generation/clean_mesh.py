#!/usr/bin/env python
"""
4dgs generation pipeline — mesh cleanup for rig-readiness.

WHY: TRELLIS/flexicubes meshes are geometrically valid but are POOR rigging inputs —
they carry many disconnected floaters and internal shells. The UniRig skeleton model
samples the SURFACE; internal surfaces + floaters give it a "filled blob" view, so the
AR decoder collapses (the crab -> 1 bone, see PROJECT.md D25). This pass turns a raw
TRELLIS mesh into a clean, single outer shell that the rig model can read.

WHAT IT DOES (in order):
  1. weld duplicate verts, drop degenerate/duplicate/non-manifold/unreferenced faces
  2. keep only connected components >= --keep-frac of the largest (kills floaters)
  3. (optional, --watertight) voxel-remesh to a single closed OUTER shell -> removes
     ALL internal geometry. Off by default because it blobs thin features (wings,
     fingers); use it when floater/internal removal alone isn't enough.

Reports component count + surface-area/bbox-density before & after — density dropping
toward the ~2-3x range (vs giraffe 2.26) is the signal the mesh is now rig-friendly.

Usage (either venv has open3d+trimesh):
  /home/sov2/projects/unirig-venv/bin/python generation/clean_mesh.py IN.obj OUT.obj
  ... --keep-frac 0.02 --watertight --voxel 256
"""
import argparse, sys
import numpy as np
import open3d as o3d


def density(v, f):
    """surface-area / bbox_area^(?) proxy: total area normalized by bbox area scale."""
    tri = v[f]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum()
    ext = v.max(0) - v.min(0)
    bbox_area = (ext[0] * ext[1] + ext[1] * ext[2] + ext[0] * ext[2]) + 1e-9
    return area / bbox_area


def stats(m, tag):
    v = np.asarray(m.vertices); f = np.asarray(m.triangles)
    if len(f) == 0:
        print(f"  [{tag}] EMPTY"); return
    tri_clusters, n_tri, _ = m.cluster_connected_triangles()
    ncomp = len(np.unique(np.asarray(tri_clusters)))
    print(f"  [{tag}] V={len(v):,} F={len(f):,} components={ncomp} "
          f"area/bbox-density={density(v, f):.2f} watertight={m.is_watertight()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--keep-frac", type=float, default=0.02,
                    help="keep connected components with >= this fraction of the largest component's triangles")
    ap.add_argument("--watertight", action="store_true",
                    help="voxel-remesh to a single closed outer shell (removes ALL internal geometry; blobs thin features)")
    ap.add_argument("--voxel", type=int, default=256, help="voxel grid resolution for --watertight")
    args = ap.parse_args()

    m = o3d.io.read_triangle_mesh(args.inp)
    if len(m.triangles) == 0:
        print(f"ERROR: no triangles in {args.inp}", file=sys.stderr); sys.exit(1)
    print(f"loaded {args.inp}")
    stats(m, "raw")

    # 1. basic repair / weld. NOTE: deliberately NOT calling remove_non_manifold_edges() —
    # on thin double-sided surfaces (butterfly wings) it is pathologically slow (hangs for
    # minutes) AND destructive (shreds the wings, which are legitimately non-manifold).
    m.remove_duplicated_vertices()
    m.remove_duplicated_triangles()
    m.remove_degenerate_triangles()
    m.remove_unreferenced_vertices()

    # 2. keep significant connected components
    tri_clusters, n_tri, _ = m.cluster_connected_triangles()
    tri_clusters = np.asarray(tri_clusters); n_tri = np.asarray(n_tri)
    if len(n_tri) > 1:
        thresh = args.keep_frac * n_tri.max()
        keep = {i for i, c in enumerate(n_tri) if c >= thresh}
        drop_mask = np.array([c not in keep for c in tri_clusters])
        m.remove_triangles_by_mask(drop_mask)
        m.remove_unreferenced_vertices()
        print(f"  components: {len(n_tri)} -> kept {len(keep)} "
              f"(dropped {drop_mask.sum():,} floater tris below {thresh:.0f})")
    stats(m, "components")

    # 3. optional watertight outer-shell remesh
    if args.watertight:
        v = np.asarray(m.vertices)
        ext = (v.max(0) - v.min(0)).max()
        pitch = ext / args.voxel
        vg = o3d.geometry.VoxelGrid.create_from_triangle_mesh(m, voxel_size=pitch)
        # rebuild a surface from the occupied voxels via Poisson on voxel centers + normals
        m.compute_vertex_normals()
        pcd = m.sample_points_poisson_disk(60000)
        rec, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)
        # crop to original bbox to drop Poisson's ballooning
        rec = rec.crop(m.get_axis_aligned_bounding_box())
        rec.remove_unreferenced_vertices()
        m = rec
        stats(m, "watertight")

    m.remove_unreferenced_vertices()
    o3d.io.write_triangle_mesh(args.out, m)
    print(f"saved {args.out}")
    stats(m, "final")


if __name__ == "__main__":
    main()
