# visualization/warped_profile_plotter.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.signal import find_peaks
from matplotlib.lines import Line2D
import matplotlib.cm as cm

def plot_warped_seismic_section(seismic_df: pd.DataFrame, topo_df: pd.DataFrame, output_dir: Path):
    """
    Calculates a dynamic warp based on the topography layers and applies it to
    the entire seismic dataset, plotting all layers with unique colors.
    """
    # 1. Prepare DataFrames and convert all units to kilometers
    seismic_topo_profile = seismic_df[seismic_df['unit'].str.strip() == 'Topog'].copy()
    seismic_topo_profile['z_km'] = seismic_topo_profile['z'] / 1000
    seismic_topo_profile['distance_km'] = (seismic_topo_profile['x'] - seismic_topo_profile['x'].min()) / 1000

    topo_04_df = topo_df[topo_df['line_id'] == 'topo_04'].copy()
    topo_04_df.rename(columns={'z': 'z_km'}, inplace=True)
    topo_04_df['distance_km'] = topo_04_df['x'] - topo_04_df['x'].min()

    if topo_04_df.empty or seismic_topo_profile.empty:
        print("Error: Could not find topography layers needed for warping.")
        return

    # 2. Find Peaks and Generate the Warp Mapping (from previous script)
    print("Finding prominent peaks to calculate warp...")
    peak_prominence = 0.25
    ref_peaks, ref_properties = find_peaks(topo_04_df['z_km'], prominence=peak_prominence)
    seismic_peaks, seismic_properties = find_peaks(seismic_topo_profile['z_km'], prominence=peak_prominence)

    num_peaks_to_match = min(len(ref_peaks), len(seismic_peaks))
    if num_peaks_to_match < 2:
        print(f"Error: Not enough peaks found ({num_peaks_to_match}). Cannot warp.")
        return

    ref_prominence_order = np.argsort(-ref_properties['prominences'])
    seismic_prominence_order = np.argsort(-seismic_properties['prominences'])
    top_ref_peaks = np.sort(ref_peaks[ref_prominence_order[:num_peaks_to_match]])
    top_seismic_peaks = np.sort(seismic_peaks[seismic_prominence_order[:num_peaks_to_match]])

    ref_peak_x = topo_04_df['distance_km'].iloc[top_ref_peaks].values
    seismic_peak_x = seismic_topo_profile['distance_km'].iloc[top_seismic_peaks].values

    seismic_lead_in = seismic_peak_x[0] - seismic_topo_profile['distance_km'].iloc[0]
    ref_start_anchor = ref_peak_x[0] - seismic_lead_in
    ref_end_anchor = ref_peak_x[-1] + (seismic_topo_profile['distance_km'].iloc[-1] - seismic_peak_x[-1])

    control_points_ref = np.concatenate(([ref_start_anchor], ref_peak_x, [ref_end_anchor]))
    control_points_seismic = np.concatenate(([seismic_topo_profile['distance_km'].iloc[0]], seismic_peak_x, [seismic_topo_profile['distance_km'].iloc[-1]]))
    
    # 3. Apply the Calculated Warp to the ENTIRE seismic dataset
    print("Applying warp to all seismic layers...")
    all_seismic_layers = seismic_df[seismic_df['unit'].str.strip() != 'Topog'].copy()
    all_seismic_layers['distance_km'] = (all_seismic_layers['x'] - all_seismic_layers['x'].min()) / 1000
    all_seismic_layers['distance_warped_km'] = np.interp(
        all_seismic_layers['distance_km'],
        control_points_seismic,
        control_points_ref
    )
    all_seismic_layers['z_km'] = all_seismic_layers['z'] / 1000

    # 4. Plot the Full, Warped Seismic Section
    # Group units and assign colors (from spatial_seismic_plotter.py)
    all_seismic_layers['unit_id'] = all_seismic_layers['unit'].str.strip().str.replace(r'\d+$', '', regex=True).fillna('Unknown')
    unique_units = sorted(all_seismic_layers['unit_id'].unique())
    colors = cm.get_cmap('tab20' if len(unique_units) <= 20 else 'viridis', len(unique_units))
    unit_to_color = {unit: colors(i) for i, unit in enumerate(unique_units)}

    fig, ax = plt.subplots(figsize=(18, 9))

    # Plot the reference profile first
    ax.plot(
        topo_04_df['distance_km'], topo_04_df['z_km'],
        label='Reference Profile (topo_04.dat)', color='black',
        linestyle='--', linewidth=2.0, zorder=100
    )

    # Plot all other warped seismic layers
    print(f"Plotting {all_seismic_layers['line_id'].nunique()} warped seismic lines...")
    for line_id in sorted(all_seismic_layers['line_id'].unique()):
        line_data = all_seismic_layers[all_seismic_layers['line_id'] == line_id].sort_values('distance_warped_km')
        if len(line_data) < 2: continue
        unit_id = line_data['unit_id'].iloc[0]
        ax.plot(
            line_data['distance_warped_km'], line_data['z_km'],
            color=unit_to_color[unit_id], linewidth=1
        )

    # 5. Create Legend and Finalize Plot
    ax.set_xlabel('Aligned Distance (km)', fontsize=12)
    ax.set_ylabel('Elevation (km)', fontsize=12)
    ax.set_title('Dynamically Warped Seismic Section', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_ylim(-30, 15)

    seismic_legend_elements = [Line2D([0], [0], color=color, lw=2, label=unit) for unit, color in unit_to_color.items()]
    ref_legend_elements = [Line2D([0], [0], color='black', linestyle='--', lw=2, label='Reference Topography')]
    
    # Place seismic legend on the side
    ncol = 3 if len(unique_units) > 40 else 2 if len(unique_units) > 20 else 1
    seismic_legend = ax.legend(handles=seismic_legend_elements, title="Seismic Units", bbox_to_anchor=(1.02, 1), loc='upper left', ncol=ncol, fontsize='small')
    ax.add_artist(seismic_legend)
    
    # Place reference legend inside the plot
    ax.legend(handles=ref_legend_elements, loc='lower left', fontsize='medium')

    ax.set_aspect(1.0)
    fig.subplots_adjust(right=0.75)
    save_path = output_dir / 'full_warped_seismic_section.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Full warped seismic section saved to {save_path}")
    
    plt.show()