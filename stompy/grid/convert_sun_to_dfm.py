"""
Read a suntans grid in the current directory and write a DFM grid, output_net.nc
"""

from stompy.grid import unstructured_grid
from stompy.model.delft import dfm_grid

def convert_mesh_suntans_to_dfm(output_name):
    #ug=unstructured_grid.SuntansGrid(".")
    #dfm_grid.write_dfm(ug,"TX_output_net.nc")

    ug=unstructured_grid.SuntansGrid(".")
    dfm_grid.write_dfm(ug,output_name)




"""
- Convert xyz to tiff using GDAL
- Use the tiff for elevation for the mesh

"""


