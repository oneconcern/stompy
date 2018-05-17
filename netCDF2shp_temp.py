# Convert netCDF delft output -> shp

import xarray as xr
from stompy.model.delft import dfm_grid

# Run 5
map_output=xr.open_dataset('/mnt/TX_modeling_new/aws_modeling/aws_setup_0323/DFM_OUTPUT_FlowFM_Run5/FlowFM_map.nc')

#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/DFM_OUTPUT_FlowFM/FlowFM_map.nc')
g=dfm_grid.DFMGrid(map_output)

# Get water depth from the last time step of output in the map file:
wse=map_output.mesh2d_s1.isel(time=-1).values
dep=map_output.mesh2d_waterdepth.isel(time=-1).values

# This is hard wired to this output only: 128th steps in the output = 8/31/2017
# The output count starts 0


# when the output's 41st output is 8/31/2017
wse0831=map_output.mesh2d_s1.isel(time=41).values
dep0831=map_output.mesh2d_waterdepth.isel(time=41).values

# Get max water depth overall time steps:
wse_max=map_output.mesh2d_s1.max(dim='time').values
dep_max=map_output.mesh2d_waterdepth.max(dim='time').values


# Run5 
g.write_cells_shp('/mnt/output_shp_dflow/TX_new/Run5_output.shp',extra_fields=  \
    [('wse',wse),('wse0831',wse0831),('wse_max',wse_max),('depth',dep),('depth0831',dep0831),('depth_max',dep_max)])
