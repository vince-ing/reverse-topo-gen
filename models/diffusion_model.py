# models/diffusion_model.py

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

def interpolate_vectors(topo_x, vector_x, dx):
    """Interpolates dx to the topography points with bounds checking."""
    f_dx = interp1d(vector_x, dx, kind='linear', bounds_error=False, fill_value=(dx[0], dx[-1]))
    interp_dx = f_dx(topo_x)
    interp_dx = np.clip(interp_dx, -100, 100)
    return interp_dx

def compute_laplacian(z, dx):
    """
    Compute the second derivative (Laplacian) of z with respect to x.
    Uses central differences: d²z/dx² ≈ (z[i+1] - 2*z[i] + z[i-1]) / dx²
    """
    laplacian = np.zeros_like(z)
    
    # Interior points: central difference
    for i in range(1, len(z) - 1):
        laplacian[i] = (z[i+1] - 2*z[i] + z[i-1]) / (dx**2)
    
    # Boundary conditions: zero flux (Neumann)
    laplacian[0] = laplacian[1]
    laplacian[-1] = laplacian[-2]
    
    return laplacian

def run_diffusion_model(create_animation=False):
    """
    Diffusion model: X from vectors, Z evolves by diffusion equation.
    
    The diffusion equation: dz/dt = κ * d²z/dx²
    
    Physics:
    - Areas with high curvature (peaks, valleys) erode/fill faster
    - Represents slope-dependent erosion processes
    - κ (kappa) is the diffusivity (m²/yr or km²/Ma)
    - Positive curvature (valleys) fill in
    - Negative curvature (peaks) erode
    """
    # Load modern topography
    topo_file = Path(getattr(config, 'modern_topo_file', "data/Topo/topo_04.dat"))
    x_modern, z_modern = load_topography(topo_file)
    
    print(f"\n{'='*60}")
    print("DIFFUSION MODEL: Vector X + Diffusion-based Z")
    print(f"{'='*60}")
    print(f"Loaded modern topography from {topo_file}")
    print(f"  X range: {x_modern.min():.2f} to {x_modern.max():.2f} km")
    print(f"  Z range: {z_modern.min():.2f} to {z_modern.max():.2f} km")
    
    # Get parameters from config
    kappa = getattr(config, 'diffusion_kappa', 0.1)  # km²/Ma
    z_initial = getattr(config, 'exp_z_initial', 0.0)
    target_final_relief = 0.5  # Target relief at 27 Ma (km)
    
    print(f"\nModel Parameters:")
    print(f"  Diffusivity κ: {kappa} km²/Ma")
    print(f"  Target elevation at 27 Ma: {z_initial} km")
    print(f"  Target relief at 27 Ma: ±{target_final_relief} km")
    
    # Vector files and durations
    vector_files = {
        "v_00.dat": 5,
        "v_01.dat": 4,
        "v_02.dat": 11,
        "v_03.dat": 7,
    }
    
    total_time = sum(vector_files.values())
    
    # Initialize
    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()
    original_x_positions = x_modern.copy()
    
    # Calculate mean spacing for diffusion calculation
    mean_dx = np.mean(np.diff(x_modern))
    
    if create_animation:
        frames_dir = Path("frames_output_diffusion")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []
        
        # Fixed plot limits
        x_margin = (x_modern.max() - x_modern.min()) * 0.2
        x_min_global = x_modern.min() - x_margin
        x_max_global = x_modern.max() + x_margin
        z_min_global = min(z_initial - target_final_relief, z_modern.min()) - 1.0
        z_max_global = z_modern.max() + 1.0
        
        print(f"\nCreating animation...")
        print(f"  X-axis limits: {x_min_global:.2f} to {x_max_global:.2f} km")
        print(f"  Y-axis limits: {z_min_global:.2f} to {z_max_global:.2f} km")
        print(f"  Mean point spacing: {mean_dx:.4f} km")
        
        # Frame 0: Modern topography
        time_elapsed = 0
        x_right_fixed = x_modern.max()
        
        plt.figure(figsize=(10, 6))
        plt.plot(current_x, current_z, color='g', linewidth=1.5, label='Modern')
        plt.title(f"Diffusion Model: {time_elapsed} Ma (Modern)")
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
            
            vec_x, dx, _ = load_vectors(vector_file)
            
            dx_dt = -dx / duration
            
            for year in range(duration):
                time_elapsed += 1
                print(f"  Frame {time_elapsed}: {time_elapsed} Ma")
                
                # Step 1: Translate X using vectors
                interp_dx_dt = interpolate_vectors(current_x, vec_x, dx_dt)
                current_x += interp_dx_dt
                
                # Step 2: Fix right boundary
                x_shift = current_x.max() - x_right_fixed
                current_x -= x_shift
                
                # Step 3: Interpolate Z onto current X positions (Lagrangian tracking)
                f_z = interp1d(current_x, current_z, kind='linear',
                              bounds_error=False, fill_value='extrapolate')
                
                # Step 4: Remesh to uniform spacing for diffusion calculation
                x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
                z_remeshed = f_z(x_remeshed)
                dx_remeshed = x_remeshed[1] - x_remeshed[0]
                
                # Step 5: Apply diffusion for this timestep
                # dz/dt = κ * d²z/dx²
                # Using explicit (forward Euler) timestepping
                dt = 1.0  # 1 Ma timestep
                
                # Compute Laplacian (second derivative)
                laplacian = compute_laplacian(z_remeshed, dx_remeshed)
                
                # Diffusion update (going backward in time, so we REVERSE diffusion)
                # This means we INCREASE curvature (sharpen features)
                dz_diffusion = -kappa * laplacian * dt
                z_remeshed += dz_diffusion
                
                # Step 6: Add decay toward baseline to ensure flat at 27 Ma
                # Linear decay: move toward z_initial based on time progress
                time_progress = time_elapsed / total_time
                decay_factor = getattr(config, 'diffusion_decay_factor', 0.05)  # How much to decay per Ma
                z_remeshed -= decay_factor * (z_remeshed - z_initial) * dt
                
                print(f"    Z range: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")
                print(f"    Diffusion dz: {dz_diffusion.min():.4f} to {dz_diffusion.max():.4f}")
                print(f"    Laplacian: {laplacian.min():.4f} to {laplacian.max():.4f}")
                
                # Update state
                current_x = x_remeshed
                current_z = z_remeshed
                
                # Track original positions
                f_orig_x = interp1d(x_remeshed, original_x_positions, kind='linear',
                                   bounds_error=False, fill_value='extrapolate')
                original_x_positions = f_orig_x(x_remeshed)
                
                # Plot
                plt.figure(figsize=(10, 6))
                plt.plot(x_remeshed, z_remeshed, color='b', linewidth=1.5)
                plt.title(f"Diffusion Model: {time_elapsed} Ma (κ={kappa} km²/Ma)")
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
        imageio.mimsave('topo_evolution_diffusion.gif', images, fps=fps)
        print(f"Animation saved as topo_evolution_diffusion.gif ({fps} fps)")
    
    print("\nDiffusion model finished.")
    print(f"Final state at {time_elapsed} Ma")

if __name__ == '__main__':
    run_diffusion_model(create_animation=True)