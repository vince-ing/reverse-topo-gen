# seismic_profile_plotter.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from .data_load import load_topography

def load_seismic_data(filepath: str | Path):
    """
    Load seismic interpretation data with X, Y, Z, unit, line_id columns.
    
    Returns
    -------
    pd.DataFrame with columns: x, y, z, unit, line_id (and optional extra params)
    """
    filepath = Path(filepath)
    
    # Read the file line by line to handle variable columns
    data_rows = []
    skipped_lines = 0
    
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue
            
            # Split on whitespace
            parts = line.split()
            
            # We need at least 5 columns: x, y, z, unit, line_id
            if len(parts) >= 5:
                try:
                    # Extract the first 5 essential columns
                    row = {
                        'x': float(parts[0]),
                        'y': float(parts[1]),
                        'z': float(parts[2]),
                        'unit': parts[3],
                        'line_id': int(parts[4])  # Must be integer
                    }
                    
                    # Add any extra parameters as optional columns
                    for i, val in enumerate(parts[5:], start=1):
                        try:
                            # Try to convert to float if it has a decimal point
                            if '.' in val:
                                row[f'param{i}'] = float(val)
                            else:
                                # Try integer, but keep as string if it fails
                                try:
                                    row[f'param{i}'] = int(val)
                                except ValueError:
                                    row[f'param{i}'] = val  # Keep as string
                        except ValueError:
                            row[f'param{i}'] = val  # Keep as string if conversion fails
                    
                    data_rows.append(row)
                    
                except ValueError as e:
                    # Skip lines where conversion fails (e.g., line_id is not a number)
                    skipped_lines += 1
                    if skipped_lines <= 5:  # Show first few skipped lines for debugging
                        print(f"Skipping line {line_num}: {line[:80]}...")
    
    # Convert to DataFrame
    df = pd.DataFrame(data_rows)
    
    if skipped_lines > 0:
        print(f"Skipped {skipped_lines} lines with invalid format")
    print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")
    
    return df

def calculate_profile_distance(df: pd.DataFrame):
    """
    Calculate cumulative distance along profile from X,Y coordinates.
    
    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'x' and 'y' columns
        
    Returns
    -------
    np.ndarray : cumulative distance in meters
    """
    # Calculate incremental distances between consecutive points
    dx = np.diff(df['x'].values, prepend=df['x'].iloc[0])
    dy = np.diff(df['y'].values, prepend=df['y'].iloc[0])
    
    # Pythagorean theorem for each segment
    incremental_dist = np.sqrt(dx**2 + dy**2)
    
    # Cumulative sum gives distance from start
    cumulative_dist = np.cumsum(incremental_dist)
    
    return cumulative_dist

def plot_seismic_profile(
    df: pd.DataFrame,
    line_id: int,
    topo_file: Path = None,
    vertical_exaggeration: float = 5.0,
    save_path: Path = None
):
    """
    Plot a 2D seismic profile for a specific line ID.
    
    Parameters
    ----------
    df : pd.DataFrame
        Full seismic dataset
    line_id : int
        Line ID to plot
    topo_file : Path, optional
        Path to topography file to overlay
    vertical_exaggeration : float
        Vertical exaggeration factor
    save_path : Path, optional
        If provided, save figure to this path
    """
    # Step 2: Filter by line ID
    line_data = df[df['line_id'] == line_id].copy()
    
    if len(line_data) == 0:
        raise ValueError(f"No data found for line_id = {line_id}")
    
    # Step 3: Calculate profile distance
    line_data['distance'] = calculate_profile_distance(line_data)
    
    # Convert to kilometers for plotting
    distance_km = line_data['distance'] / 1000
    depth_km = line_data['z'] / 1000
    
    # Step 4: Plot
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plot seismic profile
    ax.plot(distance_km, depth_km, 'o-', color='navy', 
            linewidth=2, markersize=4, label=f'Line {line_id}')
    
    # Overlay topography if provided
    if topo_file and topo_file.exists():
        try:
            topo_x, topo_z = load_topography(topo_file)
            ax.plot(topo_x / 1000, topo_z / 1000, 
                   color='sienna', linewidth=2.5, label='Topography')
        except Exception as e:
            print(f"Warning: Could not load topography: {e}")
    
    # Formatting
    ax.set_xlabel('Distance (km)', fontsize=12)
    ax.set_ylabel('Depth/Elevation (km)', fontsize=12)
    ax.set_title(f'Seismic Profile - Line {line_id} (VE = {vertical_exaggeration:.1f}×)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='best')
    
    # Set aspect ratio for vertical exaggeration
    ax.set_aspect(vertical_exaggeration)
    
    # Invert y-axis so depth increases downward
    ax.invert_yaxis()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    plt.show()
    
    return fig, ax

def get_available_lines(df: pd.DataFrame):
    """Get list of unique line IDs and their point counts."""
    line_summary = df.groupby('line_id').agg({
        'x': 'count',
        'unit': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    }).rename(columns={'x': 'n_points', 'unit': 'dominant_unit'})
    
    return line_summary

def plot_all_lines_overlay(
    df: pd.DataFrame,
    topo_file: Path = None,
    vertical_exaggeration: float = 5.0,
    save_path: Path = None,
    max_lines: int = None
):
    """
    Plot all seismic lines overlaid on a single plot.
    
    Parameters
    ----------
    df : pd.DataFrame
        Full seismic dataset
    topo_file : Path, optional
        Path to topography file to overlay
    vertical_exaggeration : float
        Vertical exaggeration factor
    save_path : Path, optional
        If provided, save figure to this path
    max_lines : int, optional
        Maximum number of lines to plot (None = all)
    """
    import matplotlib.cm as cm
    
    # Get unique line IDs
    line_ids = sorted(df['line_id'].unique())
    
    if max_lines:
        line_ids = line_ids[:max_lines]
    
    print(f"Plotting {len(line_ids)} lines...")
    
    # Create color map
    colors = cm.tab20(np.linspace(0, 1, len(line_ids)))
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Plot each line
    for idx, line_id in enumerate(line_ids):
        line_data = df[df['line_id'] == line_id].copy()
        
        if len(line_data) < 2:
            continue
        
        # Calculate profile distance for this line
        line_data['distance'] = calculate_profile_distance(line_data)
        
        # Convert to kilometers
        distance_km = line_data['distance'] / 1000
        depth_km = line_data['z'] / 1000
        
        # Plot this line
        ax.plot(distance_km, depth_km, 'o-', 
                color=colors[idx], 
                linewidth=1.5, 
                markersize=3,
                label=f'Line {line_id}',
                alpha=0.7)
    
    # Overlay topography if provided
    if topo_file and topo_file.exists():
        try:
            topo_x, topo_z = load_topography(topo_file)
            ax.plot(topo_x / 1000, topo_z / 1000, 
                   color='black', linewidth=3, label='Topography', zorder=100)
        except Exception as e:
            print(f"Warning: Could not load topography: {e}")
    
    # Formatting
    ax.set_xlabel('Distance Along Profile (km)', fontsize=12)
    ax.set_ylabel('Depth/Elevation (km)', fontsize=12)
    ax.set_title(f'All Seismic Lines Overlay (VE = {vertical_exaggeration:.1f}×)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Legend - put it outside the plot if many lines
    if len(line_ids) > 10:
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    else:
        ax.legend(loc='best', fontsize=9)
    
    # Set aspect ratio for vertical exaggeration
    ax.set_aspect(vertical_exaggeration)
    
    # Invert y-axis so depth increases downward
    ax.invert_yaxis()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    plt.show()
    
    return fig, ax

def main():
    # Step 1: Load the data
    data_file = Path("data/0MaMora1.dat")
    
    print("Loading seismic data...")
    df = load_seismic_data(data_file)
    print(f"Loaded {len(df)} data points")
    
    # Show available lines
    print("\nAvailable line IDs:")
    line_summary = get_available_lines(df)
    print(line_summary)
    
    # Example: Plot line 12974
    line_to_plot = 12974
    
    print(f"\nPlotting line {line_to_plot}...")
    
    # Path to topography file (optional)
    topo_file = Path("data/Topo/topo_04.dat")
    
    # Create the plot
    plot_seismic_profile(
        df=df,
        line_id=line_to_plot,
        topo_file=topo_file if topo_file.exists() else None,
        vertical_exaggeration=5.0,
        save_path=Path(f"output/profile_line_{line_to_plot}.png")
    )
    
    # You can also plot multiple lines
    print("\nTo plot other lines, change the line_to_plot variable.")
    print("Example line IDs from your data: 12961, 12974, 13006, 13032, 13056, 13059")

if __name__ == "__main__":
    main()