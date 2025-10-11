# spatial_seismic_plotter.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.lines import Line2D

def plot_seismic_spatial(
    df: pd.DataFrame,
    topo_file: Path = None,
    vertical_exaggeration: float = 5.0,
    save_path: Path = None,
    use_coordinate: str = 'x',  # 'x', 'y', or 'both'
    remove_outliers: bool = True,
    linewidth: float = 1.5 
):
    """
    Plot all seismic lines using actual spatial coordinates, colored by unit.
    
    Parameters
    ----------
    df : pd.DataFrame
        Full seismic dataset with x, y, z, unit, line_id columns
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
        x_q1, x_q99 = df['x'].quantile([0.01, 0.99])
        y_q1, y_q99 = df['y'].quantile([0.01, 0.99])
        
        print(f"Data range before filtering:")
        print(f"  X: {df['x'].min():.2f} to {df['x'].max():.2f}")
        print(f"  Y: {df['y'].min():.2f} to {df['y'].max():.2f}")
        
        x_range = x_q99 - x_q1
        y_range = y_q99 - y_q1
        x_min, x_max = x_q1 - 0.5*x_range, x_q99 + 0.5*x_range
        y_min, y_max = y_q1 - 0.5*y_range, y_q99 + 0.5*y_range
        
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

    # Use the 'unit' column directly for grouping and coloring.
    # The 'unit_id' column is now just a cleaned version of the 'unit' column.
    if 'unit' in df.columns:
        df['unit_id'] = df['unit'].str.strip().str.replace(r'\d+$', '', regex=True).fillna('Unknown')
    else:
        print("Warning: 'unit' column not found. Coloring all lines the same.")
        df['unit_id'] = 'Unknown'

    unique_units = sorted(df['unit_id'].unique())
    print(f"\nFound {len(unique_units)} unique seismic units after grouping: {unique_units}")

    # Create a color map for the units
    num_units = len(unique_units)
    # Use a perceptually distinct colormap
    colors = cm.get_cmap('tab20' if num_units <= 20 else 'jet', num_units)
    unit_to_color = {unit: colors(i) for i, unit in enumerate(unique_units)}
    
    line_ids = sorted(df['line_id'].unique())
    print(f"Plotting {len(line_ids)} lines from {num_units} units spatially...")
    
    fig, ax = plt.subplots(figsize=(18, 8))
    
    if use_coordinate == 'x':
        df['horizontal'] = df['x']
        xlabel = 'Easting (km)'
    elif use_coordinate == 'y':
        df['horizontal'] = df['y']
        xlabel = 'Northing (km)'
    else:
        min_x, min_y = df['x'].min(), df['y'].min()
        df['horizontal'] = np.sqrt((df['x'] - min_x)**2 + (df['y'] - min_y)**2)
        xlabel = 'Distance from Origin (km)'
    
    for line_id in line_ids:
        line_data = df[df['line_id'] == line_id].copy()
        
        if len(line_data) < 2:
            continue
        
        unit_id = line_data['unit_id'].iloc[0]
        line_data = line_data.sort_values('horizontal')
        horizontal_km = line_data['horizontal'] / 1000
        depth_km = line_data['z'] / 1000
        
        ax.plot(horizontal_km, depth_km, '-', 
                color=unit_to_color[unit_id],
                linewidth=linewidth, 
                markersize=2,
                alpha=0.7)
    
    if topo_file and topo_file.exists():
        try:
            # Assuming load_topography is in a sibling directory as per your structure
            from visualization.data_load import load_topography
            topo_x, topo_z = load_topography(topo_file)
            
            if len(topo_x) > 0:
                topo_x_median = np.median(topo_x)
                topo_x_std = np.std(topo_x)
                valid_topo = np.abs(topo_x - topo_x_median) < 5 * topo_x_std
                topo_x, topo_z = topo_x[valid_topo], topo_z[valid_topo]
                
                print(f"Topography: {len(topo_x)} points, X range: {topo_x.min():.2f} to {topo_x.max():.2f}")
                
                if topo_x.max() < df['horizontal'].min() * 0.5:
                    print("WARNING: Topography appears to be in different coordinate system - skipping overlay")
                    print(f"  Seismic data range: {df['horizontal'].min():.0f} to {df['horizontal'].max():.0f}")
                    print(f"  Topography range: {topo_x.min():.0f} to {topo_x.max():.0f}")
                    topo_horizontal = None
                else:
                    topo_horizontal = topo_x if use_coordinate != 'y' else None
            else:
                topo_horizontal = None
            
            if topo_horizontal is not None and len(topo_horizontal) > 0:
                ax.plot(topo_horizontal / 1000, topo_z / 1000, 
                       color='black', linewidth=3, label='Topography', zorder=100)
        except Exception as e:
            print(f"Warning: Could not load topography: {e}")
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Depth/Elevation (km)', fontsize=12)
    ax.set_title(f'All Seismic Lines by Unit - Spatial View (VE = {vertical_exaggeration:.1f}×)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    legend_elements = [
        Line2D([0], [0], color=color, lw=2, label=unit)
        for unit, color in unit_to_color.items()
    ]
    if any('Topography' in handle.get_label() for handle in ax.get_legend_handles_labels()[0]):
        legend_elements.append(Line2D([0], [0], color='black', lw=3, label='Topography'))

    if num_units > 40:
        ncol = 3
    elif num_units > 20:
        ncol = 2
    else:
        ncol = 1

    # Add the ncol and fontsize parameters to the legend call
    ax.legend(
        handles=legend_elements, 
        title="Seismic Units", 
        bbox_to_anchor=(1.02, 1), 
        loc='upper left',
        ncol=ncol,
        fontsize='small' # Use a smaller font for the legend
    )
    
    ax.set_aspect(vertical_exaggeration)
    fig.subplots_adjust(right=0.75)
    
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