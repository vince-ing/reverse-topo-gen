import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from pathlib import Path
from scipy.interpolate import interp1d
from config import *


def load_topography(filepath):
    """Reads x,z coordinates of modern topography"""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    data = [list(map(float, line.split())) for line in lines[1:]]
    data = np.array(data)
    print(f"Loaded Topography Min/Max Z: {data[:,1].min()}, {data[:,1].max()}")
    return data[:, 0], data[:, 1]


def load_vectors(filepath):
    """
    Loads vector displacement data (x1,z1,x2,z2) with duplicates removed on x1.
    """
    import pandas as pd
    data = pd.read_csv(filepath, sep=r'\s+', header=None,
                       usecols=[3,4,5,6], names=['x1','z1','x2','z2'], comment='B')
    data = data.drop_duplicates(subset='x1', keep='first')
    return data


def run_alpha_z_evolution(create_animation=False):
    """Run palinspastic topography evolution incorporating cumulative lateral displacement and integral α_z(t) vertical weighting"""

    topo_file = Path(modern_topo_file)
    x_modern, z_modern = load_topography(topo_file)

    vector_files = [
        ("data/Vectors/v_03.dat",7),
        ("data/Vectors/v_02.dat",11),
        ("data/Vectors/v_01.dat",4),
        ("data/Vectors/v_00.dat",5),
    ]

    lambda_topo = exp_lambda_topo

    # Create an initial flat elevation profile array same length as topo (replace 0 by your chosen flat baseline if needed)
    z_initial = np.full_like(z_modern, exp_z_initial)

    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()

    times = [0]
    z_profiles = [current_z.copy()]

    frames_dir = Path("frames_alpha_z_evolution")
    frames_dir.mkdir(exist_ok=True)
    frame_paths = []

    x_min, x_max = x_modern.min(), x_modern.max()
    z_min, z_max = min(exp_z_initial, z_modern.min()) - 1, z_modern.max() + 1

    def save_frame(x_vals, z_vals, time_ma, idx):
        plt.figure(figsize=(12,6))
        plt.plot(x_vals, z_vals, color='b')
        plt.title(f"Topography Evolution Integral α_z(t) - {time_ma:.1f} Ma")
        plt.xlabel("Distance (km)")
        plt.ylabel("Elevation (km)")
        plt.xlim(x_min, x_max)
        plt.ylim(z_min, z_max)
        plt.grid(True)
        plt.tight_layout()
        frame_path = frames_dir / f"frame_{idx:03d}.png"
        plt.savefig(frame_path)
        plt.close()
        return frame_path

    frame_paths.append(save_frame(current_x, current_z, 0, 0))

    total_time = 0
    frame_idx = 1

    cumulative_integral = 0
    integral_end = None

    for vf, duration in vector_files:
        vector_data_df = load_vectors(vf)
        vec_x1 = vector_data_df['x1'].values
        vec_z1 = vector_data_df['z1'].values
        vec_x2 = vector_data_df['x2'].values
        vec_z2 = vector_data_df['z2'].values

        dx_total = vec_x2 - vec_x1
        dz_total = vec_z2 - vec_z1

        dx_per_year = dx_total / duration
        dz_per_year = dz_total / duration

        for year in range(duration):
            total_time += 1

            f_dx = interp1d(vec_x1, -dx_per_year, kind='linear', bounds_error=False, fill_value=( -dx_per_year[0], -dx_per_year[-1]))
            f_dz = interp1d(vec_x1, -dz_per_year, kind='linear', bounds_error=False, fill_value=( -dz_per_year[0], -dz_per_year[-1]))

            interp_dx = f_dx(current_x)
            interp_dz = f_dz(current_x)

            # Accumulate lateral and vertical displacement (no remeshing!)
            current_x = current_x + interp_dx
            current_z = current_z + interp_dz

            # Compute delta z for integral
            delta_z = z_profiles[-1] - current_z
            mean_abs_delta_z = np.mean(np.abs(delta_z))

            if integral_end is None:
                integral_end = mean_abs_delta_z / lambda_topo * sum(d for _, d in vector_files)

            cumulative_integral += mean_abs_delta_z / lambda_topo

            alpha_t = (1 - np.exp(-cumulative_integral)) / (1 - np.exp(-integral_end)) if integral_end != 0 else 0

            # Blend between initial flat and current elevation profiles
            z_interp = z_initial + alpha_t * (current_z - z_initial)

            # Save for next step computation
            z_profiles.append(z_interp.copy())
            times.append(total_time)

            # Debug prints
            print(f"Step {total_time}: α={alpha_t:.4f}, x_min={current_x.min():.2f}, x_max={current_x.max():.2f}, z_min={z_interp.min():.2f}, z_max={z_interp.max():.2f}")

            frame_paths.append(save_frame(current_x, z_interp, total_time, frame_idx))
            frame_idx += 1

            current_z = z_interp  # Update current z for next iteration

    if create_animation:
        images = [imageio.imread(fp) for fp in frame_paths]
        imageio.mimsave('alpha_z_topo_evolution.gif', images, duration=0.5)
        print("Animation saved as alpha_z_topo_evolution.gif")

    print("Integral α_z topography evolution complete.")


if __name__ == "__main__":
    run_alpha_z_evolution(create_animation=True)
