# models/erosion.py
"""
Contains functions related to climate-driven erosion processes.
"""

import numpy as np
import config

def calculate_climate_erosion_factor(x, z):
    """
    Calculates a spatially variable erosion factor based on topography
    slope and prevailing rain direction.

    Args:
        x (np.ndarray): The horizontal coordinates of the topography.
        z (np.ndarray): The vertical coordinates (elevation) of the topography.

    Returns:
        np.ndarray: An array of the same size as x and z, containing the
                    erosion multiplier for each point.
    """
    # Return a neutral factor if the feature is disabled
    if not config.enable_climate_erosion:
        return np.ones_like(x)

    # 1. Calculate the slope (gradient) of the topography
    slope = np.gradient(z, x)
    
    # 2. Define the rain vector based on the angle in the config
    angle_rad = np.deg2rad(config.rain_direction_angle)
    rain_vector = np.array([np.sin(angle_rad), -np.cos(angle_rad)])

    # 3. Calculate surface normal vectors for each point on the topography
    surface_normals = np.array([-slope, np.ones_like(slope)])
    
    # 4. Normalize the surface normal vectors
    norm = np.sqrt(surface_normals[0]**2 + surface_normals[1]**2)
    # Avoid division by zero on flat surfaces
    with np.errstate(divide='ignore', invalid='ignore'):
        surface_normals /= norm
        surface_normals[np.isnan(surface_normals)] = 0 # Set NaNs to 0
    
    # 5. Calculate the dot product between the rain vector and surface normals
    dot_product = np.dot(rain_vector, surface_normals)
    
    # 6. Create the erosion multiplier
    erosion_factor = np.full_like(dot_product, config.rain_intensity)
    erosion_factor[dot_product < 0] *= config.rain_shadow_effect
    
    return erosion_factor