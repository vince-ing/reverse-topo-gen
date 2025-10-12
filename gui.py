# gui.py
"""
Main entry point for the Reverse Topography Modeler GUI.
"""
import tkinter as tk
from tkinter import ttk, filedialog
import ttkbootstrap as tb
from pathlib import Path
import threading
import queue
from PIL import Image, ImageTk, ImageSequence
import glob

import config
from simulation import run_simulation 
from comparison import create_comparison_gif_from_paths

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
        self.comparison_queue = queue.Queue()  

        # --- Create Control Variables ---
        self.model_var = tk.StringVar(value=config.ACTIVE_MODEL)

        # Global settings
        self.fps_var = tk.IntVar(value=config.animation_fps)
        self.reverse_animation_var = tk.BooleanVar(value=config.reverse_animation)
        self.vertical_exaggeration_var = tk.IntVar(value=config.vertical_exaggeration)
        self.plot_sections_var = tk.BooleanVar(value=config.plot_geological_sections)
        self.y_axis_padding_top_var = tk.DoubleVar(value=1.0)     
        self.y_axis_padding_bottom_var = tk.DoubleVar(value=2.0)  

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

        # Comparison variables - NEW
        self.comparison_path1_var = tk.StringVar(value="")
        self.comparison_path2_var = tk.StringVar(value="")

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
        
        # Use classic tk.Scale instead of ttk.Scale for resolution support
        if is_double:
            slider = tk.Scale(frame, from_=from_, to=to, variable=variable, 
                            orient=tk.HORIZONTAL, resolution=0.1, 
                            showvalue=False, highlightthickness=0)
        else:
            slider = tk.Scale(frame, from_=from_, to=to, variable=variable, 
                            orient=tk.HORIZONTAL, resolution=1,
                            showvalue=False, highlightthickness=0)
        
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

        # Tab 3: Comparison 
        comparison_tab = tb.Frame(notebook, padding=10)
        notebook.add(comparison_tab, text="Compare Runs")

        # --- Widgets for Global Settings Tab ---
        tb.Label(global_settings_tab, text="Animation & Output", 
                bootstyle="primary").pack(pady=(0, 10), anchor="w")
        self._create_parameter_slider(global_settings_tab, "Animation Speed (FPS):", 
                                     self.fps_var, 1, 60)
        self._create_parameter_slider(global_settings_tab, "Vertical Exaggeration:", 
                                     self.vertical_exaggeration_var, 1, 20)
        tb.Checkbutton(global_settings_tab, text="Animate Forward in Time", 
                      variable=self.reverse_animation_var, 
                      bootstyle="primary").pack(pady=10, anchor="w")
        tb.Checkbutton(global_settings_tab, text="Plot Geological Sections",
                      variable=self.plot_sections_var,
                      bootstyle="primary").pack(pady=10, anchor="w")
        self._create_parameter_slider(global_settings_tab, "Y-Axis Top Padding (km):", 
                             self.y_axis_padding_top_var, 0.0, 10.0, is_double=True)
        self._create_parameter_slider(global_settings_tab, "Y-Axis Bottom Padding (km):", 
                                    self.y_axis_padding_bottom_var, 0.0, 30.0, is_double=True)
        
        # --- Widgets for Comparison Tab - NEW ---
        tb.Label(comparison_tab, text="Compare Two Simulation Runs", 
                bootstyle="primary", font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 15), anchor="w")
        
        # Explanation
        explanation = ("Select two previous simulation runs to compare them side-by-side.\n"
                      "The frames will be stacked vertically in a new comparison GIF.")
        tb.Label(comparison_tab, text=explanation, bootstyle="secondary", 
                wraplength=400).pack(pady=(0, 15), anchor="w")
        
        # Run 1 Selection
        run1_frame = tb.LabelFrame(comparison_tab, text="First Run", bootstyle="info", padding=10)
        run1_frame.pack(fill=tk.X, pady=5)
        
        run1_path_frame = tb.Frame(run1_frame)
        run1_path_frame.pack(fill=tk.X, pady=5)
        tb.Entry(run1_path_frame, textvariable=self.comparison_path1_var, 
                state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tb.Button(run1_path_frame, text="Browse Frames", 
                 command=lambda: self._browse_frames_folder(self.comparison_path1_var),
                 bootstyle="info-outline").pack(side=tk.LEFT, padx=2)
        tb.Button(run1_path_frame, text="Browse GIF", 
                 command=lambda: self._browse_gif(self.comparison_path1_var),
                 bootstyle="info-outline").pack(side=tk.LEFT)
        
        # Run 2 Selection
        run2_frame = tb.LabelFrame(comparison_tab, text="Second Run", bootstyle="info", padding=10)
        run2_frame.pack(fill=tk.X, pady=5)
        
        run2_path_frame = tb.Frame(run2_frame)
        run2_path_frame.pack(fill=tk.X, pady=5)
        tb.Entry(run2_path_frame, textvariable=self.comparison_path2_var, 
                state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tb.Button(run2_path_frame, text="Browse Frames", 
                 command=lambda: self._browse_frames_folder(self.comparison_path2_var),
                 bootstyle="info-outline").pack(side=tk.LEFT, padx=2)
        tb.Button(run2_path_frame, text="Browse GIF", 
                 command=lambda: self._browse_gif(self.comparison_path2_var),
                 bootstyle="info-outline").pack(side=tk.LEFT)
        
        # Quick Select from Recent Runs
        quick_select_frame = tb.LabelFrame(comparison_tab, text="Quick Select Recent Runs", 
                                          bootstyle="success", padding=10)
        quick_select_frame.pack(fill=tk.X, pady=10)
        
        tb.Label(quick_select_frame, text="Select from recent outputs:", 
                bootstyle="secondary").pack(anchor="w", pady=(0, 5))
        
        quick_buttons_frame = tb.Frame(quick_select_frame)
        quick_buttons_frame.pack(fill=tk.X)
        
        tb.Button(quick_buttons_frame, text="Load Run 1", 
                 command=lambda: self._quick_select_run(1),
                 bootstyle="success-outline").pack(side=tk.LEFT, padx=5)
        tb.Button(quick_buttons_frame, text="Load Run 2", 
                 command=lambda: self._quick_select_run(2),
                 bootstyle="success-outline").pack(side=tk.LEFT)
        
        # Create Comparison Button
        self.create_comparison_button = tb.Button(comparison_tab, text="Create Comparison GIF", 
                                                  command=self._create_comparison,
                                                  bootstyle="primary")
        self.create_comparison_button.pack(pady=15)
        
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
                                                         text="Time Interpolation Model Parameters", 
                                                         bootstyle="info", padding=10)
        self._create_parameter_slider(self.param_frames["exponential"], "Decay Constant (λ):", 
                                     self.exp_lambda_topo_var, 1.0, 50.0, is_double=True)
        self._create_parameter_slider(self.param_frames["exponential"], "Initial Elevation (km):", 
                                     self.exp_z_initial_var, -5.0, 5.0, is_double=True)

        # -- Hybrid Parameters --
        self.param_frames["hybrid"] = tb.LabelFrame(params_container, 
                                                    text="Vertical Interpolation Model Parameters", 
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
    
    # --- Comparison Methods - ---
    def _browse_frames_folder(self, var):
        """Browse for a frames folder."""
        folder = filedialog.askdirectory(
            title="Select Frames Folder",
            initialdir="output/frames"
        )
        if folder:
            var.set(folder)

    def _browse_gif(self, var):
        """Browse for a GIF file (will extract frames from it)."""
        file = filedialog.askopenfilename(
            title="Select GIF File",
            initialdir="output/gifs",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")]
        )
        if file:
            var.set(file)
    
    def _quick_select_run(self, run_number):
        """Quick select dialog showing recent runs."""
        # Get all available runs
        frames_dir = Path("output/frames")
        gifs_dir = Path("output/gifs")
        
        options = []
        
        # Scan for frame directories
        if frames_dir.exists():
            for model_dir in frames_dir.iterdir():
                if model_dir.is_dir():
                    for run_dir in sorted(model_dir.iterdir(), reverse=True):
                        if run_dir.is_dir():
                            options.append(("Frames", f"{model_dir.name}/{run_dir.name}", str(run_dir)))
        
        # Scan for GIF files
        if gifs_dir.exists():
            for gif_file in sorted(gifs_dir.glob("*.gif"), reverse=True):
                options.append(("GIF", gif_file.stem, str(gif_file)))
        
        if not options:
            self.status_label.config(text="No runs found!")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Select Run {run_number}")
        dialog.geometry("500x400")
        
        tb.Label(dialog, text=f"Select Run {run_number}:", 
                font=("TkDefaultFont", 10, "bold")).pack(pady=10)
        
        # Create listbox with scrollbar
        list_frame = tb.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tb.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("TkDefaultFont", 9))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        for type_, name, path in options:
            listbox.insert(tk.END, f"[{type_}] {name}")
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                selected_path = options[idx][2]
                if run_number == 1:
                    self.comparison_path1_var.set(selected_path)
                else:
                    self.comparison_path2_var.set(selected_path)
                dialog.destroy()
        
        # Buttons
        button_frame = tb.Frame(dialog)
        button_frame.pack(pady=10)
        
        tb.Button(button_frame, text="Select", command=on_select, 
                 bootstyle="success").pack(side=tk.LEFT, padx=5)
        tb.Button(button_frame, text="Cancel", command=dialog.destroy, 
                 bootstyle="secondary").pack(side=tk.LEFT, padx=5)
    
    def _create_comparison(self):
        """Create a comparison GIF from two selected runs."""
        path1 = self.comparison_path1_var.get()
        path2 = self.comparison_path2_var.get()
        
        if not path1 or not path2:
            self.status_label.config(text="Select both runs!")
            return
        
        if not Path(path1).exists() or not Path(path2).exists():
            self.status_label.config(text="Invalid paths!")
            return
        
        self.create_comparison_button.config(state="disabled")
        self.progress_bar.start()
        self.status_label.config(text="Creating comparison...")
        
        # Run comparison in thread
        threading.Thread(
            target=self._run_comparison_thread,
            args=(path1, path2),
            daemon=True
        ).start()
        
        # Start checking for result
        self.after(100, self._check_comparison_status)
    
    def _run_comparison_thread(self, path1, path2):
        """Thread function to create comparison."""
        try:
            # Pass the current reverse_animation setting to the comparison function
            result_path = create_comparison_gif_from_paths(
                path1, 
                path2, 
                reverse_animation=self.reverse_animation_var.get()
            )
            self.comparison_queue.put(result_path)
        except Exception as e:
            print(f"Comparison error: {e}")
            import traceback
            traceback.print_exc()
            self.comparison_queue.put(None)
    
    def _check_comparison_status(self):
        """Check if comparison is complete."""
        try:
            result_path = self.comparison_queue.get(block=False)
            self.progress_bar.stop()
            self.create_comparison_button.config(state="normal")
            
            if result_path and Path(result_path).exists():
                self.status_label.config(text="Comparison done!")
                self._load_gif(result_path)
            else:
                self.status_label.config(text="Comparison failed!")
        except queue.Empty:
            self.after(100, self._check_comparison_status)
    
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
            'vertical_exaggeration': self.vertical_exaggeration_var.get(),
            'plot_geological_sections': self.plot_sections_var.get(),
            'y_axis_padding_top': self.y_axis_padding_top_var.get(),      
            'y_axis_padding_bottom': self.y_axis_padding_bottom_var.get(), 
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