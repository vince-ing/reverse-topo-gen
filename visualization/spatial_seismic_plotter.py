# spatial_seismic_plotter.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def plot_seismic_spatial(
    df: pd.DataFrame,
    topo_file: Path = None,
    vertical_exaggeration: float = 5.0,
    save_path: Path = None,
    use_coordinate: str = 'x',  # 'x', 'y', or 'both'
    remove_outliers: bool = True
):
    """
    Plot all seismic lines using actual spatial coordinates.
    
    Parameters
    ----------
    df : pd.DataFrame
        Full seismic dataset with x, y, z, line_id columns
    topo_file : Path, optional
        Path to topography file to overlay
    vertical_exaggeration : float
        Vertical exaggeration factor
    save_path : Path, optional
        If provided, save figure to this path
    use_coordinate : str
        Which coordinate to use for horizontal axis:
        'x' = use X coordinate (easting)
        'y' = use Y coordinate (northing)
        'both' = calculate distance from origin
    remove_outliers : bool
        If True, remove spatial outliers that are far from the main data cluster
    """
    import matplotlib.cm as cm
    
    # Filter outliers if requested
    if remove_outliers:
        # More aggressive outlier removal
        # Find the main cluster of data (middle 98%)
        x_q1, x_q99 = df['x'].quantile([0.01, 0.99])
        y_q1, y_q99 = df['y'].quantile([0.01, 0.99])
        
        print(f"Data range before filtering:")
        print(f"  X: {df['x'].min():.2f} to {df['x'].max():.2f}")
        print(f"  Y: {df['y'].min():.2f} to {df['y'].max():.2f}")
        
        # Use the middle 98% range, extended by only 0.5x the range
        x_range = x_q99 - x_q1
        y_range = y_q99 - y_q1
        
        x_min, x_max = x_q1 - 0.5*x_range, x_q99 + 0.5*x_range
        y_min, y_max = y_q1 - 0.5*y_range, y_q99 + 0.5*y_range
        
        # Filter
        initial_count = len(df)
        df = df[
            (df['x'] >= x_min) & (df['x'] <= x_max) &
            (df['y'] >= y_min) & (df['y'] <= y_max)
        ].copy()
        removed_count = initial_count - len(df)
        
        print(f"Removed {removed_count} outlier points ({removed_count/initial_count*100:.1f}%)")
        print(f"Data range after filtering:")
        print(f"  X: {df['x'].min():.2f} to {df['x'].max():.2f}")
        print(f"  Y: {df['y'].min():.2f} to {df['y'].max():.2f}")
    
    # Get unique line IDs
    line_ids = sorted(df['line_id'].unique())
    
    print(f"Plotting {len(line_ids)} lines spatially...")
    
    # Create color map
    colors = cm.tab20(np.linspace(0, 1, min(len(line_ids), 20)))
    if len(line_ids) > 20:
        # If more than 20 lines, cycle through colors
        colors = cm.tab20(np.linspace(0, 1, 20))
    
    fig, ax = plt.subplots(figsize=(18, 8))
    
    # Calculate the horizontal coordinate for all points
    if use_coordinate == 'x':
        df['horizontal'] = df['x']
        xlabel = 'Easting (km)'
    elif use_coordinate == 'y':
        df['horizontal'] = df['y']
        xlabel = 'Northing (km)'
    else:  # 'both' - calculate distance from min corner
        min_x, min_y = df['x'].min(), df['y'].min()
        df['horizontal'] = np.sqrt((df['x'] - min_x)**2 + (df['y'] - min_y)**2)
        xlabel = 'Distance from Origin (km)'
    
    # Plot each line
    for idx, line_id in enumerate(line_ids):
        line_data = df[df['line_id'] == line_id].copy()
        
        if len(line_data) < 2:
            continue
        
        # Sort by horizontal coordinate for cleaner lines
        line_data = line_data.sort_values('horizontal')
        
        # Convert to kilometers
        horizontal_km = line_data['horizontal'] / 1000
        depth_km = line_data['z'] / 1000
        
        # Use color cycling if more than 20 lines
        color_idx = idx % len(colors)
        
        # Plot this line
        ax.plot(horizontal_km, depth_km, 'o-', 
                color=colors[color_idx], 
                linewidth=1.5, 
                markersize=2,
                label=f'Line {line_id}' if idx < 30 else '',  # Limit legend entries
                alpha=0.7)
    
    # Overlay topography if provided
    if topo_file and topo_file.exists():
        try:
            from visualization.data_load import load_topography
            topo_x, topo_z = load_topography(topo_file)
            
            # Filter topography outliers
            if len(topo_x) > 0:
                topo_x_median = np.median(topo_x)
                topo_x_std = np.std(topo_x)
                valid_topo = np.abs(topo_x - topo_x_median) < 5 * topo_x_std
                topo_x = topo_x[valid_topo]
                topo_z = topo_z[valid_topo]
                
                print(f"Topography: {len(topo_x)} points, X range: {topo_x.min():.2f} to {topo_x.max():.2f}")
                
                # Check if topography coordinate system matches seismic data
                # Seismic data should be in meters (large values like 918680)
                # Topography might be in km starting from 0
                data_x_range = df['horizontal'].max() - df['horizontal'].min()
                topo_x_range = topo_x.max() - topo_x.min()
                
                # If topography range is much smaller and starts near 0, it's in different coordinates
                if topo_x.max() < df['horizontal'].min() * 0.5:
                    print("WARNING: Topography appears to be in different coordinate system - skipping overlay")
                    print(f"  Seismic data range: {df['horizontal'].min():.0f} to {df['horizontal'].max():.0f}")
                    print(f"  Topography range: {topo_x.min():.0f} to {topo_x.max():.0f}")
                    topo_horizontal = None
                else:
                    # Convert topography to same coordinate system
                    if use_coordinate == 'x':
                        topo_horizontal = topo_x
                    elif use_coordinate == 'y':
                        topo_horizontal = None
                    else:
                        topo_horizontal = topo_x
            else:
                topo_horizontal = None
            
            if topo_horizontal is not None and len(topo_horizontal) > 0:
                ax.plot(topo_horizontal / 1000, topo_z / 1000, 
                       color='black', linewidth=3, label='Topography', zorder=100)
        except Exception as e:
            print(f"Warning: Could not load topography: {e}")
    
    # Formatting
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Depth/Elevation (km)', fontsize=12)
    ax.set_title(f'All Seismic Lines - Spatial View (VE = {vertical_exaggeration:.1f}×)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Legend - only if not too many lines
    if len(line_ids) <= 30:
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=7, ncol=2)
    
    # Set aspect ratio for vertical exaggeration
    ax.set_aspect(vertical_exaggeration)
    
    # Invert y-axis so depth increases downward
    #ax.invert_yaxis()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    plt.show()
    
    return fig, ax


def analyze_line_orientation(df: pd.DataFrame):
    """
    Analyze the overall orientation of seismic lines.
    Helps determine which coordinate to use for plotting.
    """
    # Calculate ranges
    x_range = df['x'].max() - df['x'].min()
    y_range = df['y'].max() - df['y'].min()
    
    print("\nSpatial extent of data:")
    print(f"  X (Easting) range: {x_range/1000:.2f} km")
    print(f"  Y (Northing) range: {y_range/1000:.2f} km")
    print(f"  X bounds: {df['x'].min():.2f} to {df['x'].max():.2f}")
    print(f"  Y bounds: {df['y'].min():.2f} to {df['y'].max():.2f}")
    
    if x_range > y_range:
        print("\nRecommendation: Lines oriented mostly E-W, use 'x' coordinate")
        return 'x'
    else:
        print("\nRecommendation: Lines oriented mostly N-S, use 'y' coordinate")
        return 'y'