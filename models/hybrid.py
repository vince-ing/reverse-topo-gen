# models/hybrid_model.py

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from scipy.interpolate import interp1d
import config

def load_topography(filepath):
    """Loads topography data from a file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    # Skip header
    data = [list(map(float, line.split())) for line in lines[1:]]
    data = np.array(data)
    return data[:, 0], data[:, 1]

def load_vectors(filepath):
    """Loads vector data from a file using pandas to handle duplicates."""
    data = pd.read_csv(filepath, sep=r'\s+', header=None, usecols=[3, 4, 5, 6], 
                       names=['x1', 'z1', 'x2', 'z2'], comment='B')
    data = data.drop_duplicates(subset='x1', keep='first')
    
    x = data['x1'].values
    dx = data['x2'].values - data['x1'].values
    dz = data['z2'].values - data['z1'].values
    return x, dx, dz

def interpolate_vectors(topo_x, vector_x, dx, dz):
    """Interpolates dx and dz to the topography points with bounds checking."""
    f_dx = interp1d(vector_x, dx, kind='linear', bounds_error=False, fill_value=(dx[0], dx[-1]))
    f_dz = interp1d(vector_x, dz, kind='linear', bounds_error=False, fill_value=(dz[0], dz[-1]))
    interp_dx = f_dx(topo_x)
    interp_dz = f_dz(topo_x)
    
    # Clip extreme values as a safety measure
    interp_dx = np.clip(interp_dx, -100, 100)
    interp_dz = np.clip(interp_dz, -100, 100)
    
    return interp_dx, interp_dz

def run_hybrid_model(create_animation=False):
    """
    Hybrid model: X from vectors, Z decay uses vector spatial pattern but scaled to reach flat at 27 Ma.
    Combines the spatial heterogeneity of vectors with the guaranteed boundary condition of exponential.
    """
    # Load modern topography (present day - 0 Ma)
    topo_file = Path(getattr(config, 'modern_topo_file', "data/Topo/topo_04.dat"))
    x_modern, z_modern = load_topography(topo_file)
    
    print(f"\n{'='*60}")
    print("HYBRID MODEL: Vector X + Vector-weighted exponential Z")
    print(f"{'='*60}")
    print(f"Loaded modern topography from {topo_file}")
    print(f"  X range: {x_modern.min():.2f} to {x_modern.max():.2f} km")
    print(f"  Z range: {z_modern.min():.2f} to {z_modern.max():.2f} km")
    
    # Get parameters from config
    z_initial = getattr(config, 'exp_z_initial', 0.0)
    erosion_efficiency = getattr(config, 'erosion_efficiency', 0.7)
    blend_factor = getattr(config, 'hybrid_blend_factor', 0.7)
    
    # Vector files and durations (going backward in time)
    vector_files = {
        "v_00.dat": 5,
        "v_01.dat": 4,
        "v_02.dat": 11,
        "v_03.dat": 7,
    }
    
    total_time = sum(vector_files.values())
    
    print(f"\nModel Parameters:")
    print(f"  Time: 0 Ma (modern) → {total_time} Ma (flat)")
    print(f"  Target elevation at {total_time} Ma: {z_initial} km")
    print(f"  Erosion efficiency: {erosion_efficiency} (controls spatial pattern)")
    print(f"  Blend factor: {blend_factor} (time vs spatial weighting)")
    
    # Pre-compute total cumulative dz weighted by erosion efficiency
    print(f"\nPre-computing total weighted dz for normalization...")
    total_weighted_dz = np.zeros_like(x_modern)
    
    for fname, duration in vector_files.items():
        vector_file = Path("data/Vectors") / fname
        vec_x, dx, dz = load_vectors(vector_file)
        _, interp_dz = interpolate_vectors(x_modern, vec_x, dx, dz)
        
        # Accumulate weighted dz
        total_weighted_dz += erosion_efficiency * np.abs(interp_dz)
        print(f"  {fname}: dz range = {interp_dz.min():.2f} to {interp_dz.max():.2f}")
    
    print(f"  Total weighted dz: {total_weighted_dz.min():.2f} to {total_weighted_dz.max():.2f}")
    
    # Calculate normalization factor for each point
    # We want: z_modern - total_change = z_initial
    # So: total_change = z_modern - z_initial
    # Normalization: actual_change = (z_modern - z_initial) * (cumulative_dz / total_weighted_dz)
    z_range = z_modern - z_initial
    
    # Initialize
    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()
    original_x_positions = x_modern.copy()
    cumulative_weighted_dz = np.zeros_like(x_modern)
    
    if create_animation:
        frames_dir = Path("frames_output_hybrid")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []
        
        # Fixed plot limits
        x_margin = (x_modern.max() - x_modern.min()) * 0.2
        x_min_global = x_modern.min() - x_margin
        x_max_global = x_modern.max() + x_margin
        z_min_global = min(z_initial, z_modern.min()) - 1.0
        z_max_global = z_modern.max() + 1.0
        
        print(f"\nCreating animation...")
        print(f"  X-axis limits: {x_min_global:.2f} to {x_max_global:.2f} km")
        print(f"  Y-axis limits: {z_min_global:.2f} to {z_max_global:.2f} km")
        
        # Frame 0: Modern topography
        time_elapsed = 0
        x_right_fixed = x_modern.max()
        
        plt.figure(figsize=(10, 6))
        plt.plot(current_x, current_z, color='g', linewidth=1.5, label='Modern')
        plt.title(f"Hybrid Model: {time_elapsed} Ma (Modern)")
        plt.xlabel("X (km)")
        plt.ylabel("Z (km)")
        plt.xlim(x_min_global, x_max_global)
        plt.ylim(z_min_global, z_max_global)
        plt.gca().set_aspect(config.vertical_exaggeration)
        plt.grid(True, alpha=0.3)
        plt.legend()
        frame_path = frames_dir / f"frame_{time_elapsed:03d}.png"
        plt.savefig(frame_path, dpi=100)
        plt.close()
        frame_paths.append(frame_path)
        
        # Process vector files
        for fname, duration in vector_files.items():
            vector_file = Path("data/Vectors") / fname
            print(f"\nProcessing {vector_file.name} for {duration} Ma")
            
            vec_x, dx, dz = load_vectors(vector_file)
            print(f"  Vector dz range: {dz.min():.2f} to {dz.max():.2f}")
            
            dx_dt = -dx / duration
            dz_dt = dz / duration
            
            for year in range(duration):
                time_elapsed += 1
                print(f"  Frame {time_elapsed}: {time_elapsed} Ma")
                
                # Step 1: Translate X
                interp_dx_dt, interp_dz_dt = interpolate_vectors(current_x, vec_x, dx_dt, dz_dt)
                current_x += interp_dx_dt
                
                # Step 2: Fix right boundary
                x_shift = current_x.max() - x_right_fixed
                current_x -= x_shift
                
                # Step 3: Update cumulative weighted dz
                f_cumsum = interp1d(current_x, cumulative_weighted_dz, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                cumulative_weighted_dz = f_cumsum(current_x)
                cumulative_weighted_dz += erosion_efficiency * np.abs(interp_dz_dt)
                
                # Step 4: Remesh
                x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
                
                f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                original_x_positions = f_orig_x(x_remeshed)
                
                f_cumsum_remesh = interp1d(current_x, cumulative_weighted_dz, kind='linear',
                                          bounds_error=False, fill_value='extrapolate')
                cumulative_weighted_dz_remeshed = f_cumsum_remesh(x_remeshed)
                
                # Step 5: Calculate Z using hybrid approach
                # Get modern z and total_weighted_dz for original positions
                f_z_modern = interp1d(x_modern, z_modern, kind='linear',
                                     bounds_error=False, fill_value='extrapolate')
                z_modern_at_points = f_z_modern(original_x_positions)
                
                f_total_dz = interp1d(x_modern, total_weighted_dz, kind='linear',
                                     bounds_error=False, fill_value='extrapolate')
                total_dz_at_points = f_total_dz(original_x_positions)
                
                # Progress: how much of the total decay has occurred (0 to 1)
                # Use time-based progress as baseline, weighted by spatial dz pattern
                time_progress = time_elapsed / total_time  # 0 to 1 based purely on time
                
                # Spatial weighting: areas with more dz deviate from time_progress
                spatial_weight = np.ones_like(total_dz_at_points)
                mask = total_dz_at_points > 0.01
                if mask.any():
                    spatial_weight[mask] = cumulative_weighted_dz_remeshed[mask] / total_dz_at_points[mask]
                    spatial_weight = np.clip(spatial_weight, 0, 2)  # Allow some spatial variation
                
                # Blend: mostly time-based, but modulated by spatial pattern
                # This ensures all points reach 1.0 at t=27 Ma, but with spatial heterogeneity
                progress = blend_factor * time_progress + (1 - blend_factor) * spatial_weight * time_progress
                progress = np.clip(progress, 0, 1)
                
                # Interpolate: z = z_modern + progress * (z_initial - z_modern)
                z_remeshed = z_modern_at_points + progress * (z_initial - z_modern_at_points)
                
                print(f"    Progress: min={progress.min():.3f}, max={progress.max():.3f}, mean={progress.mean():.3f}")
                print(f"    Z range: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")
                
                # Update state
                current_x = x_remeshed
                current_z = z_remeshed
                cumulative_weighted_dz = cumulative_weighted_dz_remeshed
                
                # Plot
                plt.figure(figsize=(10, 6))
                plt.plot(x_remeshed, z_remeshed, color='b', linewidth=1.5)
                plt.title(f"Hybrid Model: {time_elapsed} Ma (ε={erosion_efficiency})")
                plt.xlabel("X (km)")
                plt.ylabel("Z (km)")
                plt.xlim(x_min_global, x_max_global)
                plt.ylim(z_min_global, z_max_global)
                plt.gca().set_aspect(config.vertical_exaggeration)
                plt.grid(True, alpha=0.3)
                
                frame_path = frames_dir / f"frame_{time_elapsed:03d}.png"
                plt.savefig(frame_path, dpi=100)
                plt.close()
                frame_paths.append(frame_path)
        
        # Create GIF
        print("\nCreating animation...")
        images = [imageio.imread(fp) for fp in frame_paths]
        fps = getattr(config, 'animation_fps', 2)  # Frames per second
        imageio.mimsave('topo_evolution_hybrid.gif', images, fps=fps)
        print(f"Animation saved as topo_evolution_hybrid.gif ({fps} fps)")
    
    print("\nHybrid model finished.")
    print(f"Final state at {time_elapsed} Ma should be flat at {z_initial} km")

if __name__ == '__main__':
    run_hybrid_model(create_animation=True)