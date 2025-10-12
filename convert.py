#!/usr/bin/env python3
"""
Convert geological section files from easting/northing/elevation format
to x/z format that matches the topography coordinate system.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Mapping of section files to their corresponding topo files
SECTION_TO_TOPO = {
    "data/Sections/0MaMora1.dat": "data/Topo/topo_04.dat",
    "data/Sections/5MaMoraDecompact.dat": "data/Topo/topo_03.dat",
    "data/Sections/9MaMoraDecompact.dat": "data/Topo/topo_02.dat",
    "data/Sections/20MaMoraDecompact.dat": "data/Topo/topo_01.dat",
    "data/Sections/27MaMoraDecompact.dat": "data/Topo/topo_00.dat",
}

def load_topo_file(filepath):
    """Load a topo file and return x, z arrays."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    # Skip first line (header with single number)
    data = [list(map(float, line.split())) for line in lines[1:]]
    data = np.array(data)
    return data[:, 0], data[:, 1]

def load_section_file(filepath):
    """Load a section file in easting/northing/elevation format."""
    df = pd.read_csv(
        filepath,
        sep=r'\s+',
        header=None,
        names=['easting', 'northing', 'elevation', 'unit_name', 'unit_id', 'other1', 'other2', 'other3'],
        on_bad_lines='skip'
    )
    
    # Convert to numeric where needed
    df['easting'] = pd.to_numeric(df['easting'], errors='coerce')
    df['northing'] = pd.to_numeric(df['northing'], errors='coerce')
    df['elevation'] = pd.to_numeric(df['elevation'], errors='coerce')
    df.dropna(subset=['easting', 'northing', 'elevation'], inplace=True)
    
    return df

def convert_section_to_xz(section_df, topo_x, topo_z):
    """
    Convert section from easting/northing/elevation to x/z coordinates.
    
    Strategy:
    1. Calculate distance along profile from NW corner (like the profile does)
    2. Scale to match topo X range
    3. Convert elevation from meters to km
    """
    
    # Get the NW corner as origin (min easting, max northing)
    easting_origin = section_df['easting'].min()
    northing_origin = section_df['northing'].max()
    
    # Calculate distance from NW corner
    # Assuming profile runs roughly SE (easting increases, northing decreases)
    dx = section_df['easting'] - easting_origin
    dy = northing_origin - section_df['northing']  # Positive as we go SE
    
    # Distance along profile
    distance = np.sqrt(dx**2 + dy**2)
    
    # Scale distance to match topo X range
    # Topo starts at second point (skip artificial 0,0)
    topo_x_start = topo_x[1]
    topo_x_end = topo_x[-1]
    topo_x_range = topo_x_end - topo_x_start
    
    section_distance_range = distance.max() - distance.min()
    
    if section_distance_range > 0:
        # Normalize and scale
        x_normalized = (distance - distance.min()) / section_distance_range
        new_x = topo_x_start + (x_normalized * topo_x_range)
    else:
        new_x = np.full_like(distance, topo_x_start)
    
    # Convert elevation from meters to km (simple!)
    new_z = section_df['elevation'] / 1000.0
    
    # Create output dataframe
    output_df = pd.DataFrame({
        'x': new_x,
        'z': new_z,
        'unit_name': section_df['unit_name'],
        'unit_id': section_df['unit_id']
    })
    
    return output_df

def convert_all_sections():
    """Convert all section files to x/z format."""
    
    output_dir = Path("data/Sections_xz")
    output_dir.mkdir(exist_ok=True)
    
    print("="*60)
    print("CONVERTING GEOLOGICAL SECTIONS TO X/Z FORMAT")
    print("="*60)
    
    for section_file, topo_file in SECTION_TO_TOPO.items():
        section_path = Path(section_file)
        topo_path = Path(topo_file)
        
        if not section_path.exists():
            print(f"\n✗ Section file not found: {section_path}")
            continue
        
        if not topo_path.exists():
            print(f"\n✗ Topo file not found: {topo_path}")
            continue
        
        print(f"\n{'─'*60}")
        print(f"Processing: {section_path.name} → {topo_path.name}")
        print(f"{'─'*60}")
        
        # Load files
        print(f"  Loading section...")
        section_df = load_section_file(section_path)
        print(f"    {len(section_df)} points, {section_df['unit_id'].nunique()} units")
        print(f"    Easting: {section_df['easting'].min():.1f} to {section_df['easting'].max():.1f} m")
        print(f"    Northing: {section_df['northing'].min():.1f} to {section_df['northing'].max():.1f} m")
        print(f"    Elevation: {section_df['elevation'].min():.1f} to {section_df['elevation'].max():.1f} m")
        
        print(f"  Loading topo...")
        topo_x, topo_z = load_topo_file(topo_path)
        print(f"    {len(topo_x)} points")
        print(f"    X: {topo_x.min():.3f} to {topo_x.max():.3f} km")
        print(f"    Z: {topo_z.min():.3f} to {topo_z.max():.3f} km")
        print(f"    Profile starts at X = {topo_x[1]:.3f} km (skipping artificial first point)")
        
        # Convert
        print(f"  Converting coordinates...")
        converted_df = convert_section_to_xz(section_df, topo_x, topo_z)
        
        print(f"    Converted X: {converted_df['x'].min():.3f} to {converted_df['x'].max():.3f} km")
        print(f"    Converted Z: {converted_df['z'].min():.3f} to {converted_df['z'].max():.3f} km")
        
        # Save output
        output_path = output_dir / section_path.name
        converted_df.to_csv(output_path, sep='\t', index=False, header=False, float_format='%.4f')
        print(f"  ✓ Saved: {output_path}")
    
    print(f"\n{'='*60}")
    print(f"CONVERSION COMPLETE")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    convert_all_sections()