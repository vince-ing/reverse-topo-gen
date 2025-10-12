# models/hybrid.py
"""
Hybrid landscape evolution model.
Combines vector-based X translation with vector-weighted exponential Z decay.
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


def precompute_total_weighted_dz(x_modern, vector_data, erosion_efficiency):
    """
    Pre-compute total cumulative dz weighted by erosion efficiency.
    Used for normalization to ensure boundary conditions are met.
    
    Args:
        x_modern: Modern x coordinates
        vector_data: Dictionary of vector data
        erosion_efficiency: Erosion efficiency parameter
    
    Returns:
        array: Total weighted dz for each point
    """
    total_weighted_dz = np.zeros_like(x_modern)
    
    print(f"\nPre-computing total weighted dz for normalization...")
    
    for fname, vec_data in vector_data.items():
        _, interp_dz = interpolate_vectors(x_modern, vec_data['x'], 
                                          vec_data['dx'], vec_data['dz'])
        total_weighted_dz += erosion_efficiency * np.abs(interp_dz)
        print(f"  {fname}: dz range = {interp_dz.min():.2f} to {interp_dz.max():.2f}")
    
    print(f"  Total weighted dz: {total_weighted_dz.min():.2f} to {total_weighted_dz.max():.2f}")
    
    return total_weighted_dz


def compute_hybrid_state(x_modern, z_modern, current_x, original_x_positions,
                        cumulative_weighted_dz, total_weighted_dz,
                        time_elapsed, total_time, z_initial, blend_factor):
    """
    Compute the hybrid model state for a given time.
    Blends time-based progress with spatial dz pattern.
    
    Args:
        x_modern: Modern x coordinates
        z_modern: Modern z elevations
        current_x: Current x coordinates
        original_x_positions: Original x positions (for tracking)
        cumulative_weighted_dz: Cumulative weighted dz so far
        total_weighted_dz: Total weighted dz (normalization)
        time_elapsed: Current time in Ma
        total_time: Total simulation time
        z_initial: Target initial elevation
        blend_factor: Weight between time-based and spatial progress
    
    Returns:
        tuple: (x_remeshed, z_remeshed, original_x_remeshed, cumulative_dz_remeshed, progress)
    """
    num_points = len(x_modern)
    
    # Remesh x coordinates
    x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
    
    # Interpolate tracking variables to new mesh
    f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                       bounds_error=False, fill_value='extrapolate')
    original_x_remeshed = f_orig_x(x_remeshed)
    
    f_cumsum = interp1d(current_x, cumulative_weighted_dz, kind='linear',
                       bounds_error=False, fill_value='extrapolate')
    cumulative_dz_remeshed = f_cumsum(x_remeshed)
    
    # Get modern values at original positions
    f_z_modern = interp1d(x_modern, z_modern, kind='linear',
                         bounds_error=False, fill_value='extrapolate')
    z_modern_at_points = f_z_modern(original_x_remeshed)
    
    f_total_dz = interp1d(x_modern, total_weighted_dz, kind='linear',
                         bounds_error=False, fill_value='extrapolate')
    total_dz_at_points = f_total_dz(original_x_remeshed)
    
    # Calculate progress: blend time-based with spatial weighting
    time_progress = time_elapsed / total_time  # Pure time-based (0 to 1)
    
    # Spatial weighting: areas with more dz deviate from uniform time_progress
    spatial_weight = np.ones_like(total_dz_at_points)
    mask = total_dz_at_points > 0.01
    if mask.any():
        spatial_weight[mask] = cumulative_dz_remeshed[mask] / total_dz_at_points[mask]
        spatial_weight = np.clip(spatial_weight, 0, 2)  # Allow spatial variation
    
    # Blend: ensures all points reach 1.0 at final time, with spatial heterogeneity
    progress = blend_factor * time_progress + (1 - blend_factor) * spatial_weight * time_progress
    progress = np.clip(progress, 0, 1)
    
    # Interpolate elevation: z = z_modern + progress * (z_initial - z_modern)
    z_remeshed = z_modern_at_points + progress * (z_initial - z_modern_at_points)
    
    return x_remeshed, z_remeshed, original_x_remeshed, cumulative_dz_remeshed, progress


def run_hybrid_model(params=None, create_animation=False):
    """
    Run the hybrid landscape evolution model.
    X translation from vectors, Z decay uses vector spatial pattern 
    scaled to reach flat elevation at t_initial.
    
    Args:
        params: Optional dictionary of parameters (for GUI integration)
        create_animation: If True, creates animation frames and GIF
    """
    print(f"\n{'='*60}")
    print("HYBRID MODEL: Vector X + Vector-weighted exponential Z")
    print(f"{'='*60}")
    
    # Use params if provided, otherwise use config defaults
    if params:
        z_initial = params.get('hybrid_z_initial', config.hybrid_z_initial)
        erosion_efficiency = params.get('hybrid_erosion_efficiency', config.hybrid_erosion_efficiency)
        blend_factor = params.get('hybrid_blend_factor', config.hybrid_blend_factor)
    else:
        z_initial = config.hybrid_z_initial
        erosion_efficiency = config.hybrid_erosion_efficiency
        blend_factor = config.hybrid_blend_factor
    
    # Load data
    x_modern, z_modern = load_topography()
    sections = load_geological_sections() if config.plot_geological_sections else None
    vector_data = load_all_vector_files()
    
    # Get time parameters from config
    t_initial = config.t_initial
    t_final = config.t_final
    total_time = sum(config.vector_files.values())
    
    print(f"\nModel Parameters:")
    print(f"  Time range: {t_final} Ma (modern) → {total_time} Ma (flat)")
    print(f"  Target elevation at {total_time} Ma: {z_initial} km")
    print(f"  Erosion efficiency: {erosion_efficiency} (spatial pattern weight)")
    print(f"  Blend factor: {blend_factor} (time vs spatial weighting)")
    
    # Pre-compute normalization
    total_weighted_dz = precompute_total_weighted_dz(x_modern, vector_data, erosion_efficiency)
    
    # Initialize state
    num_points = len(x_modern)
    current_x = x_modern.copy()
    current_z = z_modern.copy()
    original_x_positions = x_modern.copy()
    cumulative_weighted_dz = np.zeros_like(x_modern)
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
            model_name="Hybrid Model",
            additional_info=f"ε={erosion_efficiency}, β={blend_factor}"
        )
        
        frame_path = anim_manager.get_frame_path(time_elapsed)
        plotter.save_frame(fig, frame_path)
        anim_manager.add_frame(frame_path)
    
    # Process each vector file going backward in time
    for fname in config.vector_files.keys():
        vec_data = vector_data[fname]
        duration = vec_data['duration']
        
        print(f"\nProcessing {fname} for {duration} Ma")
        print(f"  Vector dz range: {vec_data['dz'].min():.2f} to {vec_data['dz'].max():.2f}")
        
        # Compute rates
        dx_dt = -vec_data['dx'] / duration
        dz_dt = vec_data['dz'] / duration
        
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
            
            # Update cumulative weighted dz (track progress toward total)
            f_cumsum = interp1d(current_x, cumulative_weighted_dz, kind='linear',
                               bounds_error=False, fill_value='extrapolate')
            cumulative_weighted_dz = f_cumsum(current_x)
            cumulative_weighted_dz += erosion_efficiency * np.abs(interp_dz_dt)
            
            # Compute current topography state with hybrid approach
            x_remeshed, z_remeshed, original_x_positions, cumulative_weighted_dz, progress = \
                compute_hybrid_state(
                    x_modern, z_modern, current_x, original_x_positions,
                    cumulative_weighted_dz, total_weighted_dz,
                    time_elapsed, total_time, z_initial, blend_factor
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
                    model_name="Hybrid Model",
                    additional_info=f"ε={erosion_efficiency}, β={blend_factor}"
                )
                
                frame_path = anim_manager.get_frame_path(time_elapsed)
                plotter.save_frame(fig, frame_path)
                anim_manager.add_frame(frame_path)
    
    # Create final GIF
    if create_animation:
        anim_manager.create_gif()
    
    print("\n" + "="*60)
    print("Hybrid model completed successfully!")
    print(f"Final state at {time_elapsed} Ma should be flat at {z_initial} km")
    print("="*60)


if __name__ == '__main__':
    run_hybrid_model(create_animation=True)