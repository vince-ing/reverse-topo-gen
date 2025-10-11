
import numpy as np
from pathlib import Path

def load_vectors(filepath: str | Path):
    filepath = Path(filepath)

    data = np.genfromtxt(
        filepath,
        delimiter=None,
        dtype=[
            ('Unit', 'U20'),
            ('ID1', 'U10'),
            ('ID2', 'U10'),
            ('xinitial', float),
            ('zinitial', float),
            ('x2', float),
            ('z2', float),
            ('density', float),
            ('thermal_conductivity', float),
            ('heat_capacity', float)
        ],
        encoding=None,
        comments='#',
        autostrip=True,
        names=False  # no header names in file
    )





