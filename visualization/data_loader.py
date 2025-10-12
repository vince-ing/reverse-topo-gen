# data_loader.py
"""
Centralized data loading utilities.
Handles loading topography, vectors, and geological sections.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import config


def load_topography(filepath=None):
    """
    Loads topography data from a file.
    
    Args:
        filepath: Path to topography file. If None, uses config.modern_topo_file
    
    Returns:
        tuple: (x, z) arrays
    """
    if filepath is None:
        filepath = config.modern_topo_file
    
    filepath = Path(filepath)
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Skip header if present
    data = [list(map(float, line.split())) for line in lines[1:]]
    data = np.array(data)
    
    x, z = data[:, 0], data[:, 1]
    
    print(f"Loaded topography from {filepath}")
    print(f"  X range: {x.min():.2f} to {x.max():.2f} km")
    print(f"  Z range: {z.min():.2f} to {z.max():.2f} km")
    
    return x, z


def load_vectors(filepath):
    """
    Loads vector data from a file.
    
    Args:
        filepath: Path to vector file
    
    Returns:
        tuple: (x, dx, dz) arrays
    """
    data = pd.read_csv(filepath, sep=r'\s+', header=None, usecols=[3, 4, 5, 6], 
                       names=['x1', 'z1', 'x2', 'z2'], comment='B')
    data = data.drop_duplicates(subset='x1', keep='first')
    
    x = data['x1'].values
    dx = data['x2'].values - data['x1'].values
    dz = data['z2'].values - data['z1'].values
    
    return x, dx, dz


def load_geological_sections(section_dict=None):
    """
    Load geological sections from files.
    
    Args:
        section_dict: Dictionary of {age: filepath}. If None, uses config.geological_sections
    
    Returns:
        dict: {age: DataFrame} with columns ['x', 'z', 'unit_name', 'unit_id', 'age']
    """
    if section_dict is None:
        section_dict = config.geological_sections
    
    sections = {}
    
    print("\n=== Loading Geological Sections ===")
    for age, filepath in section_dict.items():
        try:
            filepath = Path(filepath)
            
            df = pd.read_csv(filepath, sep='\t', header=None,
                           names=['x', 'z', 'unit_name', 'unit_id'],
                           on_bad_lines='skip')
            
            df['x'] = pd.to_numeric(df['x'], errors='coerce')
            df['z'] = pd.to_numeric(df['z'], errors='coerce')
            df.dropna(subset=['x', 'z'], inplace=True)
            df['age'] = age
            
            df['unit_name'] = df['unit_name'].astype(str)
            df['unit_id'] = df['unit_id'].astype(str)
            
            sections[age] = df
            
            print(f"  ✓ Loaded {age} Ma: {len(df)} points, {df['unit_id'].nunique()} units")
            print(f"    X: {df['x'].min():.2f} to {df['x'].max():.2f} km")
            print(f"    Z: {df['z'].min():.2f} to {df['z'].max():.2f} km")
            
        except Exception as e:
            print(f"  ✗ Failed to load {filepath}: {e}")
    
    print(f"=== Loaded {len(sections)} sections total ===\n")
    return sections


def get_section_for_time(time_ma, sections):
    """
    Get the appropriate geological section to display for a given time.
    Returns the section with age closest to but not less than current time.
    
    Args:
        time_ma: Current time in Ma
        sections: Dictionary of {age: DataFrame}
    
    Returns:
        DataFrame or None: The appropriate section
    """
    if not sections:
        return None
    
    available_ages = sorted(sections.keys())
    
    best_age = available_ages[0]  # Default to youngest
    
    for age in available_ages:
        if time_ma >= age:
            best_age = age
        else:
            break
    
    return sections.get(best_age)


def load_all_vector_files(vector_dict=None, vector_dir=None):
    """
    Load all vector files specified in configuration.
    
    Args:
        vector_dict: Dictionary of {filename: duration_ma}. If None, uses config.vector_files
        vector_dir: Directory containing vector files. If None, uses config.vector_dir
    
    Returns:
        dict: {filename: {'x': array, 'dx': array, 'dz': array, 'duration': float}}
    """
    if vector_dict is None:
        vector_dict = config.vector_files
    if vector_dir is None:
        vector_dir = config.vector_dir
    
    vector_data = {}
    
    print("\n=== Loading Vector Files ===")
    for fname, duration in vector_dict.items():
        try:
            filepath = Path(vector_dir) / fname
            x, dx, dz = load_vectors(filepath)
            
            vector_data[fname] = {
                'x': x,
                'dx': dx,
                'dz': dz,
                'duration': duration
            }
            
            print(f"  ✓ Loaded {fname}: {len(x)} points, {duration} Ma duration")
            
        except Exception as e:
            print(f"  ✗ Failed to load {fname}: {e}")
    
    print(f"=== Loaded {len(vector_data)} vector files ===\n")
    return vector_data