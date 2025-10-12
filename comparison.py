# comparison.py
"""
Creates a comparison GIF from two existing sets of animation frames.
Combines frames vertically to show a side-by-side (top/bottom) comparison.
"""

import glob
from pathlib import Path
from PIL import Image
import os

import config


def create_comparison_gif():
    """
    Generates a GIF comparing two model runs by stacking their frames vertically.
    """
    if not config.enable_comparison_gif:
        print("Comparison GIF creation is disabled in config.py.")
        return

    print(f"\n{'='*60}")
    print("CREATING COMPARISON GIF")
    print(f"{'='*60}")

    # Define source and output directories
    source_dir1 = Path(config.comparison_source_dir_1)
    source_dir2 = Path(config.comparison_source_dir_2)

    # Extract model and run number from paths (e.g., 'isostatic_01')
    run1_name = f"{source_dir1.parent.name}_{source_dir1.name}"
    run2_name = f"{source_dir2.parent.name}_{source_dir2.name}"
    output_filename = f"{run1_name}_vs_{run2_name}.gif"
    print(f"Automatically generated output filename: {output_filename}")
    
    output_dir_base = Path("output") / "comparisons"
    output_dir_frames = output_dir_base / "frames"
    output_dir_gifs = output_dir_base / "gifs"
    
    # Create output directories if they don't exist
    output_dir_frames.mkdir(parents=True, exist_ok=True)
    output_dir_gifs.mkdir(parents=True, exist_ok=True)

    # Find all frame images in the source directories
    frames1 = sorted(glob.glob(str(source_dir1 / 'frame_*.png')))
    frames2 = sorted(glob.glob(str(source_dir2 / 'frame_*.png')))

    if not frames1 or not frames2:
        print("Error: Could not find frames in one or both source directories.")
        print(f"  - Searched in: {source_dir1}")
        print(f"  - Searched in: {source_dir2}")
        return

    # Use the smaller number of frames to avoid errors
    num_frames = min(len(frames1), len(frames2))
    if len(frames1) != len(frames2):
        print(f"Warning: Frame counts differ. Using the smaller count: {num_frames} frames.")

    print(f"Found {num_frames} frames to process in each directory.")
    print("Stitching frames...")

    stitched_frame_paths = []
    for i in range(num_frames):
        # Open the two frames
        img1 = Image.open(frames1[i])
        img2 = Image.open(frames2[i])
        
        # Get dimensions
        width1, height1 = img1.size
        width2, height2 = img2.size
        
        # Create a new image with combined height
        total_width = max(width1, width2)
        total_height = height1 + height2
        stitched_image = Image.new('RGB', (total_width, total_height))
        
        # Paste the two images
        stitched_image.paste(img1, (0, 0))
        stitched_image.paste(img2, (0, height1))
        
        # Save the new stitched frame
        frame_name = Path(frames1[i]).name
        output_path = output_dir_frames / frame_name
        stitched_image.save(output_path)
        stitched_frame_paths.append(output_path)
        
        if (i + 1) % 10 == 0:
            print(f"  ... stitched {i + 1}/{num_frames} frames")
    
    print("\nStitching complete!")
    print("Creating final comparison GIF...")
    
    # Create the GIF from the stitched frames
    final_gif_path = output_dir_gifs / output_filename
    gif_frames = [Image.open(f) for f in stitched_frame_paths]
    
    gif_frames[0].save(
        final_gif_path,
        save_all=True,
        append_images=gif_frames[1:],
        optimize=False,
        duration=1000 / config.animation_fps,
        loop=0
    )
    
    print(f"  ✓ Comparison GIF saved: {final_gif_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    create_comparison_gif()