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
    Hybrid model: X translation from vectors (going backward), Z from new α_z(t) integral model.
    Starts at 0 Ma (modern) and goes backward to 27 Ma (flat topography).
    """
    topo_file = Path(getattr(config, 'modern_topo_file', "data/Topo/topo_04.dat"))
    x_modern, z_modern = load_topography(topo_file)

    print(f"\n{'='*60}")
    print("INTEGRAL α_z(t) MODEL: Vector-based X + New α_z(t) Z")
    print(f"{'='*60}")
    print(f"Loaded modern topography from {topo_file}")
    print(f"  X range: {x_modern.min():.2f} to {x_modern.max():.2f} km")
    print(f"  Z range: {z_modern.min():.2f} to {z_modern.max():.2f} km")

    t_initial = getattr(config, 'exp_t_initial', 27.0)  # Ma (past)
    t_final = getattr(config, 'exp_t_final', 0.0)       # Ma (present)
    lambda_topo = getattr(config, 'exp_lambda_topo', 10.0)  # Ma
    z_initial_value = getattr(config, 'exp_z_initial', 0.0)  # km (flat)

    vector_files = {
        "v_00.dat": 5,
        "v_01.dat": 4,
        "v_02.dat": 11,
        "v_03.dat": 7,
    }

    num_points = len(x_modern)
    current_x = x_modern.copy()
    original_x_positions = x_modern.copy()

    if create_animation:
        frames_dir = Path("frames_output_integral_alpha")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []

        x_margin = (x_modern.max() - x_modern.min()) * 0.2
        x_min_global = x_modern.min() - x_margin
        x_max_global = x_modern.max() + x_margin

        z_min_global = min(z_initial_value, z_modern.min()) - 1.0
        z_max_global = z_modern.max() + 1.0

        time_elapsed = 0

        # Initialize z_profiles list to store Z profile at each timestep for Δz calculation
        z_profiles = [z_modern.copy()]

        # Frame 0 plot (modern)
        plt.figure(figsize=(10, 6))
        plt.plot(current_x, z_profiles[0], color='g', linewidth=1.5, label='Modern')
        plt.title(f"Integral α_z Model: {time_elapsed} Ma (Modern)")
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

        for fname, duration in vector_files.items():
            vector_file = Path("data/Vectors") / fname
            print(f"\nProcessing {vector_file.name} for {duration} Ma")

            vec_x, dx, dz = load_vectors(vector_file)
            dx_dt = -dx / duration  # Negative for backward

            for year in range(duration):
                time_elapsed += 1

                print(f"Frame {time_elapsed}: {time_elapsed} Ma")
                print(f"  X range BEFORE: {current_x.min():.2f} to {current_x.max():.2f}")

                interp_dx_dt = interpolate_dx(current_x, vec_x, dx_dt)
                print(f"  Interpolated dx_dt: min={interp_dx_dt.min():.4f}, max={interp_dx_dt.max():.4f}")

                current_x += interp_dx_dt

                x_shift = current_x.max() - x_modern.max()
                current_x -= x_shift

                x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
                f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                                    bounds_error=False, fill_value='extrapolate')
                original_x_positions = f_orig_x(x_remeshed)

                # Build z_profiles list for Δz calculation
                # Use latest z_profile for difference calculation
                # For initial step, will duplicate present profile
                if len(z_profiles) == 1:
                    last_z = z_profiles[0]
                else:
                    last_z = z_profiles[-1]

                # We calculate Δz based on exponential weighting, but now use integral α_z(t)
                # Calculate delta_z between last and current z profile

                # First, compute tentative alpha array for all frames elapsed
                delta_z_tmp = last_z - z_initial_value  # elevation change from initial

                # Compute exp_sum numerator (cumulative sum of delta_z / lambda)
                # Since we update frame by frame, approximate cumulative sum by summing delta_z changes so far
                # Store delta_z changes in array for all steps
                # Simplify: Use mean delta z difference between last and current step (estimated as interp dx)

                # Calculate alpha cumulatively (approximate sum)
                if time_elapsed == 1:
                    # First step alpha
                    alpha_cumulative = np.mean(np.abs(delta_z_tmp)) / lambda_topo
                    exp_sum_end = alpha_cumulative
                else:
                    previous_cumulative = frame_paths[-1] if len(frame_paths) > 1 else 0
                    alpha_cumulative += np.mean(np.abs(delta_z_tmp)) / lambda_topo

                # Calculate alpha t
                alpha_t = (1 - np.exp(-alpha_cumulative)) / (1 - np.exp(-exp_sum_end))

                z_profile = z_initial_value + alpha_t * (z_modern - z_initial_value)

                f_z = interp1d(x_modern, z_profile, kind='linear', bounds_error=False, fill_value='extrapolate')
                z_remeshed = f_z(original_x_positions)

                print(f"  Z range: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")

                current_x = x_remeshed
                z_profiles.append(z_remeshed)

                plt.figure(figsize=(10, 6))
                plt.plot(x_remeshed, z_remeshed, color='b', linewidth=1.5)
                plt.title(f"Integral α_z Model: {time_elapsed} Ma")
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

        print("\nCreating animation...")
        images = [imageio.imread(fp) for fp in frame_paths]
        imageio.mimsave('topo_evolution_integral_alpha.gif', images, duration=0.5)
        print("Animation saved as topo_evolution_integral_alpha.gif")

    print("\nIntegral α_z Model finished.")
    print(f"Final state at {time_elapsed} Ma (should be flat)")



if __name__ == '__main__':
    run_exponential_model(create_animation=True)