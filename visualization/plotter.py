# visualization/plotter.py
"""
Centralized plotting utilities for landscape evolution models.
Handles all visualization logic separately from model computation.
"""

import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt  
import numpy as np
from pathlib import Path
import config
from visualization.data_loader import get_section_for_time


class TopographyPlotter:
    """
    Handles all plotting for topography evolution animations.
    Separates visualization logic from model computation.
    """
    
    def __init__(self, x_modern, z_modern, sections=None):
        """
        Initialize plotter with modern topography and optional sections.
        
        Args:
            x_modern: Modern x coordinates
            z_modern: Modern z elevations
            sections: Dictionary of geological sections {age: DataFrame}
        """
        self.x_modern = x_modern
        self.z_modern = z_modern
        self.sections = sections if config.plot_geological_sections else None
        
        # Calculate plot limits
        x_margin = (x_modern.max() - x_modern.min()) * config.x_margin_fraction
        self.x_min = x_modern.min() - x_margin
        self.x_max = x_modern.max() + x_margin
        self.z_min = config.z_min_global
        self.z_max = z_modern.max() + config.z_max_offset
        
        print(f"\nPlotter initialized:")
        print(f"  X-axis: {self.x_min:.2f} to {self.x_max:.2f} km")
        print(f"  Z-axis: {self.z_min:.2f} to {self.z_max:.2f} km")
        print(f"  Geological sections: {'Enabled' if self.sections else 'Disabled'}")

    def draw_rain(self, ax, topo_x, topo_z):
        """
        Draws animated rain on the plot based on config settings.
        The rain is drawn as semi-transparent lines that extend from the
        top of the plot down to the topography.
        """
        # Only draw if the feature is enabled and intensity is positive
        if not config.enable_climate_erosion or config.rain_intensity <= 0:
            return

        # Get plot boundaries to determine where to draw the rain
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Convert angle to radians
        angle_rad = np.deg2rad(config.rain_direction_angle)

        # Determine the number of raindrops based on intensity
        num_drops = int(50 * config.rain_intensity)
        
        # Generate random starting X positions for the rain
        x_starts = np.random.uniform(xlim[0], xlim[1], num_drops)
        # Rain starts at the top of the plot
        y_starts = np.full_like(x_starts, self.z_max)
        
        # Calculate where each rain streak ends
        # 1. Find the topography height at the starting x-position of each streak
        y_ends = np.interp(x_starts, topo_x, topo_z)
        
        # 2. Calculate the corresponding end x-position to maintain the correct angle
        # tan(angle) = opposite / adjacent = (x_start - x_end) / (y_start - y_end)
        # So, (x_start - x_end) = (y_start - y_end) * tan(angle)
        x_ends = x_starts - (y_starts - y_ends) * np.tan(angle_rad)

        # Plot each rain streak
        for i in range(num_drops):
            # Ensure rain doesn't plot below the topography if interpolation is imperfect
            if y_starts[i] > y_ends[i]:
                ax.plot([x_starts[i], x_ends[i]], [y_starts[i], y_ends[i]], 
                        color='lightblue', alpha=0.6, linewidth=1.5, zorder=50)
    
    def plot_frame(self, x, z, time_ma, model_name="Model", additional_info=None):
        """
        Create a single frame plot.
        
        Args:
            x: Current x coordinates
            z: Current z elevations
            time_ma: Current time in Ma
            model_name: Name of the model for title
            additional_info: Additional text for title (e.g., "λ=10 Ma")
        
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        fig, ax = plt.subplots(figsize=config.figure_size)
        
        # Plot geological sections first (background layer)
        if self.sections is not None:
            self._plot_geological_section(ax, time_ma)
        
        # Plot topography on top
        ax.plot(x, z, color=config.topo_color, linewidth=config.topo_line_width, 
                label='Simulated Topography', zorder=100)
        ax.fill_between(x, z, y2=self.z_min, color=config.fill_color, 
                        alpha=config.fill_alpha, zorder=99)
        
        # Formatting
        title = f"{model_name}: {time_ma} Ma"
        if time_ma == 0:
            title += " (Modern)"
        if additional_info:
            title += f" ({additional_info})"
        
        # Draw rain animation if enabled
        self.draw_rain(ax, x, z)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel("X (km)")
        ax.set_ylabel("Z (km)")
        ax.set_xlim(self.x_min, self.x_max)
        ax.set_ylim(self.z_min, self.z_max)
        ax.set_aspect(config.vertical_exaggeration)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right')
        
        return fig
    
    def _plot_geological_section(self, ax, time_ma):
        """
        Plot geological section for the given time (internal method).
        
        Args:
            ax: Matplotlib axis
            time_ma: Current time in Ma
        """
        section = get_section_for_time(time_ma, self.sections)
        
        if section is None:
            return
        
        section_age = section['age'].iloc[0]
        
        # Log section info periodically
        if time_ma % 5 == 0:
            print(f"  Plotting {section_age} Ma section "
                  f"({len(section)} points, {section['unit_id'].nunique()} units)")
        
        # Plot each unit separately
        for unit_id, group in section.groupby('unit_id'):
            group = group.sort_values('x')
            ax.plot(group['x'], group['z'], 
                   linewidth=config.section_line_width, 
                   alpha=config.section_alpha, 
                   zorder=1)
    
    def save_frame(self, fig, output_path):
        """
        Save a figure to file with consistent dimensions.
        
        Args:
            fig: Matplotlib figure
            output_path: Path to save the figure
        """
        fig.savefig(output_path, dpi=config.dpi, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)


class AnimationManager:
    """
    Manages creation of animation frames and final GIF output.
    """
    
    def __init__(self, output_dir=None, output_file=None):
        """
        Initialize animation manager.
        
        Args:
            output_dir: Directory for frames. If None, uses config.get_frames_output_dir()
            output_file: Output GIF filename. If None, uses config.get_animation_output_file()
        """
        self.output_dir = Path(output_dir or config.get_frames_output_dir())
        self.output_file = output_file or config.get_animation_output_file()
        self.output_dir.mkdir(exist_ok=True)
        self.frame_paths = []
        
        print(f"\nAnimation Manager initialized:")
        print(f"  Frames directory: {self.output_dir}")
        print(f"  Output file: {self.output_file}")
    
    def get_frame_path(self, time_ma):
        """
        Get the path for a frame at given time.
        
        Args:
            time_ma: Time in Ma (will be converted to integer for filename)
        
        Returns:
            Path: Frame file path
        """
        return self.output_dir / f"frame_{int(time_ma):03d}.png"
    
    def add_frame(self, frame_path):
        """
        Add a frame to the animation sequence.
        
        Args:
            frame_path: Path to the saved frame
        """
        self.frame_paths.append(frame_path)
    
    def create_gif(self):
        """
        Create GIF from all collected frames.
        Ensures all images have the same dimensions.
        """
        import imageio.v2 as imageio
        from PIL import Image
        
        print(f"\nCreating animation with {len(self.frame_paths)} frames...")

        if config.reverse_animation:
            print("  - Reversing frame order for forward-in-time animation.")
            self.frame_paths.reverse() 
        
        # Load all images
        images = [imageio.imread(fp) for fp in self.frame_paths]
        
        # Get the most common shape (in case there are minor differences)
        shapes = [img.shape for img in images]
        if len(set(shapes)) > 1:
            print("  Warning: Detected frames with different sizes, resizing to match...")
            # Find max dimensions
            max_h = max(shape[0] for shape in shapes)
            max_w = max(shape[1] for shape in shapes)
            
            # Resize all images to match
            resized_images = []
            for img in images:
                if img.shape[0] != max_h or img.shape[1] != max_w:
                    pil_img = Image.fromarray(img)
                    pil_img = pil_img.resize((max_w, max_h), Image.Resampling.LANCZOS)
                    resized_images.append(np.array(pil_img))
                else:
                    resized_images.append(img)
            images = resized_images
        
        duration = 1000 / config.animation_fps  # milliseconds per frame
        
        imageio.mimsave(self.output_file, images, duration=duration, loop=0)
        
        print(f"Animation saved as {self.output_file}")
        print(f"  Frame rate: {config.animation_fps} fps")
        print(f"  Duration per frame: {duration:.0f}ms")
        print(f"  Total duration: {len(self.frame_paths) * duration / 1000:.1f}s")