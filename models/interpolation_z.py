import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from pathlib import Path
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from config import *
import os

def load_topography(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    data = [list(map(float, line.split())) for line in lines[1:]]
    data = np.array(data)
    print(f"Initial Topography Min/Max Z: {data[:, 1].min()}, {data[:, 1].max()}")
    return data[:, 0], data[:, 1]

def run_interpolation_alpha_z(create_animation=False):
    topo_file = Path("data/Topo/topo_04.dat")
    x_topo, z_topo = load_topography(topo_file)
    num_points = len(x_topo)

    # Prepare toy time axis for demo: 0 (present) to t_max (past, e.g., 27 Ma)
    t_max = exp_t_initial   # Use your configured max time
    times = np.linspace(0, t_max, exp_num_frames)  # exp_num_frames from config

    # Prepare a synthetic (or real) elevation history for demonstration
    # Use shape (n_frames, n_points)
    # Ideally, you would have your z_topo_history from per-frame back-projection
    z_profiles = np.zeros((len(times), num_points))
    z_profiles[0] = z_topo  # Start with modern topo
    for i in range(1, len(times)):
        # Here we use some synthetic evolution (for demo)
        z_profiles[i] = z_profiles[0] - i * (z_profiles[0] / t_max) * (times[i] / t_max)  # Simple model

    # Compute Δz (difference between each time frame, axis=0 is time)
    delta_z = np.diff(z_profiles, axis=0)           # Shape: (frames-1, n_points)
    mean_delta_z = np.mean(np.abs(delta_z), axis=1) # Mean abs change for each time step (vector for each frame)

    # Compute cumulative sum for numerator (α_z(t) numerator up to time t)
    # and total sum for denominator (full history)
    lambda_topo = exp_lambda_topo   # from config
    exp_sum_t = np.cumsum(mean_delta_z / lambda_topo)   # up to time t
    exp_sum_end = np.sum(mean_delta_z / lambda_topo)    # total

    # α_z(t) for each timestep (note: one fewer than z_profiles, so pad)
    alpha_z = np.zeros(len(times))
    alpha_z[1:] = (1 - np.exp(-exp_sum_t)) / (1 - np.exp(-exp_sum_end))
    alpha_z[0] = 0  # At present, alpha = 0

    if create_animation:
        frames_dir = Path("frames_output")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []
        x_min, x_max = x_topo.min(), x_topo.max()
        for i, alpha in enumerate(alpha_z):
            # Weighted topography between z_initial and z_final using alpha_z(t)
            z_interp = exp_z_initial + alpha * (z_topo - exp_z_initial)
            plt.figure(figsize=(10, 6))
            plt.plot(x_topo, z_interp, color='b')
            plt.title(f"Topography α_z(t) Model - {times[i]:.1f} Ma")
            plt.xlabel("X (km)")
            plt.ylabel("Z (km)")
            plt.xlim(x_min, x_max)
            plt.grid(True)
            plt.tight_layout()
            frame_path = frames_dir / f"frame_{i:02d}.png"
            plt.savefig(frame_path)
            plt.close()
            frame_paths.append(frame_path)
        # Write GIF
        images = [imageio.imread(fp) for fp in frame_paths]
        imageio.mimsave("topo_evolution_alpha_z.gif", images, duration=0.5)
        print("Animation saved as topo_evolution_alpha_z.gif")

    print("Alpha_z(t) topography evolution complete.")

if __name__ == "__main__":
    run_interpolation_alpha_z(create_animation=True)
