# models/isostatic_model.py

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

def run_isostatic_model(create_animation=False):
    """
    Isostatic model: X from vectors, Z from vectors with isostatic compensation.
    
    Physics: When rock is exhumed (dz > 0), some becomes topography and some
    is compensated by isostatic uplift of underlying crust.
    
    Surface elevation change = rock_uplift - erosion + isostatic_response
    
    For local Airy isostasy:
    isostatic_uplift = (ρ_crust / ρ_mantle) * material_removed
    
    Net topography = rock_uplift * (1 - ρ_crust/ρ_mantle)
    Net topography ≈ rock_uplift * 0.15 to 0.3 (depending on densities)
    """
    # Load modern topography
    topo_file = Path(getattr(config, 'modern_topo_file', "data/Topo/topo_04.dat"))
    x_modern, z_modern = load_topography(topo_file)
    
    print(f"\n{'='*60}")
    print("ISOSTATIC MODEL: Vector-based with isostatic compensation")
    print(f"{'='*60}")
    print(f"Loaded modern topography from {topo_file}")
    print(f"  X range: {x_modern.min():.2f} to {x_modern.max():.2f} km")
    print(f"  Z range: {z_modern.min():.2f} to {z_modern.max():.2f} km")
    
    # Get parameters from config
    rho_crust = getattr(config, 'rho_crust', 2700)  # kg/m³
    rho_mantle = getattr(config, 'rho_mantle', 3300)  # kg/m³
    z_initial = getattr(config, 'exp_z_initial', 0.0)
    
    # Calculate isostatic efficiency: fraction of rock uplift that becomes topography
    # Surface elevation = rock_displacement * (1 - ρ_crust/ρ_mantle)
    isostatic_efficiency = 1 - (rho_crust / rho_mantle)
    
    print(f"\nModel Parameters:")
    print(f"  Crustal density: {rho_crust} kg/m³")
    print(f"  Mantle density: {rho_mantle} kg/m³")
    print(f"  Isostatic efficiency: {isostatic_efficiency:.3f}")
    print(f"  (Only {isostatic_efficiency*100:.1f}% of rock uplift becomes topographic relief)")
    print(f"  Target elevation at 27 Ma: {z_initial} km")
    
    # Vector files and durations
    vector_files = {
        "v_00.dat": 5,
        "v_01.dat": 4,
        "v_02.dat": 11,
        "v_03.dat": 7,
    }
    
    total_time = sum(vector_files.values())
    
    # Pre-compute total surface elevation change from isostatic model
    print(f"\nPre-computing total topographic change with isostasy...")
    total_topo_change = np.zeros_like(x_modern)
    
    for fname, duration in vector_files.items():
        vector_file = Path("data/Vectors") / fname
        vec_x, dx, dz = load_vectors(vector_file)
        _, interp_dz = interpolate_vectors(x_modern, vec_x, dx, dz)
        
        # Surface elevation change = rock_displacement * isostatic_efficiency
        topo_change = isostatic_efficiency * interp_dz
        total_topo_change += topo_change
        
        print(f"  {fname}: rock dz = {interp_dz.min():.2f} to {interp_dz.max():.2f}, " +
              f"topo change = {topo_change.min():.2f} to {topo_change.max():.2f}")
    
    print(f"  Total topographic change: {total_topo_change.min():.2f} to {total_topo_change.max():.2f} km")
    
    # Initialize
    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()
    original_x_positions = x_modern.copy()
    cumulative_topo_change = np.zeros_like(x_modern)
    
    if create_animation:
        frames_dir = Path("frames_output_isostatic")
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
        plt.title(f"Isostatic Model: {time_elapsed} Ma (Modern)")
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
            print(f"  Vector rock dz range: {dz.min():.2f} to {dz.max():.2f}")
            
            dx_dt = -dx / duration
            dz_dt = dz / duration  # Rock displacement rate
            
            for year in range(duration):
                time_elapsed += 1
                print(f"  Frame {time_elapsed}: {time_elapsed} Ma")
                
                # Step 1: Translate X
                interp_dx_dt, interp_dz_dt = interpolate_vectors(current_x, vec_x, dx_dt, dz_dt)
                current_x += interp_dx_dt
                
                # Step 2: Fix right boundary
                x_shift = current_x.max() - x_right_fixed
                current_x -= x_shift
                
                # Step 3: Update cumulative topographic change
                f_cumsum = interp1d(current_x, cumulative_topo_change, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                cumulative_topo_change = f_cumsum(current_x)
                
                # Add this timestep's topographic change (with isostasy)
                topo_change_dt = isostatic_efficiency * interp_dz_dt
                cumulative_topo_change += topo_change_dt
                
                print(f"    Rock dz_dt: {interp_dz_dt.min():.4f} to {interp_dz_dt.max():.4f}")
                print(f"    Topo change: {topo_change_dt.min():.4f} to {topo_change_dt.max():.4f}")
                
                # Step 4: Remesh
                x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
                
                f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                original_x_positions = f_orig_x(x_remeshed)
                
                f_cumsum_remesh = interp1d(current_x, cumulative_topo_change, kind='linear',
                                          bounds_error=False, fill_value='extrapolate')
                cumulative_topo_change_remeshed = f_cumsum_remesh(x_remeshed)
                
                # Step 5: Calculate Z using progress toward flat baseline
                # Get modern z and total_topo_change for original positions
                f_z_modern = interp1d(x_modern, z_modern, kind='linear',
                                     bounds_error=False, fill_value='extrapolate')
                z_modern_at_points = f_z_modern(original_x_positions)
                
                f_total_change = interp1d(x_modern, total_topo_change, kind='linear',
                                         bounds_error=False, fill_value='extrapolate')
                total_change_at_points = f_total_change(original_x_positions)
                
                # Progress based on cumulative topographic change
                # Use time-based blending to ensure flat at 27 Ma
                time_progress = time_elapsed / total_time
                
                spatial_progress = np.zeros_like(total_change_at_points)
                mask = np.abs(total_change_at_points) > 0.01
                spatial_progress[mask] = cumulative_topo_change_remeshed[mask] / total_change_at_points[mask]
                spatial_progress = np.clip(spatial_progress, 0, 1)
                
                # Blend time and spatial (70% time, 30% spatial)
                blend_factor = getattr(config, 'hybrid_blend_factor', 0.7)
                progress = blend_factor * time_progress + (1 - blend_factor) * spatial_progress
                progress = np.clip(progress, 0, 1)
                
                # Interpolate to flat baseline
                z_remeshed = z_modern_at_points + progress * (z_initial - z_modern_at_points)
                
                # Apply smoothing to prevent artifacts from interpolation
                # Use a simple moving average filter
                window_size = 5
                if len(z_remeshed) > window_size:
                    kernel = np.ones(window_size) / window_size
                    z_remeshed = np.convolve(z_remeshed, kernel, mode='same')
                
                print(f"    Progress: min={progress.min():.3f}, max={progress.max():.3f}, mean={progress.mean():.3f}")
                print(f"    Z range: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")
                
                # Update state
                current_x = x_remeshed
                current_z = z_remeshed
                cumulative_topo_change = cumulative_topo_change_remeshed
                
                # Plot
                plt.figure(figsize=(10, 6))
                plt.plot(x_remeshed, z_remeshed, color='b', linewidth=1.5)
                plt.title(f"Isostatic Model: {time_elapsed} Ma (η={isostatic_efficiency:.2f})")
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
        fps = getattr(config, 'animation_fps', 2)
        imageio.mimsave('topo_evolution_isostatic.gif', images, fps=fps)
        print(f"Animation saved as topo_evolution_isostatic.gif ({fps} fps)")
    
    print("\nIsostatic model finished.")
    print(f"Final state at {time_elapsed} Ma (should be ~flat at {z_initial} km)")

if __name__ == '__main__':
    run_isostatic_model(create_animation=True)