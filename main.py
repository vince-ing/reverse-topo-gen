# main.py
from visualization.data_load import load_topography
from visualization.plotting import plot_topography
from pathlib import Path

def main():
    topo_file = Path("data/Topo/topo_04.dat")
    x, z = load_topography(topo_file)
    plot_topography(x, z, title=topo_file.name, vertical_exaggeration=1)

if __name__ == "__main__":
    main()
