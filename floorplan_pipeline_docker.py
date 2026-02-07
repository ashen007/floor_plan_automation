"""
Floor Plan Generation Pipeline - Docker Edition
Optimized for cloud GPU deployment
"""

import argparse
import os
import subprocess
from pathlib import Path

import trimesh


def train_and_export_floorplan(data_dir, colmap_sparse_path, output_dir, max_iterations=10000):
    """Complete pipeline: COLMAP data → NeRF → Mesh → Floor plan"""

    data_dir = Path(data_dir)
    colmap_sparse_path = Path(colmap_sparse_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if data exists
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return False

    if not colmap_sparse_path.exists():
        print(f"❌ COLMAP data not found: {colmap_sparse_path}")
        return False

    print("=" * 60)
    print("STEP 1: TRAINING NERF")
    print("=" * 60)
    print(f"Data: {data_dir}")
    print(f"COLMAP: {colmap_sparse_path}")
    print(f"Output: {output_dir}")
    print(f"Iterations: {max_iterations}")
    print()

    # Train NeRF
    train_cmd = [
        "ns-train", "nerfacto",
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(max_iterations),
        "colmap",
        "--data", str(data_dir),
        "--colmap-path", "colmap/sparse/0"
    ]

    print(f"Running: {' '.join(train_cmd)}")
    result = subprocess.run(train_cmd)

    if result.returncode != 0:
        print("❌ Training failed!")
        return False

    print("✓ Training complete!")

    print("\n" + "=" * 60)
    print("STEP 2: EXPORTING MESH")
    print("=" * 60)

    # Find config file
    config_files = list(output_dir.glob("**/config.yml"))
    if not config_files:
        print("❌ No config.yml found!")
        return False

    config_path = sorted(config_files, key=lambda x: x.stat().st_mtime)[-1]
    print(f"Using config: {config_path}")

    # Export mesh
    export_dir = config_path.parent / "exports" / "mesh"
    export_dir.mkdir(parents=True, exist_ok=True)

    export_cmd = [
        "ns-export", "poisson",
        "--load-config", str(config_path),
        "--output-dir", str(export_dir),
        "--num-points", "1000000",
        "--remove-outliers", "True"
    ]

    print(f"Running: {' '.join(export_cmd)}")
    result = subprocess.run(export_cmd)

    if result.returncode != 0:
        print("❌ Mesh export failed!")
        return False

    print("✓ Mesh export complete!")

    # Find mesh file
    mesh_files = list(export_dir.glob("*.ply"))
    if not mesh_files:
        print("❌ No mesh file found!")
        return False

    mesh_path = sorted(mesh_files, key=lambda x: x.stat().st_mtime)[-1]
    print(f"Mesh: {mesh_path}")

    print("\n" + "=" * 60)
    print("STEP 3: GENERATING FLOOR PLAN")
    print("=" * 60)

    # Generate floor plan
    success = generate_floorplan_from_mesh(mesh_path, output_dir / "floorplan")

    if success:
        print("\n" + "=" * 60)
        print("✓ PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"\nResults:")
        print(f"  PNG: {output_dir / 'floorplan' / 'floorplan.png'}")
        print(f"  SVG: {output_dir / 'floorplan' / 'floorplan.svg'}")

    return success


def generate_floorplan_from_mesh(mesh_path, output_dir):
    """Convert mesh to floor plan"""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Loading mesh: {mesh_path}")
        mesh = trimesh.load(mesh_path)

        print(f"Mesh: {len(mesh.vertices)} vertices")
        print(f"Bounds: {mesh.bounds}")

        # Slice at floor height
        slice_height = mesh.bounds[0][2] + 0.1
        print(f"Slicing at: {slice_height}")

        slice_2d = mesh.section(plane_origin=[0, 0, slice_height],
                                plane_normal=[0, 0, 1])

        if slice_2d is None:
            print("❌ No valid slice!")
            return False

        print("✓ Slice created")

        # Convert to 2D
        slice_2d, _ = slice_2d.to_planar()

        # Export SVG
        svg_path = output_dir / 'floorplan.svg'
        slice_2d.export(str(svg_path))
        print(f"✓ SVG: {svg_path}")

        # Export PNG
        from PIL import Image, ImageDraw

        img_size = 2000
        img = Image.new('RGB', (img_size, img_size), 'white')
        draw = ImageDraw.Draw(img)

        vertices = slice_2d.vertices
        if len(vertices) > 0:
            vertices = (vertices - vertices.min(axis=0)) / (vertices.max(axis=0) - vertices.min(axis=0))
            vertices = vertices * (img_size - 100) + 50

            for entity in slice_2d.entities:
                points = vertices[entity.points].tolist()
                if len(points) > 1:
                    draw.line([tuple(p) for p in points], fill='black', width=5)

        png_path = output_dir / 'floorplan.png'
        img.save(str(png_path))
        print(f"✓ PNG: {png_path}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate floor plan from images')
    parser.add_argument('--data', type=str, default='/workspace/data/room_1',
                        help='Path to data directory')
    parser.add_argument('--output', type=str, default='/workspace/output/room_1',
                        help='Path to output directory')
    parser.add_argument('--iterations', type=int, default=10000,
                        help='Training iterations (default: 10000, reduce for faster testing)')

    args = parser.parse_args()

    DATA_DIR = args.data
    COLMAP_SPARSE_PATH = f"{args.data}/colmap/sparse/0"
    OUTPUT_DIR = args.output
    MAX_ITERATIONS = args.iterations

    print("=" * 60)
    print("FLOOR PLAN GENERATION PIPELINE")
    print("=" * 60)
    print(f"Data: {DATA_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Iterations: {MAX_ITERATIONS}")
    print()

    # Check if running in Docker
    if os.path.exists('/.dockerenv'):
        print("✓ Running in Docker")
    else:
        print("⚠ Not running in Docker")

    # Check GPU
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ GPU detected")
        else:
            print("⚠ No GPU detected")
    except:
        print("⚠ Could not check GPU")

    print()

    success = train_and_export_floorplan(
        DATA_DIR,
        COLMAP_SPARSE_PATH,
        OUTPUT_DIR,
        MAX_ITERATIONS
    )

    if success:
        print("\n🎉 Done! Check output directory for results.")
        exit(0)
    else:
        print("\n❌ Pipeline failed.")
        exit(1)
