"""
Read a suntans grid in the current directory and write a DFM grid, output_net.nc
"""

from stompy.grid import unstructured_grid
from stompy.model.delft import dfm_grid

def convert_mesh_suntans_to_dfm(suntans_path, output_path):
    ug = unstructured_grid.SuntansGrid(suntans_path)
    dfm_grid.write_dfm(ug, output_path)

