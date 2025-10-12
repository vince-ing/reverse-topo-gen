# config.py
"""
Centralized configuration for landscape evolution models.
All user-configurable parameters should be defined here.
"""

from pathlib import Path

# ============================================================================
# ANIMATION SETTINGS
# ============================================================================
animation_fps = 5
vertical_exaggeration = 5
figure_size = (12, 7)
dpi = 100
reverse_animation = False # Set to True to build the GIF from last frame to first

# ============================================================================
# MODEL SELECTION
# ============================================================================
ACTIVE_MODEL = 'isostatic'  # Options: 'exponential', 'hyrbid' and 'isostatic'

# ============================================================================
# TIME PARAMETERS
# ============================================================================
t_initial = 27.0  # Ma (starting time - oldest)
t_final = 0.0     # Ma (ending time - modern)

# ============================================================================
# CLIMATE & EROSION SETTINGS
# ============================================================================
enable_climate_erosion = False       # The master switch for this feature
rain_direction_angle = -35.0        # Angle in degrees from vertical (-90 to 90)
rain_intensity = 2.5                # Climate factor (e.g., 0.0 to 2.0)
rain_shadow_effect = 0.1            # How much to reduce erosion in rain shadows (0-1)

# ============================================================================
# EXPONENTIAL MODEL PARAMETERS
# ============================================================================
exp_lambda_topo = 10.0  # Exponential decay constant (Ma)
exp_z_initial = 0.0     # Initial elevation at t_initial (km)

# ============================================================================
# HYBRID MODEL PARAMETERS
# ============================================================================
hybrid_z_initial = 0.0           # Initial elevation at t_initial (km)
hybrid_erosion_efficiency = 0.7  # Controls spatial pattern (0-1)
hybrid_blend_factor = 0.9        # Time vs spatial weighting (0-1)

# ============================================================================
# ISOSTATIC MODEL PARAMETERS
# ============================================================================
isostatic_z_initial = 0.0        # Initial elevation at t_initial (km)
isostatic_rho_crust = 2700       # Crustal density (kg/m³)
isostatic_rho_mantle = 3300      # Mantle density (kg/m³)
isostatic_blend_factor = 0.7     # Time vs spatial weighting (0-1)
isostatic_smoothing_window = 2   # Moving average window size for smoothing

# ============================================================================
# DATA PATHS
# ============================================================================
DATA_DIR = Path("data")

# Topography
modern_topo_file = DATA_DIR / "Topo" / "topo_04.dat"

# Geological Sections (age in Ma : filepath)
geological_sections = {
    0:  DATA_DIR / "Sections_xz" / "0MaMora1.dat",
    5:  DATA_DIR / "Sections_xz" / "5MaMoraDecompact.dat",
    9:  DATA_DIR / "Sections_xz" / "9MaMoraDecompact.dat",
    20: DATA_DIR / "Sections_xz" / "20MaMoraDecompact.dat",
    27: DATA_DIR / "Sections_xz" / "27MaMoraDecompact.dat"
}

# Vector files (filename : duration in Ma)
vector_files = {
    "v_00.dat": 5,
    "v_01.dat": 4,
    "v_02.dat": 11,
    "v_03.dat": 7,
}
vector_dir = DATA_DIR / "Vectors"

# ============================================================================
# VISUALIZATION OPTIONS
# ============================================================================
plot_geological_sections = False  # Set to False to disable section plotting
section_line_width = 1.5
section_alpha = 0.4
topo_line_width = 2
topo_color = 'black'
fill_color = 'lightgrey'
fill_alpha = 0.1

# Plot margins and limits
x_margin_fraction = 0.2  # Fraction of x-range to add as margin
y_axis_padding_top = 1.0    
y_axis_padding_bottom = 2.0

if plot_geological_sections == True:
    z_min_global = -25  # Minimum Z for plot (km)
    z_max_offset = 5.0  # Offset above max topography (km)
else:
    z_min_global = -2  # Minimum Z for plot (km)
    z_max_offset = 1.0  # Offset above max topography (km)

# ============================================================================
# COMPARISON GIF SETTINGS
# ============================================================================
# To use this, first generate the frames for two different model runs.
# Then, set the paths to those frame directories here and run comparison.py.
enable_comparison_gif = True
# Example path: "output/frames/isostatic/01"
comparison_source_dir_1 = "output/frames/isostatic/01"
comparison_source_dir_2 = "output/frames/isostatic/02" # A different run

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================
OUTPUT_BASE_DIR = Path("output")

def get_next_run_number(model_name, output_type='frames'):
    """
    Get the next sequential run number for a model.
    
    Args:
        model_name: Name of the model
        output_type: 'frames' or 'gifs'
    
    Returns:
        int: Next run number (1, 2, 3, ...)
    """
    if output_type == 'frames':
        base_path = OUTPUT_BASE_DIR / "frames" / model_name
    else:  # gifs
        base_path = OUTPUT_BASE_DIR / "gifs"
    
    base_path.mkdir(parents=True, exist_ok=True)
    
    if output_type == 'frames':
        # Count existing run directories
        existing = [d for d in base_path.iterdir() if d.is_dir() and d.name.isdigit()]
    else:  # gifs
        # Count existing gif files for this model
        existing = [f for f in base_path.iterdir() if f.name.startswith(f"{model_name}_") and f.suffix == '.gif']
    
    if not existing:
        return 1
    
    if output_type == 'frames':
        max_num = max(int(d.name) for d in existing)
    else:
        # Extract numbers from filenames like "exponential_01.gif"
        max_num = max(int(f.stem.split('_')[-1]) for f in existing)
    
    return max_num + 1

def get_frames_output_dir():
    """Get frames output directory based on active model with sequential numbering."""
    run_num = get_next_run_number(ACTIVE_MODEL, 'frames')
    return OUTPUT_BASE_DIR / "frames" / ACTIVE_MODEL / f"{run_num:02d}"

def get_animation_output_file():
    """Get animation output filename based on active model with sequential numbering."""
    run_num = get_next_run_number(ACTIVE_MODEL, 'gifs')
    return OUTPUT_BASE_DIR / "gifs" / f"{ACTIVE_MODEL}_{run_num:02d}.gif"