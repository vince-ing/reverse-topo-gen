# reverse-topo-gen
This is a project that reconstructs surface topology from only vector data, visualizing it through time. It utilizes geophysics combined with machine learning algorithms to calculate surface topography, and presents it in a user-friendly and interactive simulation. 

Features:
- 3 models: isostatic, exponential, or hybrid
- Adjustable hyperparameters such as erosion efficiency, decay constants, crest density, and mantle density.
- Compare and constrast different runs and models
- Option to plot changing geologic sections through time

How to use: 
Ensure that all dependencies in requirements.txt are installed.
Run from gui.py in the root folder.
Default data from Mora et al. 2015 is provided but you can enter your own.
  Data for the topography profile must be in x, z columns
  Data for the vectors should be in x1, z1, x2, z2, and their ages must be specified

This is intended to be expanded upon, user can contribute new models and methods for generating topography
  
  
