import matplotlib.pyplot as plt
import numpy as np

def plot_vectors(data: np.ndarray, title: str = "Geological Vectors", vertical_exaggeration: float = 1.0):
    """
    Plot geological vector segments from numpy structured array.
    
    Parameters:
    - data: structured numpy array with fields 'unit', 'ID1', 'ID2', 'xinitial', 'zinitial', 'x2', 'z2', etc.
    - title: plot title
    - vertical_exaggeration: scale for z-values
    """
    plt.figure(figsize=(10, 6))
    
    # Extract unique units for color coding
    units = np.unique(data['unit'])
    cmap = plt.get_cmap('tab10', len(units))
    unit_to_color = {unit: cmap(i) for i, unit in enumerate(units)}
    
    for row in data:
        x_vals = [row['xinitial'], row['x2']]
        z_vals = [row['zinitial'], row['z2']]
        # Apply vertical exaggeration for depth
        z_vals = [val * vertical_exaggeration for val in z_vals]
        plt.plot(x_vals, z_vals, color=unit_to_color[row['unit']], label=row['unit'])
    
    # Avoid duplicate labels in the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), title="Unit")
    
    plt.xlabel("Horizontal (x)")
    plt.ylabel("Depth (z)")
    if title:
        plt.title(f"{title} (VE = {vertical_exaggeration:.1f}×)")
    plt.gca().invert_yaxis()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

