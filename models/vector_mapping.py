"""Look at vector plotter as an example of how to access the arrays
        You should match the topography points (topo_x, topo_z) to the end point of the vector (x2, z2), 
        and translate that corresponding topo point backwards (the beginning of the vector) try nearest neighbor algorithm.
        To start use topo_04.dat and v_03.dat, this will take us back 5 million years"""

import numpy as np
import matplotlib.pyplot as plt

def load_topo_points(filepath):
    topo_points = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or any(c.isalpha() for c in line):
                continue
            parts = line.split()
            if len(parts) == 2:
                x, z = map(float, parts)
                topo_points.append((x, z))
    return np.array(topo_points)

def load_vectors(filepath):
    vectors = []
    with open(filepath, 'r') as f:
        for line in f:
            fields = line.strip().split('\t')
            if len(fields) >= 7:
                x1, z1, x2, z2 = map(float, [fields[3], fields[4], fields[5], fields[6]])
                vectors.append((x1, z1, x2, z2))
    return np.array(vectors)

#vector mapping with green endpoints 
def map_topo_to_vectors(topo_points, vectors):
    mapped = []
    vec_endpoints = vectors[:, 2:4]  # (x2, z2)
    for topo_x, topo_z in topo_points:
        dists = np.linalg.norm(vec_endpoints - np.array([topo_x, topo_z]), axis=1)
        idx = np.argmin(dists)
        x1, z1, x2, z2 = vectors[idx]
        dx = x2 - x1
        dz = z2 - z1
        mapped_x = topo_x - dx
        mapped_z = topo_z - dz
        mapped.append({
            'topo': (topo_x, topo_z),
            'nearest_vector_idx': idx,
            'vector': (x1, z1, x2, z2),
            'mapped': (mapped_x, mapped_z)
        })
    return mapped

#vector mapping without vector endpoints
def plot_mapping(topo_points, vectors, mapping_results):
    # Plot original topography points
    topo_x, topo_z = topo_points[:, 0], topo_points[:, 1]
    plt.plot(topo_x, topo_z, c='blue', label='Topo Points')

    # Plot vector endpoints (x2, z2)
    vec_x2, vec_z2 = vectors[:, 2], vectors[:, 3]
    plt.scatter(vec_x2, vec_z2, c='green', marker='x', label='Vector Endpoints')

    # Plot mapped points (translated topo points)
    mapped_x = [m['mapped'][0] for m in mapping_results]
    mapped_z = [m['mapped'][1] for m in mapping_results]
    plt.plot(mapped_x, mapped_z, c='red', label='Mapped Points')

    plt.xlabel('X coordinate')
    plt.ylabel('Z coordinate')
    plt.title('Topography points, vector ends and mapped points')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_mapping_simple(topo_points, mapping_results):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16, 9))

    topo_x, topo_z = topo_points[:, 0], topo_points[:, 1]
    mapped_x = [m['mapped'][0] for m in mapping_results]
    mapped_z = [m['mapped'][1] for m in mapping_results]

    ax.plot(topo_x, topo_z, color='blue', label='Topo Points')
    ax.plot(mapped_x, mapped_z, color='red', label='Mapped Points')

    ax.set_xlabel('X coordinate')
    ax.set_ylabel('Z coordinate')
    ax.set_title('Topography points and mapped points (no vector endpoints)')
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    plt.show()

import matplotlib.pyplot as plt
import numpy as np

def simulate_topography_evolution(topo_file, vector_files, output_dir="frames"):
    import os
    from pathlib import Path
    Path(output_dir).mkdir(exist_ok=True)
    topo_points = load_topo_points(topo_file)
    current_points = topo_points.copy()
    frame_files = []
    for idx, vector_file in enumerate(vector_files):
        vectors = load_vectors(vector_file)
        mapped_results = map_topo_to_vectors(current_points, vectors)
        # Plot and save frame
        fig, ax = plt.subplots(figsize=(16, 9))
        ax.plot(current_points[:, 0], current_points[:, 1], color='blue', label='Start Points')
        mapped_x = [m['mapped'][0] for m in mapped_results]
        mapped_z = [m['mapped'][1] for m in mapped_results]
        ax.plot(mapped_x, mapped_z, color='red', label='Mapped Points')
        ax.set_xlabel('X coordinate')
        ax.set_ylabel('Z coordinate')
        ax.set_title(f'ma vector: {vector_file} ({["5-0","9-5","20-9","27-20"][idx]})')
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        framepath = f"{output_dir}/frame_{idx:02d}.png"
        fig.savefig(framepath)
        plt.close(fig)
        frame_files.append(framepath)
        # Update for next iteration
        current_points = np.column_stack([mapped_x, mapped_z])
    return frame_files




