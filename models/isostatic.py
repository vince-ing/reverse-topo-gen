# models/isostatic.py
"""
Isostatic landscape evolution model.
X translation from vectors, Z from vectors with isostatic compensation.

Physics: When rock is exhumed (dz > 0), some becomes topography and some
is compensated by isostatic uplift of underlying crust.

Surface elevation change = rock_uplift - erosion + isostatic_response

For local Airy isostasy:
isostatic_uplift = (ρ_crust / ρ_mantle) * material_removed

Net topography = rock_uplift * (1 - ρ_crust/ρ_mantle)
Net topography ≈ rock_uplift * 0.15 to 0.3 (depending on densities)
"""

import numpy as np
from scipy.interpolate import interp1d
import config
from visualization.data_loader import (
    load_topography, 
    load_geological_sections, 
    load_all_vector_files
)
from visualization.plotter import TopographyPlotter, AnimationManager
from .erosion import calculate_climate_erosion_factor


def interpolate_vectors(topo_x, vector_x, dx, dz):
    """
    Interpolates dx and dz to the topography points with bounds checking.
    
    Args:
        topo_x: Topography x coordinates
        vector_x: Vector x coordinates
        dx: X displacement values
        dz: Z displacement values
    
    Returns:
        tuple: (interp_dx, interp_dz) arrays
    """
    f_dx = interp1d(vector_x, dx, kind='linear', 
                   bounds_error=False, fill_value=(dx[0], dx[-1]))
    f_dz = interp1d(vector_x, dz, kind='linear', 
                   bounds_error=False, fill_value=(dz[0], dz[-1]))
    
    interp_dx = f_dx(topo_x)
    interp_dz = f_dz(topo_x)
    
    # Clip extreme values as safety measure
    interp_dx = np.clip(interp_dx, -100, 100)
    interp_dz = np.clip(interp_dz, -100, 100)
    
    return interp_dx, interp_dz


def calculate_isostatic_efficiency(rho_crust, rho_mantle):
    """
    Calculate isostatic efficiency: fraction of rock uplift that becomes topography.
    
    Args:
        rho_crust: Crustal density (kg/m³)
        rho_mantle: Mantle density (kg/m³)
    
    Returns:
        float: Isostatic efficiency (0-1)
    """
    return 1 - (rho_crust / rho_mantle)


def precompute_total_topographic_change(x_modern, vector_data, isostatic_efficiency):
    """
    Pre-compute total topographic change with isostatic compensation.
    
    Args:
        x_modern: Modern x coordinates
        vector_data: Dictionary of vector data
        isostatic_efficiency: Isostatic efficiency factor
    
    Returns:
        array: Total topographic change for each point
    """
    total_topo_change = np.zeros_like(x_modern)
    
    print(f"\nPre-computing total topographic change with isostasy...")
    
    for fname, vec_data in vector_data.items():
        _, interp_dz = interpolate_vectors(x_modern, vec_data['x'], 
                                          vec_data['dx'], vec_data['dz'])
        
        # Surface elevation change = rock_displacement * isostatic_efficiency
        topo_change = isostatic_efficiency * interp_dz
        total_topo_change += topo_change
        
        print(f"  {fname}: rock dz = {interp_dz.min():.2f} to {interp_dz.max():.2f}, "
              f"topo change = {topo_change.min():.2f} to {topo_change.max():.2f}")
    
    print(f"  Total topographic change: {total_topo_change.min():.2f} to {total_topo_change.max():.2f} km")
    
    return total_topo_change


def apply_smoothing(z, window_size):
    """
    Apply moving average smoothing to prevent interpolation artifacts.
    
    Args:
        z: Elevation array
        window_size: Size of smoothing window
    
    Returns:
        array: Smoothed elevation
    """
    if len(z) <= window_size:
        return z
    
    kernel = np.ones(window_size) / window_size
    return np.convolve(z, kernel, mode='same')


def compute_isostatic_state(x_modern, z_modern, current_x, original_x_positions,
                           cumulative_topo_change, total_topo_change,
                           time_elapsed, total_time, z_initial, blend_factor,
                           smoothing_window):
    """
    Compute the isostatic model state for a given time.
    Blends time-based progress with spatial topographic change pattern.
    
    Args:
        x_modern: Modern x coordinates
        z_modern: Modern z elevations
        current_x: Current x coordinates
        original_x_positions: Original x positions (for tracking)
        cumulative_topo_change: Cumulative topographic change so far
        total_topo_change: Total topographic change (normalization)
        time_elapsed: Current time in Ma
        total_time: Total simulation time
        z_initial: Target initial elevation
        blend_factor: Weight between time-based and spatial progress
        smoothing_window: Window size for smoothing
    
    Returns:
        tuple: (x_remeshed, z_remeshed, original_x_remeshed, cumulative_change_remeshed, progress)
    """
    num_points = len(x_modern)
    
    # Remesh x coordinates
    x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
    
    # Interpolate tracking variables to new mesh
    f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                       bounds_error=False, fill_value='extrapolate')
    original_x_remeshed = f_orig_x(x_remeshed)
    
    f_cumsum = interp1d(current_x, cumulative_topo_change, kind='linear',
                       bounds_error=False, fill_value='extrapolate')
    cumulative_change_remeshed = f_cumsum(x_remeshed)
    
    # Get modern values at original positions
    f_z_modern = interp1d(x_modern, z_modern, kind='linear',
                         bounds_error=False, fill_value='extrapolate')
    z_modern_at_points = f_z_modern(original_x_remeshed)
    
    f_total_change = interp1d(x_modern, total_topo_change, kind='linear',
                             bounds_error=False, fill_value='extrapolate')
    total_change_at_points = f_total_change(original_x_remeshed)
    
    # Calculate progress: blend time-based with spatial weighting
    time_progress = time_elapsed / total_time  # Pure time-based (0 to 1)
    
    # Spatial progress based on cumulative topographic change
    spatial_progress = np.zeros_like(total_change_at_points)
    mask = np.abs(total_change_at_points) > 0.01
    spatial_progress[mask] = cumulative_change_remeshed[mask] / total_change_at_points[mask]
    spatial_progress = np.clip(spatial_progress, 0, 1)
    
    # Blend: ensures all points reach 1.0 at final time, with spatial heterogeneity
    progress = blend_factor * time_progress + (1 - blend_factor) * spatial_progress
    progress = np.clip(progress, 0, 1)
    
    # Interpolate elevation to flat baseline
    z_remeshed = z_modern_at_points + progress * (z_initial - z_modern_at_points)
    
    # Apply smoothing to prevent artifacts
    z_remeshed = apply_smoothing(z_remeshed, smoothing_window)
    
    return x_remeshed, z_remeshed, original_x_remeshed, cumulative_change_remeshed, progress


def run_isostatic_model(params, create_animation=False):
    """
    Run the isostatic landscape evolution model.
    X translation from vectors, Z from vectors with isostatic compensation.
    
    Args:
        create_animation: If True, creates animation frames and GIF
    """
    print(f"\n{'='*60}")
    print("ISOSTATIC MODEL: Vector-based with isostatic compensation")
    print(f"{'='*60}")

    blend_factor = params['isostatic_blend_factor']
    smoothing_window = params['isostatic_smoothing_window']
    rho_crust = params['isostatic_rho_crust']
    rho_mantle = params['isostatic_rho_mantle']
    
    # Load data
    x_modern, z_modern = load_topography()
    sections = load_geological_sections() if config.plot_geological_sections else None
    vector_data = load_all_vector_files()
    
    # Get parameters from config
    t_initial = config.t_initial
    t_final = config.t_final
    z_initial = config.isostatic_z_initial
    rho_crust = config.isostatic_rho_crust
    rho_mantle = config.isostatic_rho_mantle
    blend_factor = config.isostatic_blend_factor
    smoothing_window = config.isostatic_smoothing_window
    
    # Calculate isostatic efficiency
    isostatic_efficiency = calculate_isostatic_efficiency(rho_crust, rho_mantle)
    
    total_time = sum(config.vector_files.values())
    
    print(f"\nModel Parameters:")
    print(f"  Time range: {t_final} Ma (modern) → {total_time} Ma (flat)")
    print(f"  Crustal density: {rho_crust} kg/m³")
    print(f"  Mantle density: {rho_mantle} kg/m³")
    print(f"  Isostatic efficiency: {isostatic_efficiency:.3f}")
    print(f"  (Only {isostatic_efficiency*100:.1f}% of rock uplift becomes topographic relief)")
    print(f"  Target elevation at {total_time} Ma: {z_initial} km")
    print(f"  Blend factor: {blend_factor} (time vs spatial weighting)")
    
    # Pre-compute normalization
    total_topo_change = precompute_total_topographic_change(x_modern, vector_data, isostatic_efficiency)
    
    # Initialize state
    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()
    original_x_positions = x_modern.copy()
    cumulative_topo_change = np.zeros_like(x_modern)
    x_right_fixed = x_modern.max()
    
    # Setup animation if requested
    if create_animation:
        plotter = TopographyPlotter(x_modern, z_modern, sections)
        anim_manager = AnimationManager()
        
        print(f"\nGenerating animation frames...")
    
    # Frame 0: Modern topography
    time_elapsed = 0
    
    if create_animation:
        fig = plotter.plot_frame(
            current_x, current_z, time_elapsed,
            model_name="Isostatic Model",
            additional_info=f"η={isostatic_efficiency:.2f}"
        )
        
        frame_path = anim_manager.get_frame_path(time_elapsed)
        plotter.save_frame(fig, frame_path)
        anim_manager.add_frame(frame_path)
    
    # Process each vector file going backward in time
    for fname in config.vector_files.keys():
        vec_data = vector_data[fname]
        duration = vec_data['duration']
        
        print(f"\nProcessing {fname} for {duration} Ma")
        print(f"  Vector rock dz range: {vec_data['dz'].min():.2f} to {vec_data['dz'].max():.2f}")
        
        # Compute rates
        dx_dt = -vec_data['dx'] / duration
        dz_dt = vec_data['dz'] / duration  # Rock displacement rate
        
        for year in range(duration):
            time_elapsed += 1
            
            if time_elapsed % 5 == 0:
                print(f"  Time: {time_elapsed} Ma")
            
            # Apply X translation
            interp_dx_dt, interp_dz_dt = interpolate_vectors(
                current_x, vec_data['x'], dx_dt, dz_dt
            )
            current_x += interp_dx_dt
            
            # Keep right edge fixed
            x_shift = current_x.max() - x_right_fixed
            current_x -= x_shift
            
            # Update cumulative topographic change (with isostasy)
            f_cumsum = interp1d(current_x, cumulative_topo_change, kind='linear',
                               bounds_error=False, fill_value='extrapolate')
            cumulative_topo_change = f_cumsum(current_x)
            
            # Add this timestep's topographic change
            topo_change_dt = isostatic_efficiency * interp_dz_dt
            cumulative_topo_change += topo_change_dt

            # Calculate the erosion factor based on the current topography
            climate_factor = calculate_climate_erosion_factor(current_x, current_z)
            
            # Add this timestep's topographic change, MODIFIED by the climate factor
            topo_change_dt = (isostatic_efficiency * interp_dz_dt) * climate_factor
            cumulative_topo_change += topo_change_dt
            
            if time_elapsed % 5 == 0:
                print(f"    Rock dz_dt: {interp_dz_dt.min():.4f} to {interp_dz_dt.max():.4f}")
                print(f"    Topo change: {topo_change_dt.min():.4f} to {topo_change_dt.max():.4f}")
            
            # Compute current topography state with isostatic approach
            x_remeshed, z_remeshed, original_x_positions, cumulative_topo_change, progress = \
                compute_isostatic_state(
                    x_modern, z_modern, current_x, original_x_positions,
                    cumulative_topo_change, total_topo_change,
                    time_elapsed, total_time, z_initial, blend_factor,
                    smoothing_window
                )
            
            if time_elapsed % 5 == 0:
                print(f"    Progress: min={progress.min():.3f}, max={progress.max():.3f}, mean={progress.mean():.3f}")
                print(f"    Z range: {z_remeshed.min():.2f} to {z_remeshed.max():.2f}")
            
            # Update current state
            current_x = x_remeshed
            current_z = z_remeshed
            
            # Create animation frame
            if create_animation:
                fig = plotter.plot_frame(
                    x_remeshed, z_remeshed, time_elapsed,
                    model_name="Isostatic Model",
                    additional_info=f"η={isostatic_efficiency:.2f}"
                )
                
                frame_path = anim_manager.get_frame_path(time_elapsed)
                plotter.save_frame(fig, frame_path)
                anim_manager.add_frame(frame_path)
    
    # Create final GIF
    if create_animation:
        anim_manager.create_gif()
    
    print("\n" + "="*60)
    print("Isostatic model completed successfully!")
    print(f"Final state at {time_elapsed} Ma (should be ~flat at {z_initial} km)")
    print("="*60)


if __name__ == '__main__':
    run_isostatic_model(create_animation=True)