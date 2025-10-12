# main.py
"""
Main entry point for landscape evolution models.
"""

import config


def main():
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


if __name__ == "__main__":
    main()