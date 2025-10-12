# config.py

# Visualization settings
vertical_exaggeration = 10.0

# ========================================
# Exponential Model Parameters
# ========================================

# Modern topography file (z_final)
modern_topo_file = "data/Topo/topo_04.dat"

# Animation settings
animation_fps = 5.0  # Seconds per frame in GIF animations
                                # 0.5 = faster, 1.0 = moderate, 2.0 = slower

# Time parameters
exp_t_initial = 27.0    # Start time in Ma (initial flat topography)
exp_t_final = 0.0       # End time in Ma (modern topography)

# Exponential growth parameter
exp_lambda_topo = 100.0  # Time constant in Ma
                        # Smaller values = rapid early growth, then plateau
                        # Larger values = more linear/uniform growth
                        # Try: 5, 10, 15, 20 to see different behaviors

# Vector Z Model Parameters
vector_z_lambda = 20.0  # Time constant for vector-based Z scaling (Ma)

# Initial topography elevation
exp_z_initial = 0.0     # Initial elevation in km (0 = sea level)
                        # Can also be negative (below sea level) or positive

# Vector Z Model Parameters (erosion efficiency approach)
erosion_efficiency = 0.5  # Fraction of rock uplift that becomes topography (0-1)
                          # 0.5 = half the rock uplift is eroded away
                          # 0.7 = 70% becomes topography, 30% is eroded
                          # 1.0 = all rock uplift becomes topography (no erosion)

# Hybrid Model Parameters
hybrid_blend_factor = 0.7  # Blending between time-based (1.0) and spatial pattern (0.0)
                           # 0.9 = 90% time-based, more uniform decay (guaranteed flat at 27 Ma)
                           # 0.7 = 70% time-based, 30% spatial variation (balanced)
                           # 0.5 = 50/50 blend, more spatial heterogeneity
                           # Higher values = smoother, more guaranteed to reach flat
                           # Lower values = more spatial variation from vectors

# Isostatic Model Parameters
rho_crust = 2700   # Crustal density in kg/m³ (typical: 2600-2800)
rho_mantle = 3300  # Mantle density in kg/m³ (typical: 3200-3400)
# Isostatic efficiency = 1 - (rho_crust/rho_mantle) ≈ 0.18
# This means only ~18% of rock uplift becomes topographic relief
# The rest is compensated by isostatic rebound

# Diffusion Model Parameters
diffusion_kappa = 0.001         # Diffusivity in km²/Ma (typical: 0.01-1.0)
                               # Higher = faster smoothing
                               # Lower = preserves sharp features longer
diffusion_decay_factor = 0.05  # Linear decay toward baseline per Ma (0.01-0.1)
                               # Controls how fast topography flattens overall

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