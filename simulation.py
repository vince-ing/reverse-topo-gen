# simulation.py
import config
import queue

# Import the main functions from your existing model files
from models.isostatic import run_isostatic_model
from models.exponential import run_exponential_model
from models.hybrid import run_hybrid_model

def run_simulation(params, output_file_path, result_queue):
    """
    Acts as a bridge between the GUI and the scientific models.

    This function:
    1. Takes parameters and an output path from the GUI.
    2. Overwrites settings in the global `config` file with the GUI settings.
    3. Selects and runs the appropriate model based on `params['model']`.
    4. Puts the result path in the queue for the GUI to retrieve.
    
    Args:
        params: Dictionary of simulation parameters from GUI
        output_file_path: Path where GIF should be saved (already determined by GUI)
        result_queue: Queue to communicate results back to GUI
    """
    print("--- Simulation Bridge Activated ---")
    print(f"Expected output file: {output_file_path}")
    
    # --- Step A: Update the global config with GUI parameters ---
    print("Updating config from GUI parameters...")
    config.ACTIVE_MODEL = params['model']
    config.animation_fps = params['fps']
    config.reverse_animation = params['reverse_animation']
    config.vertical_exaggeration = params['vertical_exaggeration']  # NEW
    
    # Update model-specific parameters in config
    if params['model'] == 'isostatic':
        config.isostatic_blend_factor = params['isostatic_blend_factor']
        config.isostatic_smoothing_window = params['isostatic_smoothing_window']
        config.isostatic_rho_crust = params['isostatic_rho_crust']
        config.isostatic_rho_mantle = params['isostatic_rho_mantle']
    elif params['model'] == 'exponential':
        config.exp_lambda_topo = params['exp_lambda_topo']
        config.exp_z_initial = params['exp_z_initial']
    elif params['model'] == 'hybrid':
        config.hybrid_z_initial = params['hybrid_z_initial']
        config.hybrid_erosion_efficiency = params['hybrid_erosion_efficiency']
        config.hybrid_blend_factor = params['hybrid_blend_factor']
    
    # --- Step B: Select and run the correct model ---
    model_name = params['model']
    print(f"Model selected: {model_name}")

    try:
        # Run the selected model with animation enabled
        if model_name == 'isostatic':
            run_isostatic_model(params, create_animation=True)
            
        elif model_name == 'exponential':
            run_exponential_model(params, create_animation=True)
            
        elif model_name == 'hybrid':
            run_hybrid_model(params, create_animation=True)
            
        else:
            print(f"Error: Unknown model '{model_name}'")
            result_queue.put(None)
            return

        # --- Step C: Use the output path that was passed in ---
        # The GIF should have been saved to output_file_path by the model
        if output_file_path.exists():
            print(f"Simulation successful. Output at: {output_file_path}")
            result_queue.put(str(output_file_path))
        else:
            print(f"Error: Simulation ran, but output file was not found at {output_file_path}")
            result_queue.put(None)

    except Exception as e:
        print(f"--- An error occurred during the simulation ---")
        print(e)
        import traceback
        traceback.print_exc()
        result_queue.put(None)