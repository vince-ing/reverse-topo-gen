# spatial_seismic_plotter.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.lines import Line2D

# spatial_seismic_plotter.py

def plot_seismic_spatial(
    df: pd.DataFrame,
    vertical_exaggeration: float = 5.0,
    save_path: Path = None,
    use_coordinate: str = 'x',
    remove_outliers: bool = True,
    linewidth: float = 1.0
):
    """
    Plot all seismic lines using actual spatial coordinates, colored by grouped unit.

    The 'Topog' unit is treated as a special reference layer, plotted on top
    with its own legend.

    Parameters
    ----------
    df : pd.DataFrame
        Full seismic dataset with x, y, z, unit, and line_id columns.
    vertical_exaggeration : float
        Vertical exaggeration factor.
    save_path : Path, optional
        If provided, save figure to this path.
    use_coordinate : str
        Which coordinate to use for horizontal axis: 'x', 'y', or 'both'.
    remove_outliers : bool
        If True, remove spatial outliers that are far from the main data cluster.
    linewidth : float
        Thickness of the seismic lines on the plot.
    """
    import matplotlib.cm as cm

    # (Code for outlier removal is unchanged)
    if remove_outliers:
        x_q1, x_q99 = df['x'].quantile([0.01, 0.99])
        y_q1, y_q99 = df['y'].quantile([0.01, 0.99])
        print(f"Data range before filtering:\n  X: {df['x'].min():.2f} to {df['x'].max():.2f}\n  Y: {df['y'].min():.2f} to {df['y'].max():.2f}")
        x_range, y_range = x_q99 - x_q1, y_q99 - y_q1
        x_min, x_max = x_q1 - 0.5 * x_range, x_q99 + 0.5 * x_range
        y_min, y_max = y_q1 - 0.5 * y_range, y_q99 + 0.5 * y_range
        initial_count = len(df)
        df = df[(df['x'] >= x_min) & (df['x'] <= x_max) & (df['y'] >= y_min) & (df['y'] <= y_max)].copy()
        removed_count = initial_count - len(df)
        print(f"Removed {removed_count} outlier points ({removed_count / initial_count * 100:.1f}%)")
        print(f"Data range after filtering:\n  X: {df['x'].min():.2f} to {df['x'].max():.2f}\n  Y: {df['y'].min():.2f} to {df['y'].max():.2f}")

    # (Code for grouping units is unchanged)
    if 'unit' in df.columns:
        df['unit_id'] = df['unit'].str.strip().str.replace(r'\d+$', '', regex=True).fillna('Unknown')
    else:
        df['unit_id'] = 'Unknown'

    # --- START OF FIX ---
    # 1. CALCULATE HORIZONTAL COORDINATE FIRST
    # This ensures the 'horizontal' column exists before we split the DataFrame.
    if use_coordinate == 'x':
        df['horizontal'] = df['x']
        xlabel = 'Easting (km)'
    elif use_coordinate == 'y':
        df['horizontal'] = df['y']
        xlabel = 'Northing (km)'
    else:  # 'both'
        min_x, min_y = df['x'].min(), df['y'].min()
        df['horizontal'] = np.sqrt((df['x'] - min_x)**2 + (df['y'] - min_y)**2)
        xlabel = 'Distance from Origin (km)'

    # 2. NOW, SPLIT THE DATAFRAME
    # The copies will correctly contain the 'horizontal' column.
    topog_unit_df = df[df['unit_id'] == 'Topog'].copy()
    seismic_df = df[df['unit_id'] != 'Topog'].copy()
    # --- END OF FIX ---

    unique_units = sorted(seismic_df['unit_id'].unique())
    print(f"\nFound {len(unique_units)} unique seismic units after grouping: {unique_units}")
    if not topog_unit_df.empty:
        print("Found special unit: 'Topog'")

    # (Code for color map and figure creation is unchanged)
    num_units = len(unique_units)
    colors = cm.get_cmap('tab20' if num_units <= 20 else 'viridis', num_units)
    unit_to_color = {unit: colors(i) for i, unit in enumerate(unique_units)}
    fig, ax = plt.subplots(figsize=(18, 8))

    # (The rest of the plotting and legend code is correct and unchanged)
    print(f"Plotting {seismic_df['line_id'].nunique()} lines from {num_units} units spatially...")
    for line_id in sorted(seismic_df['line_id'].unique()):
        line_data = seismic_df[seismic_df['line_id'] == line_id].copy()
        if len(line_data) < 2: continue
        unit_id = line_data['unit_id'].iloc[0]
        line_data = line_data.sort_values('horizontal') # This will now work
        horizontal_km, depth_km = line_data['horizontal'] / 1000, line_data['z'] / 1000
        ax.plot(horizontal_km, depth_km, '-', color=unit_to_color[unit_id], linewidth=linewidth, alpha=0.7, zorder=2)

    if not topog_unit_df.empty:
        print(f"Plotting {topog_unit_df['line_id'].nunique()} 'Topog' lines...")
        for line_id in sorted(topog_unit_df['line_id'].unique()):
            line_data = topog_unit_df[topog_unit_df['line_id'] == line_id].copy()
            if len(line_data) < 2: continue
            line_data = line_data.sort_values('horizontal') # This will now work
            horizontal_km, depth_km = line_data['horizontal'] / 1000, line_data['z'] / 1000
            ax.plot(horizontal_km, depth_km, '-', color='saddlebrown', linewidth=linewidth + 0.5, zorder=10)

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Depth/Elevation (km)', fontsize=12)
    ax.set_title(f'Unit Boundaries - Spatial View (VE = {vertical_exaggeration:.1f}×)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    seismic_legend_elements = [Line2D([0], [0], color=color, lw=2, label=unit) for unit, color in unit_to_color.items()]
    ncol = 3 if num_units > 40 else 2 if num_units > 20 else 1
    seismic_legend = ax.legend(handles=seismic_legend_elements, title="Seismic Units", bbox_to_anchor=(1.02, 1), loc='upper left', ncol=ncol, fontsize='small')
    ax.add_artist(seismic_legend)

    if not topog_unit_df.empty:
        special_legend_elements = [Line2D([0], [0], color='saddlebrown', lw=2, label='Topography')]
        ax.legend(
            handles=special_legend_elements,
            title="Reference Layers",
            bbox_to_anchor=(1.02, 1.5),  
            loc='upper left',           
            fontsize='small'
        )

    ax.set_aspect(vertical_exaggeration)
    fig.subplots_adjust(right=0.70)

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
    x_range = df['x'].max() - df['x'].min()
    y_range = df['y'].max() - df['y'].min()
    
    print("\nSpatial extent of data:")
    print(f"  X (Easting) range: {x_range / 1000:.2f} km")
    print(f"  Y (Northing) range: {y_range / 1000:.2f} km")
    print(f"  X bounds: {df['x'].min():.2f} to {df['x'].max():.2f}")
    print(f"  Y bounds: {df['y'].min():.2f} to {df['y'].max():.2f}")
    
    if x_range > y_range:
        print("\nRecommendation: Lines oriented mostly E-W, use 'x' coordinate")
        return 'x'
    else:
        print("\nRecommendation: Lines oriented mostly N-S, use 'y' coordinate")
        return 'y'