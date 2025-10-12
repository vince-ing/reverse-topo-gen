# gui.py
"""
Main entry point for the Reverse Topography Modeler GUI.
"""
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from pathlib import Path
import threading
import queue
from PIL import Image, ImageTk, ImageSequence

import config
from simulation import run_simulation 

class TopoApp(tb.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("Reverse Topography Modeler")
        self.geometry("1400x900")

        # --- GIF Animation Attributes ---
        self.gif_frames = []
        self.gif_frame_index = 0
        self.animation_job = None
        self.gif_path = None

        # --- Queue for thread communication ---
        self.simulation_queue = queue.Queue()

        # --- Create Control Variables ---
        self.model_var = tk.StringVar(value=config.ACTIVE_MODEL)

        # Global settings
        self.fps_var = tk.IntVar(value=config.animation_fps)
        self.reverse_animation_var = tk.BooleanVar(value=config.reverse_animation)

        # Isostatic model parameters
        self.isostatic_blend_var = tk.DoubleVar(value=config.isostatic_blend_factor)
        self.isostatic_smoothing_var = tk.IntVar(value=config.isostatic_smoothing_window)
        self.isostatic_rho_crust_var = tk.IntVar(value=config.isostatic_rho_crust)
        self.isostatic_rho_mantle_var = tk.IntVar(value=config.isostatic_rho_mantle)
        
        # Exponential model parameters
        self.exp_lambda_topo_var = tk.DoubleVar(value=config.exp_lambda_topo)
        self.exp_z_initial_var = tk.DoubleVar(value=config.exp_z_initial)

        # Hybrid model parameters
        self.hybrid_z_initial_var = tk.DoubleVar(value=config.hybrid_z_initial)
        self.hybrid_erosion_efficiency_var = tk.DoubleVar(value=config.hybrid_erosion_efficiency)
        self.hybrid_blend_factor_var = tk.DoubleVar(value=config.hybrid_blend_factor)

        # Dictionary to manage parameter frames
        self.param_frames = {}

        self._create_layout()
        self._create_widgets()
        self._on_model_select()

    def _create_layout(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side: GIF display
        self.gif_display_frame = tb.Frame(main_pane)
        main_pane.add(self.gif_display_frame, weight=2)

        # Right side: Controls
        right_pane_container = tb.Frame(main_pane)
        main_pane.add(right_pane_container, weight=1)

        right_vertical_pane = ttk.PanedWindow(right_pane_container, orient=tk.VERTICAL)
        right_vertical_pane.pack(fill=tk.BOTH, expand=True)

        self.model_controls_frame = tb.Frame(right_vertical_pane, padding=10)
        right_vertical_pane.add(self.model_controls_frame, weight=3)

        self.status_frame = tb.Frame(right_vertical_pane, padding=10)
        right_vertical_pane.add(self.status_frame, weight=1)
        
    def _create_parameter_slider(self, parent, text, variable, from_, to, is_double=False):
        """Helper function to create a labeled slider."""
        frame = tb.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        tb.Label(frame, text=text, width=25).pack(side=tk.LEFT, padx=(0, 10))
        
        # Round double values for cleaner display
        if is_double:
            variable.trace_add("write", lambda *args: variable.set(round(variable.get(), 2)))
        
        slider = tb.Scale(frame, from_=from_, to=to, variable=variable, orient=tk.HORIZONTAL)
        slider.pack(fill=tk.X, expand=True, side=tk.LEFT)
        entry = tb.Entry(frame, textvariable=variable, width=7)
        entry.pack(side=tk.LEFT, padx=(10, 0))
        return frame

    def _on_model_select(self, event=None):
        selected_model = self.model_var.get()
        config.ACTIVE_MODEL = selected_model
        
        for name, frame in self.param_frames.items():
            if name == selected_model:
                frame.pack(fill=tk.X, pady=10)
            else:
                frame.pack_forget()

    def _create_widgets(self):
        # GIF Display Label
        self.gif_label = tb.Label(self.gif_display_frame, 
                                  text="Simulation output will be displayed here.", 
                                  bootstyle="secondary")
        self.gif_label.pack(fill=tk.BOTH, expand=True)

        # Right Frame Widgets (Modeling Controls)
        notebook = ttk.Notebook(self.model_controls_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Model & Parameters
        model_params_tab = tb.Frame(notebook, padding=10)
        notebook.add(model_params_tab, text="Model & Parameters")

        # Tab 2: Global Settings
        global_settings_tab = tb.Frame(notebook, padding=10)
        notebook.add(global_settings_tab, text="Global Settings")

        # --- Widgets for Global Settings Tab ---
        tb.Label(global_settings_tab, text="Animation & Output", 
                bootstyle="primary").pack(pady=(0, 10), anchor="w")
        self._create_parameter_slider(global_settings_tab, "Animation Speed (FPS):", 
                                     self.fps_var, 1, 60)
        tb.Checkbutton(global_settings_tab, text="Animate Forward in Time", 
                      variable=self.reverse_animation_var, 
                      bootstyle="primary").pack(pady=10, anchor="w")
        
        # --- Widgets for Model Parameters Tab ---
        model_selection_frame = tb.Frame(model_params_tab)
        model_selection_frame.pack(fill=tk.X, pady=5)
        tb.Label(model_selection_frame, text="Select Model:", 
                width=15).pack(side=tk.LEFT, padx=(0, 10))
        model_combo = tb.Combobox(model_selection_frame, textvariable=self.model_var, 
                                 values=["isostatic", "exponential", "hybrid"], 
                                 state="readonly")
        model_combo.pack(fill=tk.X, expand=True)
        model_combo.bind("<<ComboboxSelected>>", self._on_model_select)

        params_container = tb.Frame(model_params_tab)
        params_container.pack(fill=tk.X, pady=10)

        # -- Isostatic Parameters --
        self.param_frames["isostatic"] = tb.LabelFrame(params_container, 
                                                       text="Isostatic Model Parameters", 
                                                       bootstyle="info", padding=10)
        self._create_parameter_slider(self.param_frames["isostatic"], "Blend Factor:", 
                                     self.isostatic_blend_var, 0.0, 1.0, is_double=True)
        self._create_parameter_slider(self.param_frames["isostatic"], "Smoothing Window:", 
                                     self.isostatic_smoothing_var, 1, 20)
        self._create_parameter_slider(self.param_frames["isostatic"], "Crust Density (kg/m³):", 
                                     self.isostatic_rho_crust_var, 2000, 3500)
        self._create_parameter_slider(self.param_frames["isostatic"], "Mantle Density (kg/m³):", 
                                     self.isostatic_rho_mantle_var, 3000, 4500)

        # -- Exponential Parameters --
        self.param_frames["exponential"] = tb.LabelFrame(params_container, 
                                                         text="Exponential Model Parameters", 
                                                         bootstyle="info", padding=10)
        self._create_parameter_slider(self.param_frames["exponential"], "Decay Constant (λ):", 
                                     self.exp_lambda_topo_var, 1.0, 50.0, is_double=True)
        self._create_parameter_slider(self.param_frames["exponential"], "Initial Elevation (km):", 
                                     self.exp_z_initial_var, -5.0, 5.0, is_double=True)

        # -- Hybrid Parameters --
        self.param_frames["hybrid"] = tb.LabelFrame(params_container, 
                                                    text="Hybrid Model Parameters", 
                                                    bootstyle="info", padding=10)
        self._create_parameter_slider(self.param_frames["hybrid"], "Initial Elevation (km):", 
                                     self.hybrid_z_initial_var, -5.0, 5.0, is_double=True)
        self._create_parameter_slider(self.param_frames["hybrid"], "Erosion Efficiency:", 
                                     self.hybrid_erosion_efficiency_var, 0.0, 1.0, is_double=True)
        self._create_parameter_slider(self.param_frames["hybrid"], "Blend Factor:", 
                                     self.hybrid_blend_factor_var, 0.0, 1.0, is_double=True)
        
        # --- Bottom Frame Widgets (Action & Status) ---
        tb.Label(self.status_frame, text="Action & Status", 
                bootstyle="info").pack(pady=(0, 10), anchor="w")
        self.run_button = tb.Button(self.status_frame, text="Run Simulation", 
                                    bootstyle="success", command=self._start_simulation)
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))
        self.progress_bar = tb.Progressbar(self.status_frame, bootstyle="success-striped", 
                                          mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, expand=True, side=tk.LEFT)
        self.status_label = tb.Label(self.status_frame, text="", bootstyle="light")
        self.status_label.pack(side=tk.LEFT, padx=(10,0))
    
    # --- Simulation Handling Methods ---
    def _start_simulation(self):
        """Starts the simulation process in a separate thread."""
        self.run_button.config(state="disabled")
        self.progress_bar.start()
        self.status_label.config(text="Running...")
        
        # Collect all current parameters into a dictionary
        params = {
            'model': self.model_var.get(),
            'fps': self.fps_var.get(),
            'reverse_animation': self.reverse_animation_var.get(),
            # Isostatic
            'isostatic_blend_factor': self.isostatic_blend_var.get(),
            'isostatic_smoothing_window': self.isostatic_smoothing_var.get(),
            'isostatic_rho_crust': self.isostatic_rho_crust_var.get(),
            'isostatic_rho_mantle': self.isostatic_rho_mantle_var.get(),
            # Exponential
            'exp_lambda_topo': self.exp_lambda_topo_var.get(),
            'exp_z_initial': self.exp_z_initial_var.get(),
            # Hybrid
            'hybrid_z_initial': self.hybrid_z_initial_var.get(),
            'hybrid_erosion_efficiency': self.hybrid_erosion_efficiency_var.get(),
            'hybrid_blend_factor': self.hybrid_blend_factor_var.get(),
        }

        # Get the output path for the GIF ONCE before running
        output_file = config.get_animation_output_file()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Run simulation in a thread to not freeze the GUI
        threading.Thread(
            target=run_simulation, 
            args=(params, output_file, self.simulation_queue), 
            daemon=True
        ).start()
        
        # Start checking the queue for a result
        self.after(100, self._check_simulation_status)

    def _check_simulation_status(self):
        """Checks the queue for a result from the simulation thread."""
        try:
            result_path = self.simulation_queue.get(block=False)
            self.progress_bar.stop()
            self.run_button.config(state="normal")

            if result_path and Path(result_path).exists():
                self.status_label.config(text="Done!")
                self._load_gif(result_path)
            else:
                self.status_label.config(text="Error!")
                self.gif_label.config(text="Simulation failed or produced no output.", image='')

        except queue.Empty:
            # If no result yet, check again after 100ms
            self.after(100, self._check_simulation_status)

    # --- GIF Animation Methods ---
    def _load_gif(self, path):
        """Loads a GIF and starts its animation."""
        if self.animation_job:
            self.after_cancel(self.animation_job)
        
        self.gif_path = path
        self.gif_label.config(text="")

        try:
            image = Image.open(self.gif_path)
            self.gif_frames = []
            for frame in ImageSequence.Iterator(image):
                photo = ImageTk.PhotoImage(frame.copy())
                self.gif_frames.append(photo)
            
            self.gif_frame_index = 0
            self.frame_duration = image.info.get('duration', 1000 // self.fps_var.get())
            self._animate_gif()
        except Exception as e:
            self.gif_label.config(text=f"Error loading GIF:\n{e}")
            print(f"Error loading GIF: {e}")

    def _animate_gif(self):
        """Cycles through GIF frames to create animation."""
        if not self.gif_frames:
            return

        # Set the current frame
        frame = self.gif_frames[self.gif_frame_index]
        self.gif_label.config(image=frame)

        # Move to the next frame
        self.gif_frame_index = (self.gif_frame_index + 1) % len(self.gif_frames)

        # Schedule the next frame update
        self.animation_job = self.after(self.frame_duration, self._animate_gif)


def main():
    app = TopoApp()
    app.mainloop()

if __name__ == "__main__":
    main()