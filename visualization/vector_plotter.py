# visualization/vector_plotter.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .data_load import load_topography

def load_vector_data(filepath: str | Path):
    """
    Load a multi-column ASCII vector file using pandas.
    Reads the unit name (col 0) and vector coordinates (cols 3, 4, 5, 6).
    """
    filepath = Path(filepath)
    
    try:
        # Use pandas to easily handle mixed text/numeric columns
        df = pd.read_csv(
            filepath,
            delim_whitespace=True,
            header=None,
            usecols=[0, 3, 4, 5, 6], # Read unit, x1, z1, x2, z2
            names=['unit', 'x1', 'z1', 'x2', 'z2']
        )
    except Exception as e:
        raise IOError(f"Could not read file {filepath}: {e}")

    return df

def plot_vectors_and_topography(
    vector_file: str | Path,
    topo_file: str | Path,
    title: str = "Vector Plot with Topography",
    vertical_exaggeration: float = 1.0,
    arrow_stride: int = 10,
):
    """
    Plots a subset of vectors colored by unit and a topographic profile.
    
    Parameters
    ----------
    arrow_stride : int
        Step to skip vectors. 1 plots all, 10 plots every 10th vector.
    """
    # Load the vector and topography data
    vector_df = load_vector_data(vector_file)
    topo_x, topo_z = load_topography(topo_file)

    fig, ax = plt.subplots(figsize=(15, 7))
    
    # --- Plot Vectors by Unit using ax.quiver() ---
    unique_units = vector_df['unit'].unique()
    colors = plt.cm.get_cmap('tab20', len(unique_units))
    
    for i, unit in enumerate(unique_units):
        unit_data = vector_df[vector_df['unit'] == unit].iloc[::arrow_stride]
        color = colors(i)
        
        # Calculate vector components (dx, dz)
        dx = unit_data['x2'] - unit_data['x1']
        dz = unit_data['z2'] - unit_data['z1']
        
        # Use quiver for efficient and correctly scaled vector plotting
        ax.quiver(
            unit_data['x1'], unit_data['z1'], dx, dz,
            color=color,
            label=unit,
            angles='xy',          # Arrow angle is calculated from dx, dz
            scale_units='xy',   # Scale arrows in data units
            scale=1,              # A scale of 1 means arrows are drawn to their true length
            width=0.002,          # Arrow width in figure units (consistent appearance)
            zorder=2
        )
            
    # Plot the topographic profile last and with a high zorder to ensure it's on top
    ax.plot(topo_x, topo_z, color="black", lw=2, label="Topography", zorder=10)

    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Elevation (km)")
    ax.set_title(f"{title}  (VE = {vertical_exaggeration:.1f}×) [1 of {arrow_stride} vectors shown]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_aspect(vertical_exaggeration)

    # Set plot limits to focus on the data
    ax.set_xlim(vector_df['x1'].min() - 1, vector_df['x2'].max() + 1)
    ax.set_ylim(vector_df[['z1', 'z2']].min().min() - 10, topo_z.max() + 10)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height]) # Shrink plot width
    ax.legend(
        loc='center left',
        bbox_to_anchor=(1, 0.5),
        ncol=2, # Adjust number of columns as needed
        fontsize='small'
    )
    plt.show()