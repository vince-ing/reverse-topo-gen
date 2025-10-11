# visualization/data_load.py
import numpy as np
import pandas as pd
from pathlib import Path

def load_topography(file_path: Path) -> (np.ndarray, np.ndarray):
    """
    Loads a two-column topography file using pandas for robustness,
    skipping the header row.
    """
    try:
        # Using sep='\s+' is the modern, more reliable way to handle
        # space-separated values.
        topo_df = pd.read_csv(
            file_path,
            sep='\s+',              # Use the recommended separator
            skiprows=1,             # Skips the text header row
            header=None,            # No header row to read
            names=['x', 'z'],       # Assign column names
            engine='python'         # Use the more robust Python parsing engine
        )
        
        # Add a print statement for debugging
        print(f"--- Topo Loading: Loaded {topo_df.shape[0]} points from {file_path.name} ---")

        if topo_df.empty:
            print(f"Warning: No data loaded from topography file '{file_path.name}'.")
            return np.array([]), np.array([])

        return topo_df['x'].to_numpy(), topo_df['z'].to_numpy()

    except Exception as e:
        print(f"Error loading topography file {file_path}: {e}")
        return np.array([]), np.array([])