# models/seismic_reconstruction.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.spatial import cKDTree
from matplotlib.lines import Line2D
import matplotlib.cm as cm

def load_vectors(filepath: Path) -> np.ndarray:
    """Loads displacement vectors from the specified file."""
    vectors = []
    with open(filepath, 'r') as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) >= 7:
                try:
                    # Fields are: (id, ?, ?, x1, z1, x2, z2)
                    x1, z1, x2, z2 = map(float, [fields[3], fields[4], fields[5], fields[6]])
                    vectors.append((x1, z1, x2, z2))
                except (ValueError, IndexError):
                    continue # Skip lines that cannot be parsed
    return np.array(vectors)

def reconstruct_layers(seismic_df: pd.DataFrame, vectors: np.ndarray) -> pd.DataFrame:
    """
    Applies a reverse vector mapping to all points in a seismic DataFrame.

    For each point in the seismic data, it finds the nearest vector endpoint (x2, z2)
    and translates the point backward by that vector's displacement (dx, dz).
    """
    if vectors.size == 0:
        print("Error: Vector data is empty. Cannot perform reconstruction.")
        return seismic_df

    print("Reconstructing layers using nearest-neighbor vector mapping...")
    
    # Use a KDTree for highly efficient nearest-neighbor searches
    vector_endpoints = vectors[:, 2:4] # Use (x2, z2) as the query points
    tree = cKDTree(vector_endpoints)

    # Get the coordinates of all points in the seismic data
    seismic_points = seismic_df[['x', 'z']].values

    # Query the tree to find the index of the nearest vector for each seismic point
    # This is extremely fast, even for millions of points.
    distances, indices = tree.query(seismic_points, k=1)

    # Get the full vector corresponding to each nearest endpoint
    matched_vectors = vectors[indices]

    # Calculate the displacement (dx, dz) for each matched vector
    dx = matched_vectors[:, 2] - matched_vectors[:, 0] # x2 - x1
    dz = matched_vectors[:, 3] - matched_vectors[:, 1] # z2 - z1

    # Create a new DataFrame with the reconstructed coordinates
    reconstructed_df = seismic_df.copy()
    reconstructed_df['x_recon'] = reconstructed_df['x'] - dx
    reconstructed_df['z_recon'] = reconstructed_df['z'] - dz
    
    print(f"Reconstruction complete. Processed {len(reconstructed_df)} points.")
    return reconstructed_df

def reconstruct_topography(topo_df: pd.DataFrame, vectors: np.ndarray) -> pd.DataFrame:
    """
    Applies reverse vector mapping to topography points, handling unit conversion.
    """
    if vectors.size == 0 or topo_df.empty:
        return pd.DataFrame()

    print("Reconstructing reference topography...")
    
    # Create a copy and convert topo data from km to meters for the calculation
    topo_m_df = topo_df.copy()
    topo_m_df['x'] *= 1000
    topo_m_df['z'] *= 1000

    vector_endpoints = vectors[:, 2:4] # (x2, z2) in meters
    tree = cKDTree(vector_endpoints)

    topo_points_m = topo_m_df[['x', 'z']].values
    distances, indices = tree.query(topo_points_m, k=1)
    
    matched_vectors = vectors[indices]
    dx = matched_vectors[:, 2] - matched_vectors[:, 0] # meters
    dz = matched_vectors[:, 3] - matched_vectors[:, 1] # meters

    reconstructed_topo_df = topo_m_df.copy()
    reconstructed_topo_df['x_recon'] = reconstructed_topo_df['x'] - dx
    reconstructed_topo_df['z_recon'] = reconstructed_topo_df['z'] - dz

    print("Topography reconstruction complete.")
    return reconstructed_topo_df

def plot_reconstruction(
    original_df: pd.DataFrame,
    reconstructed_df: pd.DataFrame,
    reconstructed_topo_df: pd.DataFrame,
    output_dir: Path
):
    """
    Plots the original topography, the reconstructed seismic layers, and the
    reconstructed topography (now a subsurface layer).
    """
    print("Generating reconstruction comparison plot...")
    original_df['distance_km'] = (original_df['x'] - original_df['x'].min()) / 1000
    reconstructed_df['distance_km'] = (reconstructed_df['x_recon'] - reconstructed_df['x_recon'].min()) / 1000

    plot_df = original_df[original_df['unit'].str.strip() != 'Topog'].copy()
    plot_df['unit_id'] = plot_df['unit'].str.strip().str.replace(r'\d+$', '', regex=True).fillna('Unknown')
    unique_units = sorted(plot_df['unit_id'].unique())
    colors = cm.get_cmap('tab20' if len(unique_units) <= 20 else 'viridis', len(unique_units))
    unit_to_color = {unit: colors(i) for i, unit in enumerate(unique_units)}

    fig, ax = plt.subplots(figsize=(18, 9))

    # Plot Reconstructed Seismic Layers (multi-colored)
    for line_id in sorted(reconstructed_df['line_id'].unique()):
        # ... (this loop is unchanged)
        orig_line_data = plot_df[plot_df['line_id'] == line_id]
        if orig_line_data.empty: continue
        recon_line_data = reconstructed_df[reconstructed_df['line_id'] == line_id].sort_values('distance_km')
        unit_id = orig_line_data['unit_id'].iloc[0]
        ax.plot(
            recon_line_data['distance_km'], recon_line_data['z_recon'] / 1000,
            color=unit_to_color[unit_id], linewidth=2, zorder=5
        )

    # Plot Reconstructed Topography (Red Line)
    if not reconstructed_topo_df.empty:
        # Normalize its horizontal axis and convert z from meters to km
        recon_topo = reconstructed_topo_df.sort_values('x_recon')
        recon_topo['distance_km'] = (recon_topo['x_recon'] - recon_topo['x_recon'].min()) / 1000
        ax.plot(
            recon_topo['distance_km'], recon_topo['z_recon'] / 1000,
            color='red', linewidth=2.5, zorder=10
        )

    # Plot Original Topography for reference (Dashed Black Line)
    topo_df = original_df[original_df['unit'].str.strip() == 'Topog'].copy()
    if not topo_df.empty:
        ax.plot(
            topo_df['distance_km'], topo_df['z'] / 1000,
            color='black', linestyle='--', linewidth=2.5, zorder=10
        )

    # Configure plot aesthetics
    ax.set_xlabel('Profile Distance (km)', fontsize=12)
    ax.set_ylabel('Elevation (km)', fontsize=12)
    ax.set_title('Translation Backwards through time', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_ylim(-30, 20)
    ax.set_aspect(1)

    # Create a combined legend
    dashed_line = Line2D([0], [0], color='black', linestyle='--', lw=2.5, label='Present-Day Topography')
    red_line = Line2D([0], [0], color='red', lw=2.5, label='Reconstructed (Past)')
    solid_line = Line2D([0], [0], color='gray', lw=2, label='Reconstructed Layers (Past)')
    ax.legend(handles=[dashed_line, red_line, solid_line], loc='lower left', fontsize='medium')

    save_path = output_dir / 'palinspastic_reconstruction.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Reconstruction plot saved to {save_path}")
    plt.show()