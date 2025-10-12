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

# ============================================================================
# MODEL SELECTION
# ============================================================================
ACTIVE_MODEL = 'isostatic'  # Options: 'exponential', etc.

# ============================================================================
# TIME PARAMETERS
# ============================================================================
t_initial = 27.0  # Ma (starting time - oldest)
t_final = 0.0     # Ma (ending time - modern)

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
hybrid_blend_factor = 0.7        # Time vs spatial weighting (0-1)

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
if plot_geological_sections == True:
    z_min_global = -25  # Minimum Z for plot (km)
    z_max_offset = 5.0  # Offset above max topography (km)
else:
    z_min_global = -2  # Minimum Z for plot (km)
    z_max_offset = 1.0  # Offset above max topography (km)


# ============================================================================
# OUTPUT SETTINGS
# ============================================================================
def get_frames_output_dir():
    """Get frames output directory based on active model."""
    return Path(f"frames_output_{ACTIVE_MODEL}")

def get_animation_output_file():
    """Get animation output filename based on active model."""
    return f"topo_evolution_{ACTIVE_MODEL}.gif"