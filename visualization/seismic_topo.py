# visualization/seismic_topo.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.signal import find_peaks

def plot_topo_comparison(seismic_df: pd.DataFrame, topo_df: pd.DataFrame, output_dir: Path):
    """
    Finds corresponding peaks in both profiles and dynamically warps the seismic
    data for the most accurate alignment, ignoring artificial flat areas.
    """
    # 1. Prepare DataFrames and convert all units to kilometers
    seismic_topo_profile = seismic_df[seismic_df['unit'].str.strip() == 'Topog'].copy()
    seismic_topo_profile['z_km'] = seismic_topo_profile['z'] / 1000
    seismic_topo_profile['distance_km'] = (seismic_topo_profile['x'] - seismic_topo_profile['x'].min()) / 1000

    topo_04_df = topo_df[topo_df['line_id'] == 'topo_04'].copy()
    topo_04_df.rename(columns={'z': 'z_km'}, inplace=True)
    topo_04_df['distance_km'] = topo_04_df['x'] - topo_04_df['x'].min()

    if topo_04_df.empty or seismic_topo_profile.empty:
        print("Error: Could not find necessary topography data to plot.")
        return

    # 2. Find Prominent Peaks in Both Profiles
    print("Finding prominent peaks to use as control points...")
    peak_prominence = 0.25 # In km. A higher value finds only more major peaks.

    ref_peaks, ref_properties = find_peaks(topo_04_df['z_km'], prominence=peak_prominence)
    seismic_peaks, seismic_properties = find_peaks(seismic_topo_profile['z_km'], prominence=peak_prominence)

    num_peaks_to_match = min(len(ref_peaks), len(seismic_peaks))
    if num_peaks_to_match < 2:
        print(f"Error: Not enough prominent peaks found ({num_peaks_to_match}). Try lowering 'peak_prominence'.")
        return

    ref_prominence_order = np.argsort(-ref_properties['prominences'])
    seismic_prominence_order = np.argsort(-seismic_properties['prominences'])
    top_ref_peaks = np.sort(ref_peaks[ref_prominence_order[:num_peaks_to_match]])
    top_seismic_peaks = np.sort(seismic_peaks[seismic_prominence_order[:num_peaks_to_match]])
    
    # Get the x-coordinates (distance_km) of these final control point peaks
    ref_peak_x = topo_04_df['distance_km'].iloc[top_ref_peaks].values
    seismic_peak_x = seismic_topo_profile['distance_km'].iloc[top_seismic_peaks].values

    # ===================================================================
    # 3. NEW: Anchor the warp based on first/last peaks, not file start/end
    # ===================================================================
    # This preserves the shape of the seismic data before its first peak and after its last peak.
    seismic_lead_in = seismic_peak_x[0] - seismic_topo_profile['distance_km'].iloc[0]
    seismic_lead_out = seismic_topo_profile['distance_km'].iloc[-1] - seismic_peak_x[-1]

    # Define the new reference anchors based on the seismic profile's shape
    ref_start_anchor = ref_peak_x[0] - seismic_lead_in
    ref_end_anchor = ref_peak_x[-1] + seismic_lead_out

    # Create the control point sets for interpolation
    control_points_ref = np.concatenate(([ref_start_anchor], ref_peak_x, [ref_end_anchor]))
    control_points_seismic = np.concatenate(([seismic_topo_profile['distance_km'].iloc[0]], seismic_peak_x, [seismic_topo_profile['distance_km'].iloc[-1]]))
    
    print(f"Matched {len(control_points_ref)} control points. Warping seismic profile...")
    # ===================================================================

    # 4. Warp the Seismic X-Axis Using the Control Points
    seismic_topo_profile['distance_warped_km'] = np.interp(
        seismic_topo_profile['distance_km'],
        control_points_seismic,
        control_points_ref
    )
    
    # 5. Create the Final Plot
    fig, ax = plt.subplots(figsize=(18, 8))

    ax.plot(
        topo_04_df['distance_km'], topo_04_df['z_km'],
        label='Reference Profile (topo_04.dat)',
        color='black', linestyle='--', linewidth=2.5
    )
    ax.plot(
        seismic_topo_profile['distance_warped_km'], seismic_topo_profile['z_km'],
        label='Warped Seismic Profile (0MaMora1 Topog)',
        color='red', linewidth=2
    )

    ax.set_xlabel('Aligned Distance (km)', fontsize=12)
    ax.set_ylabel('Elevation (km)', fontsize=12)
    ax.set_title('Dynamically Warped Comparison of Seismic vs. Reference Topography', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.6)
    
    save_path = output_dir / 'warped_aligned_topo_comparison.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Final warped and aligned plot saved to {save_path}")
    
    plt.show()