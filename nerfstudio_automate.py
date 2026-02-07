import subprocess
from pathlib import Path

import trimesh


def train_and_export_floorplan(data_dir, colmap_sparse_path, output_dir, max_iterations=10000):
    """Complete pipeline: COLMAP data → NeRF → Mesh → Floor plan"""

    data_dir = Path(data_dir)
    colmap_sparse_path = Path(colmap_sparse_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("STEP 1: TRAINING NERF")
    print("=" * 60)

    # Train NeRF using COLMAP data
    # Note: Arguments before 'colmap' apply to nerfacto, after 'colmap' apply to the dataparser
    train_cmd = [
        "ns-train", "nerfacto",
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(max_iterations),
        "colmap",
        "--data", str(data_dir),
        "--colmap-path", "colmap/sparse/0"  # Relative to data directory
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

    # Find the most recent config.yml file
    config_files = list(output_dir.glob("**/config.yml"))
    if not config_files:
        print("❌ No config.yml found! Training may have failed.")
        return False

    # Get the most recent config
    config_path = sorted(config_files, key=lambda x: x.stat().st_mtime)[-1]
    print(f"Using config: {config_path}")

    # Create export directory
    export_dir = config_path.parent / "exports" / "mesh"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Export mesh using Poisson reconstruction
    export_cmd = [
        "ns-export", "poisson",
        "--load-config", str(config_path),
        "--output-dir", str(export_dir),
        "--num-points", "1000000",  # High quality mesh
        "--remove-outliers", "True"
    ]

    print(f"Running: {' '.join(export_cmd)}")
    result = subprocess.run(export_cmd)

    if result.returncode != 0:
        print("❌ Mesh export failed!")
        return False

    print("✓ Mesh export complete!")

    # Find the exported mesh
    mesh_files = list(export_dir.glob("*.ply"))
    if not mesh_files:
        print("❌ No mesh file found!")
        return False

    mesh_path = sorted(mesh_files, key=lambda x: x.stat().st_mtime)[-1]
    print(f"Mesh saved at: {mesh_path}")

    print("\n" + "=" * 60)
    print("STEP 3: GENERATING FLOOR PLAN")
    print("=" * 60)

    # Generate floor plan from mesh
    success = generate_floorplan_from_mesh(mesh_path, output_dir / "floorplan")

    if success:
        print("\n" + "=" * 60)
        print("✓ PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"\nFloor plan saved to: {output_dir / 'floorplan'}")
        print(f"  - PNG: {output_dir / 'floorplan' / 'floorplan.png'}")
        print(f"  - SVG: {output_dir / 'floorplan' / 'floorplan.svg'}")

    return success


def generate_floorplan_from_mesh(mesh_path, output_dir):
    """Convert mesh to floor plan by slicing at floor height"""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Loading mesh from: {mesh_path}")
        mesh = trimesh.load(mesh_path)

        print(f"Mesh bounds: {mesh.bounds}")
        print(f"Mesh has {len(mesh.vertices)} vertices")

        # Slice mesh at floor height (slightly above the lowest point)
        slice_height = mesh.bounds[0][2] + 0.1  # 10cm above lowest point
        print(f"Slicing at height: {slice_height}")

        slice_2d = mesh.section(plane_origin=[0, 0, slice_height],
                                plane_normal=[0, 0, 1])

        if slice_2d is None:
            print("❌ No valid slice found at this height!")
            print("Try adjusting the slice height or check if the mesh is valid.")
            return False

        print("✓ Slice created successfully")

        # Convert to 2D path
        slice_2d, _ = slice_2d.to_planar()

        # Export as SVG
        svg_path = output_dir / 'floorplan.svg'
        slice_2d.export(str(svg_path))
        print(f"✓ SVG saved: {svg_path}")

        # Export as PNG image
        from PIL import Image, ImageDraw

        img_size = 2000  # Higher resolution
        img = Image.new('RGB', (img_size, img_size), 'white')
        draw = ImageDraw.Draw(img)

        # Scale and draw paths
        vertices = slice_2d.vertices
        if len(vertices) > 0:
            # Normalize to image space
            vertices = (vertices - vertices.min(axis=0)) / (vertices.max(axis=0) - vertices.min(axis=0))
            vertices = vertices * (img_size - 100) + 50  # Add 50px padding

            # Draw all entities
            for entity in slice_2d.entities:
                points = vertices[entity.points].tolist()
                if len(points) > 1:
                    draw.line([tuple(p) for p in points], fill='black', width=5)

        png_path = output_dir / 'floorplan.png'
        img.save(str(png_path))
        print(f"✓ PNG saved: {png_path}")

        return True

    except Exception as e:
        print(f"❌ Error generating floor plan: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Configuration
    DATA_DIR = "./data/room_1"
    COLMAP_SPARSE_PATH = "./data/room_1/colmap/sparse/0"
    OUTPUT_DIR = "./output/room_1"
    MAX_ITERATIONS = 10000  # Reduce for faster testing (e.g., 5000)

    print("Starting automated floor plan generation...")
    print(f"Data directory: {DATA_DIR}")
    print(f"COLMAP path: {COLMAP_SPARSE_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print()

    success = train_and_export_floorplan(
        DATA_DIR,
        COLMAP_SPARSE_PATH,
        OUTPUT_DIR,
        MAX_ITERATIONS
    )

    if success:
        print("\n🎉 All done! Check your output directory for the floor plan.")
    else:
        print("\n❌ Pipeline failed. Check errors above.")
