# interpolation_z.py 

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from pathlib import Path
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from config import *
import os

def load_topography(filepath):
    """Loads topography data from a file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    # Skip header
    data = [list(map(float, line.split())) for line in lines[1:]]
    data = np.array(data)
    print(f"Initial Topography Min/Max Z: {data[:, 1].min()}, {data[:, 1].max()}")
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
    # Use nearest neighbor for out-of-bounds instead of extrapolation
    f_dx = interp1d(vector_x, dx, kind='linear', bounds_error=False, fill_value=(dx[0], dx[-1]))
    f_dz = interp1d(vector_x, dz, kind='linear', bounds_error=False, fill_value=(dz[0], dz[-1]))
    interp_dx = f_dx(topo_x)
    interp_dz = f_dz(topo_x)
    
    # Clip extreme values as a safety measure
    interp_dx = np.clip(interp_dx, -100, 100)  # Maximum 100 km displacement per Ma
    interp_dz = np.clip(interp_dz, -100, 100)  # Maximum 100 km vertical change per Ma
    
    return interp_dx, interp_dz

def run_interpolation(create_animation=False):
    """
    Runs the interpolation of topography over time.
    If create_animation is True, it will generate a GIF of the process.
    """
    topo_file = Path("data/Topo/topo_04.dat")
    vector_files = {
        "v_00.dat": 5,
        "v_01.dat": 4,
        "v_02.dat": 11,
        "v_03.dat": 7,
    }

    x_topo, z_topo = load_topography(topo_file)
    current_topo = np.vstack((x_topo, z_topo)).T
    num_points = len(x_topo)  # Remember original number of points for remeshing

    print(f"Starting interpolation with {topo_file.name}")

    if create_animation:
        frames_dir = Path("frames_output")
        frames_dir.mkdir(exist_ok=True)
        frame_paths = []
        x_min, x_max = x_topo.min(), x_topo.max()
        
        # Plot initial topography
        plt.figure(figsize=(10, 6))
        plt.plot(current_topo[:, 0], current_topo[:, 1], color='g', label='Initial Topography')
        plt.title("Initial Topography (0 Ma)")
        plt.xlabel("X (km)")
        plt.ylabel("Z (km)")
        plt.legend()
        plt.grid(True)
        plt.savefig(frames_dir / "initial_topo.png")
        plt.close()
        print("Saved initial topography plot to 'frames_output/initial_topo.png'")

        # Use adaptive y-limits instead of pre-calculating
        # Start with initial topography range + 50% margin
        z_margin = (z_topo.max() - z_topo.min()) * 0.5
        z_min_initial = z_topo.min() - z_margin
        z_max_initial = z_topo.max() + z_margin

    time_elapsed = 0
    # Main loop for processing and creating frames
    for fname, duration in vector_files.items():
        vector_file = Path("data/Vectors") / fname
        print(f"Processing {vector_file.name} for a duration of {duration} million years.")

        vec_x, dx, dz = load_vectors(vector_file)
        
        # Print vector statistics for debugging
        print(f"  Vector X range: {vec_x.min():.2f} to {vec_x.max():.2f}")
        print(f"  dx range: {dx.min():.2f} to {dx.max():.2f}")
        print(f"  dz range: {dz.min():.2f} to {dz.max():.2f}")
        
        dx_dt = dx / duration
        dz_dt = dz / duration

        for year in range(duration):
            time_elapsed += 1
            print(f"  - Year: {time_elapsed} million years ago")

            interp_dx_dt, interp_dz_dt = interpolate_vectors(current_topo[:, 0], vec_x, dx_dt, dz_dt)
            
            current_topo[:, 0] -= interp_dx_dt
            current_topo[:, 1] -= interp_dz_dt
            
            # Remesh to maintain even point spacing and prevent bunching
            x_new = np.linspace(current_topo[:, 0].min(), current_topo[:, 0].max(), num_points)
            f_z = interp1d(current_topo[:, 0], current_topo[:, 1], kind='linear', 
                          bounds_error=False, fill_value='extrapolate')
            z_new = f_z(x_new)
            current_topo = np.vstack((x_new, z_new)).T
            
            # Check for anomalies
            if np.any(np.abs(current_topo[:, 1]) > 1000):
                print(f"    WARNING: Extreme Z values detected at frame {time_elapsed}")
                print(f"    Z-range: {current_topo[:, 1].min():.2f} to {current_topo[:, 1].max():.2f}")
            
            if create_animation:
                print(f"    Frame {time_elapsed}: Z-range = {current_topo[:, 1].min():.2f} to {current_topo[:, 1].max():.2f}")
                
                # Use adaptive y-limits that expand as needed
                curr_z_min = current_topo[:, 1].min()
                curr_z_max = current_topo[:, 1].max()
                z_range = curr_z_max - curr_z_min
                plot_margin = max(z_range * 0.1, 1.0)  # At least 1 km margin
                
                plt.figure(figsize=(10, 6))
                plt.plot(current_topo[:, 0], current_topo[:, 1], color='b')
                plt.title(f"Topography at {time_elapsed} Ma")
                plt.xlabel("X (km)")
                plt.ylabel("Z (km)")
                plt.xlim(x_min, x_max)
                plt.ylim(curr_z_min - plot_margin, curr_z_max + plot_margin)
                plt.gca().set_aspect(vertical_exaggeration)
                plt.grid(True)
                frame_path = frames_dir / f"frame_{time_elapsed:02d}.png"
                plt.savefig(frame_path)
                plt.close()
                frame_paths.append(frame_path)

    if create_animation:
        print("\nCreating animation...")
        images = [imageio.imread(fp) for fp in sorted(frame_paths)]
        imageio.mimsave('topo_evolution_z.gif', images, duration=0.5)
        print("Animation saved as topo_evolution_z.gif")

    print("\nInterpolation finished.")
    print("Final topography represents the state at 27 million years ago.")
    print(f"Final Z-range: {current_topo[:, 1].min():.2f} to {current_topo[:, 1].max():.2f}")

if __name__ == '__main__':
    run_interpolation(create_animation=True)