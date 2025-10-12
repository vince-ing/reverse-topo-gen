# models/vector_z_model.py

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

def alpha_z_function(cumsum_dz_current, cumsum_dz_total, lambda_z):
    """
    Vector-based exponential interpolation function using cumulative dz.
    
    Args:
        cumsum_dz_current: Cumulative sum of dz from time 0 to current time t
        cumsum_dz_total: Total cumulative sum of dz from time 0 to end
        lambda_z: Time constant controlling growth rate
    
    Returns:
        alpha_z: Interpolation factor between 0 and 1
    """
    numerator = 1 - np.exp(-cumsum_dz_current / lambda_z)
    denominator = 1 - np.exp(-cumsum_dz_total / lambda_z)
    return numerator / denominator

def run_vector_z_model(create_animation=False):
    """
    Vector Z model: X translation from vectors, Z from vectors with erosion efficiency.
    Starts at 0 Ma (modern) and goes backward to 27 Ma.
    Uses simple erosion efficiency instead of complex exponential scaling.
    """
    # Load modern topography (present day - 0 Ma)
    topo_file = Path(getattr(config, 'modern_topo_file', "data/Topo/topo_04.dat"))
    x_modern, z_modern = load_topography(topo_file)
    
    print(f"\n{'='*60}")
    print("VECTOR Z MODEL: Vector-based X + Vector-based Z with erosion efficiency")
    print(f"{'='*60}")
    print(f"Loaded modern topography from {topo_file}")
    print(f"  X range: {x_modern.min():.2f} to {x_modern.max():.2f} km")
    print(f"  Z range: {z_modern.min():.2f} to {z_modern.max():.2f} km")
    
    # Get parameters from config
    erosion_efficiency = getattr(config, 'erosion_efficiency', 0.7)  # Fraction of rock uplift that becomes topography
    
    # Vector files and durations (going backward in time)
    vector_files = {
        "v_00.dat": 5,   # 0-5 Ma
        "v_01.dat": 4,   # 5-9 Ma
        "v_02.dat": 11,  # 9-20 Ma
        "v_03.dat": 7,   # 20-27 Ma
    }
    
    print(f"\nModel Parameters:")
    print(f"  Time: 0 Ma (modern) → 27 Ma (past)")
    print(f"  Erosion efficiency: {erosion_efficiency}")
    print(f"  (Fraction of rock uplift that becomes topography)")
    
    # Initialize with modern topography
    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()
    original_x_positions = x_modern.copy()
    
    if create_animation:
        frames_dir = Path("frames_output_vector_z")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []
        
        # Calculate fixed plot limits
        x_margin = (x_modern.max() - x_modern.min()) * 0.2
        x_min_global = x_modern.min() - x_margin
        x_max_global = x_modern.max() + x_margin
        
        # Z limits based on modern topography
        z_min_global = z_modern.min() - 1.0
        z_max_global = z_modern.max() + 1.0
        
        print(f"\nCreating animation...")
        print(f"  X-axis limits: {x_min_global:.2f} to {x_max_global:.2f} km")
        print(f"  Y-axis limits: {z_min_global:.2f} to {z_max_global:.2f} km")
        
        # Frame 0: Modern topography (0 Ma)
        time_elapsed = 0
        
        # Track the right boundary position (fixed)
        x_right_fixed = x_modern.max()
        
        plt.figure(figsize=(10, 6))
        plt.plot(current_x, current_z, color='g', linewidth=1.5, label='Modern')
        plt.title(f"Vector Z Model: {time_elapsed} Ma (Modern)")
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
        
        # Process vector files going backward in time
        for fname, duration in vector_files.items():
            vector_file = Path("data/Vectors") / fname
            print(f"\nProcessing {vector_file.name} for {duration} Ma")
            
            vec_x, dx, dz = load_vectors(vector_file)
            print(f"  Vector X range: {vec_x.min():.2f} to {vec_x.max():.2f}")
            print(f"  dx range: {dx.min():.2f} to {dx.max():.2f}")
            print(f"  dz range: {dz.min():.2f} to {dz.max():.2f}")
            print(f"  dz mean: {dz.mean():.2f}, median: {np.median(dz):.2f}")
            
            # Going backward: reverse the displacement
            dx_dt = -dx / duration
            dz_dt = dz / duration  # DON'T negate dz - we'll handle the sign in the update
            print(f"  dz_dt range: {dz_dt.min():.4f} to {dz_dt.max():.4f}, mean: {dz_dt.mean():.4f}")
            
            for year in range(duration):
                time_elapsed += 1
                
                print(f"  Frame {time_elapsed}: {time_elapsed} Ma")
                print(f"    X range BEFORE: {current_x.min():.2f} to {current_x.max():.2f}")
                print(f"    Z range BEFORE: {current_z.min():.2f} to {current_z.max():.2f}")
                
                # Step 1: Translate X and Z backward using vectors
                interp_dx_dt, interp_dz_dt = interpolate_vectors(current_x, vec_x, dx_dt, dz_dt)
                print(f"    Interpolated dx_dt: min={interp_dx_dt.min():.4f}, max={interp_dx_dt.max():.4f}, mean={interp_dx_dt.mean():.4f}")
                print(f"    Interpolated dz_dt: min={interp_dz_dt.min():.4f}, max={interp_dz_dt.max():.4f}, mean={interp_dz_dt.mean():.4f}")
                
                # Update X
                current_x += interp_dx_dt
                print(f"    X range after translation: {current_x.min():.2f} to {current_x.max():.2f}")
                
                # Update Z with erosion efficiency
                # Going backward in time: REMOVE topography that was built
                # dz is positive for uplift, so we SUBTRACT erosion_efficiency * dz to go backward
                z_change = -erosion_efficiency * interp_dz_dt
                print(f"    Z change being applied: min={z_change.min():.4f}, max={z_change.max():.4f}, mean={z_change.mean():.4f}")
                current_z += z_change
                print(f"    Z range after removing topography: {current_z.min():.2f} to {current_z.max():.2f}")
                
                # Step 2: Fix right boundary
                x_shift = current_x.max() - x_right_fixed
                current_x -= x_shift
                print(f"    X range after fixing boundary: {current_x.min():.2f} to {current_x.max():.2f}")
                
                # Step 3: Remesh to maintain even spacing
                x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
                
                # Interpolate Z and original_x_positions onto remeshed grid
                f_z = interp1d(current_x, current_z, kind='linear',
                              bounds_error=False, fill_value='extrapolate')
                z_remeshed = f_z(x_remeshed)
                
                f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                original_x_positions = f_orig_x(x_remeshed)
                
                print(f"    Z range after remeshing: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")
                print(f"    Original X range: {original_x_positions.min():.2f} to {original_x_positions.max():.2f}")
                
                # Update current state
                current_x = x_remeshed
                current_z = z_remeshed
                
                # Plot frame
                plt.figure(figsize=(10, 6))
                plt.plot(x_remeshed, z_remeshed, color='b', linewidth=1.5)
                plt.title(f"Vector Z Model: {time_elapsed} Ma (ε={erosion_efficiency})")
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
        imageio.mimsave('topo_evolution_vector_z.gif', images, duration=0.5)
        print(f"Animation saved as topo_evolution_vector_z.gif")
    
    print("\nVector Z model finished.")
    print(f"Final state at {time_elapsed} Ma (should be flat)")

if __name__ == '__main__':
    run_vector_z_model(create_animation=True)