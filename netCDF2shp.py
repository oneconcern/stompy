# Runs this script on parallels Linux!
# go to /media/psf/Home/WORK/git/src
# and run netCDF2shp.py


import xarray as xr
from stompy.model.delft import dfm_grid

#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART01/DFM_OUTPUT_FlowFM_rst/FlowFM_rst_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/DFM_OUTPUT_FlowFM/FlowFM_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART02/DFM_OUTPUT_FlowFM_rst_n80pc/FlowFM_rst_n80pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART03/DFM_OUTPUT_FlowFM_rst_n120pc/FlowFM_rst_n120pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART04/DFM_OUTPUT_FlowFM_rst_n50pc/FlowFM_rst_n50pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART06/DFM_OUTPUT_FlowFM_rst_n90pc/FlowFM_rst_n90pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART07/DFM_OUTPUT_FlowFM_rst_n110pc/FlowFM_rst_n110pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART08/DFM_OUTPUT_FlowFM_rst_n75pc/FlowFM_rst_n75pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART09/DFM_OUTPUT_FlowFM_rst_n135pc/FlowFM_rst_n135pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART10/DFM_OUTPUT_FlowFM_rst_n130pc/FlowFM_rst_n130pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART11/DFM_OUTPUT_FlowFM_rst_n140pc/FlowFM_rst_n140pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART12/DFM_OUTPUT_FlowFM_rst_n105pc/FlowFM_rst_n105pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART13/DFM_OUTPUT_FlowFM_rst_n115pc/FlowFM_rst_n115pc_map.nc')
map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART14/DFM_OUTPUT_FlowFM_rst_n125pc/FlowFM_rst_n125pc_map.nc')

#map_output=xr.open_dataset('/media/psf/Home/WORK/TX_modeling_Harris_linux_WSE/DFM_OUTPUT_FlowFM/FlowFM_map.nc')



#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/DFM_OUTPUT_FlowFM/FlowFM_map.nc')
g=dfm_grid.DFMGrid(map_output)

# Get water depth from the last time step of output in the map file:
wse=map_output.mesh2d_s1.isel(time=-1).values
dep=map_output.mesh2d_waterdepth.isel(time=-1).values

# Get max water depth overall time steps:
wse_max=map_output.mesh2d_s1.max(dim='time').values
dep_max=map_output.mesh2d_waterdepth.max(dim='time').values

#g.write_cells_shp('grid-cells-wse-proc0000.shp',extra_fields=[('wse',wse),('wse_max',wse_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/sim02_dflow_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart06_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart07_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart08_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart09_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart10_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart11_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart12_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart13_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart14_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])

#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/WSE_testcase.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
