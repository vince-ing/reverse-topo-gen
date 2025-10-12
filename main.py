# main.py
import pandas as pd
import imageio.v2 as imageio

from config import *
from models.vector_mapping import simulate_topography_evolution
from visualization.data_load import load_topography
from visualization.plotting import plot_topography
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
from models.interpolation_z import run_interpolation as run_z_interpolation
from models.exponential import run_exponential_model
from models.vector_z_model import run_vector_z_model
from models.hybrid import run_hybrid_model
from models.isostatic_model import run_isostatic_model
from models.diffusion_model import run_diffusion_model





def plot_simple_topography():
    """Original topography plotting function"""
    topo_file = Path("data/Topo/topo_04.dat")
    x, z = load_topography(topo_file)
    plot_topography(x, z, title=topo_file.name, vertical_exaggeration=1)

def plot_seismic_sections():
    """Plot seismic profile sections"""
    # Load the seismic data
    data_file = Path("data/Sections/0MaMora1.dat")
    
    print("Loading seismic data...")
    df = load_seismic_data(data_file)
    print(f"Loaded {len(df)} data points")
    
    # Show available lines
    print("\nAvailable line IDs:")
    line_summary = get_available_lines(df)
    print(line_summary.head(20))  # Show first 20 lines
    print(f"\nTotal lines: {len(line_summary)}")
    
    # Analyze spatial orientation
    recommended_coord = analyze_line_orientation(df)
    
    # Path to topography file for overlay
    topo_file = Path("data/Topo/topo_04.dat")
    
    # Create output directory if it doesn't exist
    output_dir = Path("visualization/output")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # OPTION 1: Plot all lines using actual spatial coordinates (DEFAULT)
    print("\nPlotting all lines using spatial coordinates...")
    plot_seismic_spatial(
        df=df,
        #topo_file=topo_file if topo_file.exists() else None,
        vertical_exaggeration=1.0,
        save_path=output_dir / "all_lines_spatial.png",
        use_coordinate='both',  # Use 'x', 'y', or 'both'
        #linewidth=1.0
    )
    
    # OPTION 2: Plot individual lines normalized (COMMENTED OUT)
    """
    line_to_plot = 12974
    print(f"\nPlotting line {line_to_plot}...")
    plot_seismic_profile(
        df=df,
        line_id=line_to_plot,
        topo_file=topo_file if topo_file.exists() else None,
        vertical_exaggeration=5.0,
        save_path=output_dir / f"profile_line_{line_to_plot}.png"
    )
    """
    
    print(f"\nDone! Figure saved to {output_dir}")

def plot_vector_data():
    """Plots vector data with a topographic overlay"""
    vector_file = Path("data/Vectors/v_03.dat")
    topo_file = Path("data/Topo/topo_04.dat")
    plot_vectors_and_topography(
        vector_file,
        topo_file,
        title="Vector Displacement with Topography",
        arrow_stride=15 # Lower number = more arrows
    )


def plot_comparison():
    """Loads seismic and topo data and plots them for comparison."""
    # 1. Define file paths
    seismic_file = Path("data/Sections/0MaMora1.dat")
    topo_file = Path("data/Topo/topo_04.dat")
    output_dir = Path("visualization/output")
    output_dir.mkdir(exist_ok=True, parents=True)

    # 2. Load the data from paths into DataFrames
    seismic_df = load_seismic_data(seismic_file)
    
    # load_topography returns x, z arrays, so we must create a DataFrame
    topo_x, topo_z = load_topography(topo_file)
    topo_df = pd.DataFrame({
        'x': topo_x,
        'z': topo_z,
        'line_id': 'topo_04'  # Add a line_id so the plotting function can find it
    })

    # 3. Call the plotting function with the loaded DataFrames <-- ADD THIS
    plot_topo_comparison(
        seismic_df=seismic_df,
        topo_df=topo_df,
        output_dir=output_dir
    )

def plot_full_warped_profile():
    """Loads all data and creates the final warped profile plot."""
    print("\n--- Generating Full Warped Seismic Section Plot ---")
    seismic_file = Path("data/Sections/0MaMora1.dat")
    topo_file = Path("data/Topo/topo_04.dat")
    output_dir = Path("visualization/output")
    output_dir.mkdir(exist_ok=True, parents=True)

    seismic_df = load_seismic_data(seismic_file)
    topo_x, topo_z = load_topography(topo_file)
    topo_df = pd.DataFrame({
        'x': topo_x,
        'z': topo_z,
        'line_id': 'topo_04'
    })
    
    # Call the new plotting function
    plot_warped_seismic_section(
        seismic_df=seismic_df,
        topo_df=topo_df,
        output_dir=output_dir
    )

def run_reconstruction():
    """
    Loads seismic, topography, and vector data, runs the palinspastic
    reconstruction on all layers, and plots the result.
    """
    print("\n--- Running Palinspastic Reconstruction ---")
    seismic_file = Path("data/Sections/0MaMora1.dat")
    vector_file = Path("data/Vectors/v_03.dat")
    topo_file = Path("data/Topo/topo_04.dat") # <-- Path to topo data
    output_dir = Path("visualization/output")
    output_dir.mkdir(exist_ok=True, parents=True)

    # 1. Load all data sources
    seismic_df = load_seismic_data(seismic_file)
    vectors = load_vectors(vector_file)
    
    # Load the reference topography and convert to a DataFrame
    topo_x, topo_z = load_topography(topo_file)
    topo_df = pd.DataFrame({'x': topo_x, 'z': topo_z})

    if seismic_df.empty or vectors.size == 0 or topo_df.empty:
        print("Could not load necessary data. Aborting reconstruction.")
        return

    # 2. Reconstruct both the seismic layers and the reference topography
    reconstructed_seismic_df = reconstruct_layers(seismic_df, vectors)
    reconstructed_topo_df = reconstruct_topography(topo_df, vectors)

    # 3. Plot the final results
    plot_reconstruction(
        original_df=seismic_df,
        reconstructed_df=reconstructed_seismic_df,
        reconstructed_topo_df=reconstructed_topo_df,
        output_dir=output_dir
    )
    

def main():
    """Main entry point - choose what to run"""
    
    print("=" * 60)
    print("Topography & Seismic Profile Visualization")
    print("=" * 60)

    #run_z_interpolation(create_animation=True)
    #run_vector_z_model(create_animation=True)
    #run_exponential_model(create_animation=True)
    #run_hybrid_model(create_animation=True)
    #run_isostatic_model(create_animation=True)
    run_diffusion_model(create_animation=True)
    
    # Choose what to run:
    # Option 1: Plot simple topography
    # plot_simple_topography()
    
    # Option 2: Plot seismic sections (DEFAULT)
    #  Call the plotting function with the loaded DataFrames
    #plot_comparison()
    #plot_seismic_sections()
    #plot_vector_data()
    #plot_full_warped_profile()
    #run_reconstruction()
    
    print("\nOptions:")
    print("  - To change coordinate system, edit use_coordinate in main.py")
    print("  - To plot a single line, uncomment OPTION 2 in plot_seismic_sections()")

    topo_file = "data/Topo/topo_04.dat"
    vectors_file = "data/Vectors/v_03.dat"
    vector_files = [
        "data/Vectors/v_03.dat",
        "data/Vectors/v_02.dat",
        "data/Vectors/v_01.dat",
        "data/Vectors/v_00.dat"
    ]

    topo_points = load_topo_points(topo_file)
    vectors = load_vectors(vectors_file)
    mapping_results = map_topo_to_vectors(topo_points, vectors)

    #plot_mapping(topo_points, vectors, mapping_results)
    #plot_mapping_simple(topo_points, mapping_results)

    frame_paths = simulate_topography_evolution(topo_file, vector_files)
    # (Optional: You can use imageio or OpenCV to combine frames into a GIF/video)

    # For GIF:
    images = [imageio.imread(fp) for fp in frame_paths]
    imageio.mimsave('topo_evolution.gif', images, duration=1)

if __name__ == "__main__":
    main()