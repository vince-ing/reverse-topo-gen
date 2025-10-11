# models/exponential.py

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
    dx = data['x2'].values - data['x1'].values  # Displacement from past to present
    dz = data['z2'].values - data['z1'].values
    return x, dx, dz

def interpolate_dx(topo_x, vector_x, dx):
    """Interpolates dx to the topography points with bounds checking."""
    f_dx = interp1d(vector_x, dx, kind='linear', bounds_error=False, fill_value=(dx[0], dx[-1]))
    interp_dx = f_dx(topo_x)
    # Clip extreme values as a safety measure
    interp_dx = np.clip(interp_dx, -100, 100)  # Maximum 100 km displacement per Ma
    return interp_dx

def alpha_function(t, t_initial, t_final, lambda_topo):
    """
    Exponential interpolation function.
    
    Args:
        t: Current time (Ma)
        t_initial: Start time (e.g., 27 Ma - past)
        t_final: End time (e.g., 0 Ma - present)
        lambda_topo: Time constant controlling growth rate
    
    Returns:
        alpha: Interpolation factor between 0 (at t_initial) and 1 (at t_final)
    """
    numerator = 1 - np.exp(-(t - t_initial) / lambda_topo)
    denominator = 1 - np.exp(-(t_final - t_initial) / lambda_topo)
    return numerator / denominator

def run_exponential_model(create_animation=False):
    """
    Hybrid model: X translation from vectors (going backward), Z from exponential equation.
    Starts at 0 Ma (modern) and goes backward to 27 Ma (flat topography).
    """
    # Load modern topography (present day - 0 Ma)
    topo_file = Path(getattr(config, 'modern_topo_file', "data/Topo/topo_04.dat"))
    x_modern, z_modern = load_topography(topo_file)
    
    print(f"\n{'='*60}")
    print("EXPONENTIAL MODEL: Vector-based X + Exponential Z")
    print(f"{'='*60}")
    print(f"Loaded modern topography from {topo_file}")
    print(f"  X range: {x_modern.min():.2f} to {x_modern.max():.2f} km")
    print(f"  Z range: {z_modern.min():.2f} to {z_modern.max():.2f} km")
    
    # Get parameters from config
    t_initial = getattr(config, 'exp_t_initial', 27.0)  # Ma (past)
    t_final = getattr(config, 'exp_t_final', 0.0)       # Ma (present)
    lambda_topo = getattr(config, 'exp_lambda_topo', 10.0)  # Ma
    z_initial_value = getattr(config, 'exp_z_initial', 0.0)  # km (flat at 27 Ma)
    
    # Vector files and durations (going backward in time)
    vector_files = {
        "v_00.dat": 5,   # 0-5 Ma
        "v_01.dat": 4,   # 5-9 Ma
        "v_02.dat": 11,  # 9-20 Ma
        "v_03.dat": 7,   # 20-27 Ma
    }
    
    print(f"\nModel Parameters:")
    print(f"  Time: 0 Ma (modern) → 27 Ma (past)")
    print(f"  Lambda (time constant): {lambda_topo} Ma")
    print(f"  Initial elevation at 27 Ma: {z_initial_value} km")
    
    # Initialize with modern topography
    num_points = len(x_modern)
    current_x = x_modern.copy()
    
    # Track which original X position each point came from (for Z lookup)
    original_x_positions = x_modern.copy()
    
    if create_animation:
        frames_dir = Path("frames_output_exponential")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []
        
        # Calculate fixed plot limits
        x_margin = (x_modern.max() - x_modern.min()) * 0.2
        x_min_global = x_modern.min() - x_margin
        x_max_global = x_modern.max() + x_margin
        
        # Z limits based on modern and flat topography
        z_min_global = min(z_initial_value, z_modern.min()) - 1.0
        z_max_global = z_modern.max() + 1.0
        
        print(f"\nCreating animation...")
        print(f"  X-axis limits: {x_min_global:.2f} to {x_max_global:.2f} km")
        print(f"  Y-axis limits: {z_min_global:.2f} to {z_max_global:.2f} km")
        
        # Frame 0: Modern topography (0 Ma)
        time_elapsed = 0
        t_current = t_final  # Start at 0 Ma
        alpha_t = alpha_function(t_current, t_initial, t_final, lambda_topo)  # Should be 1.0
        z_current = z_initial_value + alpha_t * (z_modern - z_initial_value)
        
        # Track the right boundary position (fixed)
        x_right_fixed = x_modern.max()
        
        plt.figure(figsize=(10, 6))
        plt.plot(current_x, z_current, color='g', linewidth=1.5, label='Modern')
        plt.title(f"Exponential Model: {time_elapsed} Ma (Modern)")
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
            
            # Going backward: reverse the displacement
            dx_dt = -dx / duration  # Negative to go backward in time
            
            for year in range(duration):
                time_elapsed += 1
                t_current = time_elapsed  # Time in Ma from present
                
                print(f"  Frame {time_elapsed}: {time_elapsed} Ma")
                print(f"    X range BEFORE: {current_x.min():.2f} to {current_x.max():.2f}")
                
                # Step 1: Translate X backward using vectors (differential motion)
                interp_dx_dt = interpolate_dx(current_x, vec_x, dx_dt)
                print(f"    Interpolated dx_dt: min={interp_dx_dt.min():.4f}, max={interp_dx_dt.max():.4f}, mean={interp_dx_dt.mean():.4f}")
                
                current_x += interp_dx_dt  # Add because dx_dt is already negative
                print(f"    X range after translation: {current_x.min():.2f} to {current_x.max():.2f}")
                
                # Step 2: Fix right boundary by shifting everything
                x_shift = current_x.max() - x_right_fixed
                current_x -= x_shift
                print(f"    Shifted by {x_shift:.4f} to fix right boundary")
                print(f"    X range after fixing boundary: {current_x.min():.2f} to {current_x.max():.2f}")
                
                # Step 3: Remesh to maintain even spacing
                x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
                
                # Interpolate the original X positions onto the remeshed grid
                # This tracks which part of the original topography each point represents
                f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                original_x_positions = f_orig_x(x_remeshed)
                
                # Step 4: Calculate Z using exponential function
                t_for_alpha = t_initial - t_current  # At t_current=0: gives 27; at t_current=27: gives 0
                alpha_t = alpha_function(t_for_alpha, t_final, t_initial, lambda_topo)
                print(f"    Alpha value: {alpha_t:.4f} (1=modern, 0=flat)")
                
                # Now alpha_t goes from ~1 (at t_current=0 Ma) to 0 (at t_current=27 Ma)
                z_profile = z_initial_value + alpha_t * (z_modern - z_initial_value)
                
                # Step 5: Interpolate Z values based on where each point came from originally
                # Use original_x_positions to look up the appropriate Z from the modern topography
                f_z = interp1d(x_modern, z_profile, kind='linear', 
                              bounds_error=False, fill_value='extrapolate')
                z_remeshed = f_z(original_x_positions)
                print(f"    Z range: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")
                print(f"    Original X range being sampled: {original_x_positions.min():.2f} to {original_x_positions.max():.2f}")
                
                # Update current_x to the remeshed positions
                current_x = x_remeshed
                
                # Plot frame
                plt.figure(figsize=(10, 6))
                plt.plot(x_remeshed, z_remeshed, color='b', linewidth=1.5)
                plt.title(f"Exponential Model: {time_elapsed} Ma (λ={lambda_topo} Ma)")
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
        imageio.mimsave('topo_evolution_exponential.gif', images, duration=0.5)
        print(f"Animation saved as topo_evolution_exponential.gif")
    
    print("\nExponential model finished.")
    print(f"Final state at {time_elapsed} Ma (should be flat)")

if __name__ == '__main__':
    run_exponential_model(create_animation=True)