# models/exponential.py
"""
Exponential landscape evolution model.
Pure model logic - all visualization handled by plotter module.
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


def interpolate_dx(topo_x, vector_x, dx):
    """
    Interpolates dx to the topography points with bounds checking.
    
    Args:
        topo_x: Topography x coordinates
        vector_x: Vector x coordinates
        dx: Displacement values
    
    Returns:
        array: Interpolated dx values
    """
    f_dx = interp1d(vector_x, dx, kind='linear', 
                   bounds_error=False, fill_value=(dx[0], dx[-1]))
    interp_dx = f_dx(topo_x)
    interp_dx = np.clip(interp_dx, -100, 100)
    return interp_dx


def alpha_function(t, t_initial, t_final, lambda_topo):
    """
    Exponential interpolation function.
    
    Args:
        t: Current time
        t_initial: Initial time
        t_final: Final time
        lambda_topo: Exponential decay constant
    
    Returns:
        float: Alpha value [0, 1]
    """
    numerator = 1 - np.exp(-(t - t_initial) / lambda_topo)
    denominator = 1 - np.exp(-(t_final - t_initial) / lambda_topo)
    return numerator / denominator


def compute_topography_state(x_modern, z_modern, current_x, original_x_positions, 
                             time_ma, t_initial, t_final, lambda_topo, z_initial):
    """
    Compute the topography state for a given time.
    Pure computation function with no side effects.
    
    Args:
        x_modern: Modern x coordinates
        z_modern: Modern z elevations
        current_x: Current x coordinates
        original_x_positions: Original x positions (for tracking)
        time_ma: Current time in Ma
        t_initial: Initial time
        t_final: Final time
        lambda_topo: Exponential decay constant
        z_initial: Initial elevation
    
    Returns:
        tuple: (x_remeshed, z_remeshed)
    """
    num_points = len(x_modern)
    
    # Remesh x coordinates
    x_remeshed = np.linspace(current_x.min(), current_x.max(), num_points)
    
    # Interpolate original positions to new mesh
    f_orig_x = interp1d(current_x, original_x_positions, kind='linear',
                       bounds_error=False, fill_value='extrapolate')
    original_x_positions_remeshed = f_orig_x(x_remeshed)
    
    # Compute Z using exponential function
    t_for_alpha = t_initial - time_ma
    alpha_t = alpha_function(t_for_alpha, t_final, t_initial, lambda_topo)
    z_profile = z_initial + alpha_t * (z_modern - z_initial)
    
    # Interpolate Z to remeshed coordinates
    f_z = interp1d(x_modern, z_profile, kind='linear', 
                  bounds_error=False, fill_value='extrapolate')
    z_remeshed = f_z(original_x_positions_remeshed)
    
    return x_remeshed, z_remeshed, original_x_positions_remeshed


def run_exponential_model(params=None, create_animation=False):
    """
    Run the exponential landscape evolution model.
    Hybrid approach: X translation from vectors (backward), Z from exponential equation.
    
    Args:
        params: Optional dictionary of parameters (for GUI integration)
        create_animation: If True, creates animation frames and GIF
    """
    print(f"\n{'='*60}")
    print("EXPONENTIAL MODEL: Vector-based X + Exponential Z")
    print(f"{'='*60}")
    
    # Use params if provided, otherwise use config defaults
    if params:
        lambda_topo = params.get('exp_lambda_topo', config.exp_lambda_topo)
        z_initial = params.get('exp_z_initial', config.exp_z_initial)
    else:
        lambda_topo = config.exp_lambda_topo
        z_initial = config.exp_z_initial
    
    # Load data
    x_modern, z_modern = load_topography()
    sections = load_geological_sections() if config.plot_geological_sections else None
    vector_data = load_all_vector_files()
    
    # Get time parameters from config
    t_initial = config.t_initial
    t_final = config.t_final
    
    print(f"\nModel Parameters:")
    print(f"  Time range: {t_final} Ma (modern) → {t_initial} Ma (past)")
    print(f"  Lambda: {lambda_topo} Ma")
    print(f"  Initial elevation at {t_initial} Ma: {z_initial} km")
    
    # Initialize state
    num_points = len(x_modern)
    current_x = x_modern.copy()
    original_x_positions = x_modern.copy()
    x_right_fixed = x_modern.max()
    
    # Setup animation if requested
    if create_animation:
        plotter = TopographyPlotter(x_modern, z_modern, sections)
        anim_manager = AnimationManager()
        
        print(f"\nGenerating animation frames...")
    
    # Frame 0: Modern topography
    time_elapsed = 0
    
    if create_animation:
        x_plot, z_plot, _ = compute_topography_state(
            x_modern, z_modern, current_x, original_x_positions,
            time_elapsed, t_initial, t_final, lambda_topo, z_initial
        )
        
        fig = plotter.plot_frame(
            x_plot, z_plot, time_elapsed, 
            model_name="Reverse Model",
            additional_info=f"λ={lambda_topo} Ma"
        )
        
        frame_path = anim_manager.get_frame_path(time_elapsed)
        plotter.save_frame(fig, frame_path)
        anim_manager.add_frame(frame_path)
    
    # Process each vector file going backward in time
    for fname in config.vector_files.keys():
        vec_data = vector_data[fname]
        duration = vec_data['duration']
        
        print(f"\nProcessing {fname} for {duration} Ma")
        
        # Compute rate of displacement
        dx_dt = -vec_data['dx'] / duration
        
        for year in range(duration):
            time_elapsed += 1
            
            if time_elapsed % 5 == 0:
                print(f"  Time: {time_elapsed} Ma")
            
            # Apply X translation
            interp_dx_dt = interpolate_dx(current_x, vec_data['x'], dx_dt)
            current_x += interp_dx_dt
            
            # Keep right edge fixed
            x_shift = current_x.max() - x_right_fixed
            current_x -= x_shift
            
            # Compute current topography state
            x_remeshed, z_remeshed, original_x_positions = compute_topography_state(
                x_modern, z_modern, current_x, original_x_positions,
                time_elapsed, t_initial, t_final, lambda_topo, z_initial
            )
            
            # Update current state
            current_x = x_remeshed
            
            # Create animation frame
            if create_animation:
                fig = plotter.plot_frame(
                    x_remeshed, z_remeshed, time_elapsed,
                    model_name="Reverse Model",
                    additional_info=f"λ={lambda_topo} Ma"
                )
                
                frame_path = anim_manager.get_frame_path(time_elapsed)
                plotter.save_frame(fig, frame_path)
                anim_manager.add_frame(frame_path)
    
    # Create final GIF
    if create_animation:
        anim_manager.create_gif()
    
    print("\n" + "="*60)
    print("Exponential model completed successfully!")
    print("="*60)


if __name__ == '__main__':
    run_exponential_model(create_animation=True)