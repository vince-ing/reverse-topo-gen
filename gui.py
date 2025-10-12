# gui.py
"""
Main entry point for the Reverse Topography Modeler GUI.
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import config  # Import your config file to get default values

class TopoApp(tb.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("Reverse Topography Modeler")
        self.geometry("1200x800")

        # --- Create Control Variables ---
        # These hold the state of the UI widgets and link to the config values
        self.model_var = tk.StringVar(value=config.ACTIVE_MODEL)

        # Global settings
        self.fps_var = tk.IntVar(value=config.animation_fps)
        self.reverse_animation_var = tk.BooleanVar(value=config.reverse_animation)

        # Isostatic model parameters
        self.isostatic_blend_var = tk.DoubleVar(value=config.isostatic_blend_factor)
        self.isostatic_smoothing_var = tk.IntVar(value=config.isostatic_smoothing_window)
        self.isostatic_rho_crust_var = tk.IntVar(value=config.isostatic_rho_crust)
        self.isostatic_rho_mantle_var = tk.IntVar(value=config.isostatic_rho_mantle)

        # (Add variables for other models here if needed)

        # This dictionary will help manage the parameter frames
        self.param_frames = {}

        self._create_layout()
        self._create_widgets()
        
        # Set the initial visibility of the parameter frame
        self._on_model_select()

    def _create_layout(self):
        """Creates the main paned window layout."""
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left_frame = tb.Frame(main_pane, padding=10)
        main_pane.add(self.left_frame, weight=1)

        right_pane_container = tb.Frame(main_pane)
        main_pane.add(right_pane_container, weight=2)

        right_vertical_pane = ttk.PanedWindow(right_pane_container, orient=tk.VERTICAL)
        right_vertical_pane.pack(fill=tk.BOTH, expand=True)

        self.model_controls_frame = tb.Frame(right_vertical_pane, padding=10)
        right_vertical_pane.add(self.model_controls_frame, weight=3)

        self.status_frame = tb.Frame(right_vertical_pane, padding=10)
        right_vertical_pane.add(self.status_frame, weight=1)

    def _create_parameter_slider(self, parent, text, variable, from_, to):
        """Helper function to create a labeled slider."""
        frame = tb.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        tb.Label(frame, text=text, width=20).pack(side=tk.LEFT, padx=(0, 10))
        slider = tb.Scale(frame, from_=from_, to=to, variable=variable, orient=tk.HORIZONTAL)
        slider.pack(fill=tk.X, expand=True, side=tk.LEFT)
        # Show the value next to the slider
        tb.Label(frame, textvariable=variable, width=5).pack(side=tk.LEFT, padx=(10, 0))
        return frame

    def _on_model_select(self, event=None):
        """Callback function to show/hide parameter frames based on model selection."""
        selected_model = self.model_var.get()
        for name, frame in self.param_frames.items():
            if name == selected_model:
                frame.pack(fill=tk.X, pady=10)
            else:
                frame.pack_forget()

    def _create_widgets(self):
        """Creates and places the widgets in their respective frames."""
        # --- Left Frame Widgets ---
        tb.Label(self.left_frame, text="Global Settings", bootstyle="primary").pack(pady=(0, 10), anchor="w")
        self._create_parameter_slider(self.left_frame, "Animation Speed (FPS):", self.fps_var, 1, 30)
        tb.Checkbutton(self.left_frame, text="Animate Forward in Time", variable=self.reverse_animation_var, bootstyle="primary").pack(pady=10, anchor="w")

        # --- Right Frame Widgets (Modeling Controls) ---
        notebook = ttk.Notebook(self.model_controls_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        model_params_tab = tb.Frame(notebook, padding=10)
        notebook.add(model_params_tab, text="Model & Parameters")

        # Model Selection Dropdown
        model_selection_frame = tb.Frame(model_params_tab)
        model_selection_frame.pack(fill=tk.X, pady=5)
        tb.Label(model_selection_frame, text="Select Model:", width=15).pack(side=tk.LEFT, padx=(0, 10))
        model_combo = tb.Combobox(model_selection_frame, textvariable=self.model_var, values=["isostatic", "exponential", "hybrid"], state="readonly")
        model_combo.pack(fill=tk.X, expand=True)
        model_combo.current(0)
        model_combo.bind("<<ComboboxSelected>>", self._on_model_select) # Bind the function

        # --- Dynamic Parameter Frames ---
        params_container = tb.Frame(model_params_tab)
        params_container.pack(fill=tk.X)

        # -- Isostatic Parameters --
        self.param_frames["isostatic"] = tb.LabelFrame(params_container, text="Isostatic Model Parameters", bootstyle="info", padding=10)
        self._create_parameter_slider(self.param_frames["isostatic"], "Blend Factor:", self.isostatic_blend_var, 0.0, 1.0)
        self._create_parameter_slider(self.param_frames["isostatic"], "Smoothing Window:", self.isostatic_smoothing_var, 1, 10)

        # -- Exponential Parameters (Placeholder) --
        self.param_frames["exponential"] = tb.LabelFrame(params_container, text="Exponential Model Parameters", bootstyle="info", padding=10)
        tb.Label(self.param_frames["exponential"], text="Exponential sliders will go here.").pack()

        # -- Hybrid Parameters (Placeholder) --
        self.param_frames["hybrid"] = tb.LabelFrame(params_container, text="Hybrid Model Parameters", bootstyle="info", padding=10)
        tb.Label(self.param_frames["hybrid"], text="Hybrid sliders will go here.").pack()

        # --- Bottom Frame Widgets (Action & Status) ---
        tb.Label(self.status_frame, text="Action & Status", bootstyle="info").pack(pady=(0, 10), anchor="w")
        run_button = tb.Button(self.status_frame, text="▶️ Run Simulation", bootstyle="success")
        run_button.pack(side=tk.LEFT, padx=(0, 10))
        progress = tb.Progressbar(self.status_frame, bootstyle="success-striped")
        progress.pack(fill=tk.X, expand=True, side=tk.LEFT)

def main():
    app = TopoApp()
    app.mainloop()

if __name__ == "__main__":
    main()