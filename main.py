# main.py
<<<<<<< HEAD
import pandas as pd
from models.interpolation import interpolate_surface, save_topography_gif

<<<<<<< Updated upstream
import imageio.v2 as imageio
=======
from config import *
from models.interpolation_z import run_interpolation_alpha_z
>>>>>>> Stashed changes
from models.vector_mapping import simulate_topography_evolution
from visualization.data_load import load_topography
from visualization.plotting import plot_topography
from models.alpha_z_evolution import run_alpha_z_evolution

from visualization.seismic_profile_plotter import (
    load_seismic_data,
    plot_seismic_profile,
    plot_all_lines_overlay,
    get_available_lines
)
from visualization.spatial_seismic_plotter import (
    plot_seismic_spatial,
    analyze_line_orientation
)
from visualization.vector_plotter import plot_vectors_and_topography
from visualization.seismic_topo import plot_topo_comparison
from visualization.warped_profile_plotter import plot_warped_seismic_section
from visualization.seismic_reconstruction import load_vectors, reconstruct_layers, reconstruct_topography, plot_reconstruction
from pathlib import Path
from models.vector_mapping import (
    load_topo_points,
    load_vectors,
    map_topo_to_vectors,
    plot_mapping, 
    plot_mapping_simple
)
<<<<<<< Updated upstream
def run_topography_interpolation_and_gif():
    topo_file = Path("data/Topo/topo_04.dat")
    x_init, z_init = load_topography(topo_file)

    vector_files = [
        "data/Vectors/v_03.dat",
        "data/Vectors/v_02.dat",
        "data/Vectors/v_01.dat",
        "data/Vectors/v_00.dat"
    ]

    vector_x_list = []
    vector_z_list = []
    vector_x_coords_list = []

    for vf in vector_files:
        # Assumes load_vectors returns array with columns: x_coord, dx, dz
        v = load_vectors(vf)
        if v.shape[1] < 3:
            raise ValueError(f"Vector file {vf} should contain at least 3 columns: x_coord, dx, dz")

        vector_x_coords_list.append(v[:, 0])  # Vector point x coords
        vector_x_list.append(v[:, 1])         # dx displacement
        vector_z_list.append(v[:, 2])         # dz displacement

        # Optional debug print
        print(f"Loaded {vf} with vector points: {len(v[:,0])}")

    time_stamps = [0, 5, 9, 20, 27]
    desired_times = [0, 2, 5, 7, 9, 12, 16, 20, 23, 27]

    surfaces = interpolate_surface(
        x_init, z_init,
        vector_x_list, vector_z_list,
        vector_x_coords_list,
        time_stamps,
        desired_times,
        lambda_topo=10.0
    )

    xlim = (min(x_init), max(x_init))
    zlim = (min(z_init) - 10, max(z_init) + 10)
    # In main.py

    save_topography_gif(
        surfaces,
        filename='interpolated_topography.gif',
        xlim=xlim,
        ylim=zlim,
        figsize=(8, 8),
        duration=0.7
    )
    print("Saved interpolated topo animation to interpolated_topography.gif")


=======
from models.interpolation_z import run_interpolation_alpha_z
from models.exponential import run_exponential_model
>>>>>>> Stashed changes
=======
"""
Main entry point for landscape evolution models.
"""

import config
>>>>>>> 4ae2c049122fb9355a7f9f3d990475223247da68


def main():
<<<<<<< HEAD
    """Main entry point - choose what to run"""

<<<<<<< Updated upstream
    ##topography interpolation gif 
    run_topography_interpolation_and_gif()
    
    # print("=" * 60)
    # print("Topography & Seismic Profile Visualization")
    # print("=" * 60)
=======
    print("=" * 60)
    print("Topography & Seismic Profile Visualization")
    print("=" * 60)

    #run_z_interpolation(create_animation=True)
    run_alpha_z_evolution(create_animation=True)

>>>>>>> Stashed changes
    
    # # Choose what to run:
    # # Option 1: Plot simple topography
    # # plot_simple_topography()
    
    # # Option 2: Plot seismic sections (DEFAULT)
    # #  Call the plotting function with the loaded DataFrames
    # #plot_comparison()
    # #plot_seismic_sections()
    # plot_vector_data()
    # #plot_full_warped_profile()
    # run_reconstruction()
    
    # print("\nOptions:")
    # print("  - To change coordinate system, edit use_coordinate in main.py")
    # print("  - To plot a single line, uncomment OPTION 2 in plot_seismic_sections()")

    # topo_file = "data/Topo/topo_04.dat"
    # vectors_file = "data/Vectors/v_03.dat"
    # vector_files = [
    #     "data/Vectors/v_03.dat",
    #     "data/Vectors/v_02.dat",
    #     "data/Vectors/v_01.dat",
    #     "data/Vectors/v_00.dat"
    # ]

    # topo_points = load_topo_points(topo_file)
    # vectors = load_vectors(vectors_file)
    # mapping_results = map_topo_to_vectors(topo_points, vectors)

    # plot_mapping(topo_points, vectors, mapping_results)
    # plot_mapping_simple(topo_points, mapping_results)

    # frame_paths = simulate_topography_evolution(topo_file, vector_files)
    # # (Optional: You can use imageio or OpenCV to combine frames into a GIF/video)

    # # For GIF:
    # images = [imageio.imread(fp) for fp in frame_paths]
    # imageio.mimsave('topo_evolution.gif', images, duration=1)

<<<<<<< Updated upstream

=======
    # For GIF:
    images = [imageio.imread(fp) for fp in frame_paths]
    imageio.mimsave('topo_evolution.gif', images, duration=1)
    
>>>>>>> Stashed changes
=======
    """
    Main function to run the selected landscape evolution model.
    Model selection is controlled by config.ACTIVE_MODEL
    """
    
    print(f"\n{'='*60}")
    print(f"LANDSCAPE EVOLUTION MODEL RUNNER")
    print(f"{'='*60}")
    print(f"Active model: {config.ACTIVE_MODEL}")
    print(f"Geological sections: {'Enabled' if config.plot_geological_sections else 'Disabled'}")
    print(f"Animation FPS: {config.animation_fps}")
    print(f"Vertical exaggeration: {config.vertical_exaggeration}x")
    print(f"{'='*60}\n")
    
    # Import and run the appropriate model
    if config.ACTIVE_MODEL == 'exponential':
        from models.exponential import run_exponential_model
        run_exponential_model(create_animation=True)
    elif config.ACTIVE_MODEL == 'hybrid':
        from models.hybrid import run_hybrid_model
        run_hybrid_model(create_animation=True)
    elif config.ACTIVE_MODEL == 'isostatic':
        from models.isostatic import run_isostatic_model
        run_isostatic_model(create_animation=True)
    else:
        print(f"ERROR: Unknown model '{config.ACTIVE_MODEL}'")
        print(f"Available models: exponential, hybrid, isostatic")
        return
    
    print("\nModel run complete!")


>>>>>>> 4ae2c049122fb9355a7f9f3d990475223247da68
if __name__ == "__main__":
    main()