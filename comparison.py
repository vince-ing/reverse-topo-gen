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


def create_comparison_gif_from_paths(path1, path2, reverse_animation=None):
    """
    Create a comparison GIF from two paths (can be frame directories or GIF files).
    
    Args:
        path1: Path to first run (frames directory or GIF file)
        path2: Path to second run (frames directory or GIF file)
        reverse_animation: If True, reverse frame order. If None, use config setting.
    
    Returns:
        Path: Path to the created comparison GIF
    """
    print(f"\n{'='*60}")
    print("CREATING COMPARISON GIF FROM PATHS")
    print(f"{'='*60}")
    
    # Use config setting if not specified
    if reverse_animation is None:
        reverse_animation = config.reverse_animation
    
    print(f"Reverse animation (forward in time): {reverse_animation}")
    
    path1 = Path(path1)
    path2 = Path(path2)
    
    # Determine if paths are directories (frames) or files (GIFs)
    frames1 = _get_frames_from_path(path1)
    frames2 = _get_frames_from_path(path2)
    
    if not frames1 or not frames2:
        print("Error: Could not extract frames from one or both paths.")
        return None
    
    # Generate output filename
    name1 = _get_run_name(path1)
    name2 = _get_run_name(path2)
    output_filename = f"{name1}_vs_{name2}.gif"
    print(f"Output filename: {output_filename}")
    
    # Create comparison
    output_path = _create_comparison_from_frames(frames1, frames2, output_filename, reverse_animation)
    
    print(f"\n{'='*60}")
    print(f"COMPARISON COMPLETE")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")
    
    return output_path


def _get_frames_from_path(path):
    """
    Get frame file paths from either a directory or a GIF file.
    
    Args:
        path: Path to frames directory or GIF file
    
    Returns:
        list: List of frame paths (for directory) or PIL Image objects (for GIF)
    """
    path = Path(path)
    
    if path.is_dir():
        # It's a frames directory
        frames = sorted(glob.glob(str(path / 'frame_*.png')))
        print(f"Found {len(frames)} frames in directory: {path}")
        return frames
    
    elif path.is_file() and path.suffix == '.gif':
        # It's a GIF file - extract frames to temp directory
        print(f"Extracting frames from GIF: {path}")
        temp_dir = Path("output/comparisons/temp") / path.stem
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        gif = Image.open(path)
        frames = []
        
        for i in range(gif.n_frames):
            gif.seek(i)
            frame_path = temp_dir / f"frame_{i:03d}.png"
            # Convert to RGB in case of palette mode
            frame_rgb = gif.convert('RGB')
            frame_rgb.save(frame_path)
            frames.append(str(frame_path))
        
        print(f"Extracted {len(frames)} frames to: {temp_dir}")
        return frames
    
    else:
        print(f"Error: Invalid path type: {path}")
        return None


def _get_run_name(path):
    """
    Generate a descriptive name for a run based on its path.
    
    Args:
        path: Path to frames directory or GIF file
    
    Returns:
        str: Descriptive name
    """
    path = Path(path)
    
    if path.is_dir():
        # For directory: model_runnumber (e.g., isostatic_01)
        return f"{path.parent.name}_{path.name}"
    elif path.is_file():
        # For GIF: use filename without extension
        return path.stem
    else:
        return "unknown"


def _create_comparison_from_frames(frames1, frames2, output_filename, reverse_animation=False):
    """
    Create a comparison GIF by stitching frames vertically.
    
    Args:
        frames1: List of frame paths for first run
        frames2: List of frame paths for second run
        output_filename: Name for output GIF
        reverse_animation: If True, reverse frame order for forward-in-time animation
    
    Returns:
        Path: Path to created GIF
    """
    output_dir_base = Path("output") / "comparisons"
    output_dir_frames = output_dir_base / "frames"
    output_dir_gifs = output_dir_base / "gifs"
    
    # Create output directories
    output_dir_frames.mkdir(parents=True, exist_ok=True)
    output_dir_gifs.mkdir(parents=True, exist_ok=True)
    
    # Use the smaller number of frames
    num_frames = min(len(frames1), len(frames2))
    if len(frames1) != len(frames2):
        print(f"Warning: Frame counts differ. Using the smaller count: {num_frames} frames.")
    
    print(f"Stitching {num_frames} frames...")
    
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
        frame_name = f"frame_{i:03d}.png"
        output_path = output_dir_frames / frame_name
        stitched_image.save(output_path)
        stitched_frame_paths.append(output_path)
        
        if (i + 1) % 10 == 0:
            print(f"  ... stitched {i + 1}/{num_frames} frames")
    
    print("\nStitching complete!")
    
    # Reverse frame order if requested
    if reverse_animation:
        print("  - Reversing frame order for forward-in-time animation.")
        stitched_frame_paths.reverse()
    
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
    
    return final_gif_path


def create_comparison_gif():
    """
    Generates a GIF comparing two model runs by stacking their frames vertically.
    Uses paths from config file (legacy function for backwards compatibility).
    """
    if not config.enable_comparison_gif:
        print("Comparison GIF creation is disabled in config.py.")
        return

    print(f"\n{'='*60}")
    print("CREATING COMPARISON GIF (from config)")
    print(f"{'='*60}")

    # Define source directories from config
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
    
    # Reverse frame order if requested
    if config.reverse_animation:
        print("  - Reversing frame order for forward-in-time animation.")
        stitched_frame_paths.reverse()
    
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