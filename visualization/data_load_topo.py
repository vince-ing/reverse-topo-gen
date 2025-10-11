# visualization/data_load.py
import numpy as np
from pathlib import Path

def load_topography(filepath: str | Path):
    """
    Load a 2-column ASCII topography file (x, z).
    Ignores blank lines and text headers automatically.
    """
    filepath = Path(filepath)

    try:
        # Try using genfromtxt, which is more forgiving than loadtxt
        data = np.genfromtxt(
            filepath,
            comments="#",     # skip comment lines
            invalid_raise=False,
            usecols=(0, 1),   # read only first two columns
        )
    except Exception as e:
        raise IOError(f"Could not read file {filepath}: {e}")

    # Drop any rows that are entirely NaN
    data = data[~np.isnan(data).any(axis=1)]

    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"File {filepath} must have at least two numeric columns (x, z).")

    x, z = data[:, 0], data[:, 1]
    return x, z
