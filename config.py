# config.py

# Visualization settings
vertical_exaggeration = 10.0

# ========================================
# Exponential Model Parameters
# ========================================

# Modern topography file (z_final)
modern_topo_file = "data/Topo/topo_04.dat"

# Time parameters
exp_t_initial = 27.0    # Start time in Ma (initial flat topography)
exp_t_final = 0.0       # End time in Ma (modern topography)

# Exponential growth parameter
exp_lambda_topo = 100.0  # Time constant in Ma
                        # Smaller values = rapid early growth, then plateau
                        # Larger values = more linear/uniform growth
                        # Try: 5, 10, 15, 20 to see different behaviors

# Initial topography elevation
exp_z_initial = 0.0     # Initial elevation in km (0 = sea level)
                        # Can also be negative (below sea level) or positive

# Animation settings
exp_num_frames = 27     # Number of frames (27 = one per million years)

# ========================================
# Notes:
# ========================================
# The exponential model uses: z(t) = z_initial + α(t)(z_final - z_initial)
# where α(t) = (1 - exp(-(t - t_initial)/λ)) / (1 - exp(-(t_final - t_initial)/λ))
#
# λ (lambda_topo) controls the shape:
#   - Small λ (e.g., 5): Fast initial growth → slow later
#   - Large λ (e.g., 20): Slow initial growth → fast later  
#   - λ ≈ (t_final - t_initial)/2: Approximately linear growth