import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from scipy.interpolate import interp1d

def resample_vector_to_topo(x_vector_coords, vector_vals, x_topo):
    """
    Resample vector_vals from its native x_vector_coords grid to x_topo grid.
    """
    if len(x_vector_coords) != len(vector_vals):
        raise ValueError(
            f"x_vector_coords and vector_vals length mismatch: "
            f"{len(x_vector_coords)} vs {len(vector_vals)}"
        )
    interpolator = interp1d(x_vector_coords, vector_vals, bounds_error=False, fill_value="extrapolate")
    return interpolator(x_topo)

# In models/interpolation.py

def interpolate_surface(
    x_init: np.ndarray,
    z_init: np.ndarray,
    vector_x_list: list,
    vector_z_list: list,
    vector_x_coords_list: list,
    time_stamps: list,
    desired_times: list,
    lambda_topo: float = 10.0  # This is no longer used if you make z linear
):
    """
    Returns a list of (x, z) tuples for each desired time, backprojected/interpolated.
    """
    N = len(x_init)
    if not (len(vector_x_list) == len(time_stamps) - 1):
        raise ValueError("Vector lists must be one fewer than time stamps")

    # --- OPTIMIZATION: Resample all vectors ONCE before the main loop ---
    resampled_intervals = []
    for i in range(len(time_stamps) - 1):
        t0, t1 = time_stamps[i], time_stamps[i+1]
        dx_raw, dz_raw, x_vec_coords = vector_x_list[i], vector_z_list[i], vector_x_coords_list[i]
        
        # Resample dx and dz onto the topography's x-coordinates
        dx_resampled = resample_vector_to_topo(x_vec_coords, dx_raw, x_init)
        dz_resampled = resample_vector_to_topo(x_vec_coords, dz_raw, x_init)
        
        resampled_intervals.append((t0, t1, dx_resampled, dz_resampled))
    # --------------------------------------------------------------------

    results = []
    for t in desired_times:
        cumulative_dx = np.zeros(N)
        cumulative_dz = np.zeros(N)

        # Use the pre-calculated resampled vectors
        for (t0, t1, dx, dz) in resampled_intervals:
            if t >= t0 and t <= t1:
                alpha = (t - t0) / (t1 - t0)
                cumulative_dx += alpha * dx
                cumulative_dz += alpha * dz
                break
            elif t > t1:
                cumulative_dx += dx
                cumulative_dz += dz
        
        x_proj = x_init - cumulative_dx
        
        # --- FIX: Using simple linear change for Z for consistency ---
        z_proj = z_init - cumulative_dz
        # -------------------------------------------------------------

        results.append((x_proj, z_proj))
        
    return results


def save_topography_gif(
    topographies,
    filename='interpolated_topography.gif',
    xlim=None,
    ylim=None,
    figsize=(8, 8),
    duration=0.8
):
    """
    topographies: list of (x, z) tuples for each frame
    """
    frames = []
    for i, (x, z) in enumerate(topographies):
        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(x, z, color='sienna', lw=2)
        ax.set_aspect('equal', adjustable='box')
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)
        ax.set_title(f'Topography t={i}')
        ax.set_xlabel('X')
        ax.set_ylabel('Z')
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.canvas.draw()
        
        # Convert ARGB buffer to RGB image array
        data = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
        h, w = fig.canvas.get_width_height()
        data = data.reshape(h, w, 4)
        img = data[:, :, 1:4]  # Extract RGB channels
        
        frames.append(img)
        plt.close(fig)
    
    imageio.mimsave(filename, frames, duration=duration)
