# visualization/plotting.py
import matplotlib.pyplot as plt
import numpy as np

def plot_topography(
    x: np.ndarray,
    z: np.ndarray,
    title: str = "Topographic Profile",
    vertical_exaggeration: float = 1.0,
):
    """
    Plot a topographic profile with optional vertical exaggeration.
    
    Parameters
    ----------
    x : np.ndarray
        Horizontal distance (in meters)
    z : np.ndarray
        Elevation (in meters)
    title : str
        Plot title
    vertical_exaggeration : float
        How much to exaggerate vertical relief (e.g., 5 = 5× taller)
    """

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, z, color="sienna", lw=2)

    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Elevation (km)")
    ax.set_title(f"{title}  (VE = {vertical_exaggeration:.1f}×)")
    ax.grid(True, alpha=0.3)

    ax.set_aspect(vertical_exaggeration)

    plt.tight_layout()
    plt.show()

    
