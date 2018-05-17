# Runs this script on parallels Linux!

#  $ source activate meshgen # activate the new 'meshgen' environment

# go to /media/psf/Home/WORK/git/src
# and run netCDF2shp.py


import xarray as xr
from stompy.model.delft import dfm_grid


#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/RESTART14/DFM_OUTPUT_FlowFM_rst_n125pc/FlowFM_rst_n125pc_map.nc')
#map_output=xr.open_dataset('/media/psf/Home/WORK/sim04/DFM_OUTPUT_FlowFM/FlowFM_map.nc')
#map_output=xr.open_dataset('/mnt/TX_modeling_new/linux_modeling/DFM_OUTPUT_FlowFM/FlowFM_map.nc')
#map_output=xr.open_dataset('/mnt/TX_modeling_new/linux_modeling_110pc/DFM_OUTPUT_FlowFM_run3/FlowFM_map.nc')

# Run 1
#map_output=xr.open_dataset('/mnt/TX_modeling_new/aws_modeling/aws_setup_032018/DFM_OUTPUT_FlowFM_Run1/FlowFM_map.nc')

# Run 2
#map_output=xr.open_dataset('/mnt/TX_modeling_new/aws_modeling/aws_setup_0321/DFM_OUTPUT_FlowFM_Run2/FlowFM_map.nc')

# Run 4
#map_output=xr.open_dataset('/mnt/TX_modeling_new/linux_modeling_110pc_WSE/DFM_OUTPUT_FlowFM_Run4/FlowFM_map.nc')

# Run 6
#map_output=xr.open_dataset('/mnt/TX_modeling_new/aws_modeling/aws_setup_Run6_87pc/DFM_OUTPUT_FlowFM_Run6/FlowFM_map.nc')

# Run 5
#map_output=xr.open_dataset('/mnt/TX_modeling_new/aws_modeling/aws_setup_0323/DFM_OUTPUT_FlowFM_Run5/FlowFM_map.nc')

# NC modeling
map_output=xr.open_dataset('/mnt/WORK/NC_modeling/linux_runs/test5_87pc/DFM_OUTPUT_FlowFM/FlowFM_map.nc')

#map_output=xr.open_dataset('/media/psf/Home/WORK/sim02_br_removed_all_Q/DFM_OUTPUT_FlowFM/FlowFM_map.nc')
g=dfm_grid.DFMGrid(map_output)

# Get water depth from the last time step of output in the map file:
wse=map_output.mesh2d_s1.isel(time=-1).values
dep=map_output.mesh2d_waterdepth.isel(time=-1).values

# This is hard wired to this output only: 128th steps in the output = 8/31/2017
# The output count starts 0
#wse0831=map_output.mesh2d_s1.isel(time=128).values
#dep0831=map_output.mesh2d_waterdepth.isel(time=128).values

# when the output's 41st output is 8/31/2017
#wse0831=map_output.mesh2d_s1.isel(time=41).values
#dep0831=map_output.mesh2d_waterdepth.isel(time=41).values

# when the output's 41st output is 8/31/2017
wse1013=map_output.mesh2d_s1.isel(time=49).values
dep1013=map_output.mesh2d_waterdepth.isel(time=49).values

# Get max water depth overall time steps:
wse_max=map_output.mesh2d_s1.max(dim='time').values
dep_max=map_output.mesh2d_waterdepth.max(dim='time').values


#g.write_cells_shp('/media/psf/Home/WORK/sim02_br_removed_all_Q/output_shp/sim02_restart14_output.shp',extra_fields=[('wse',wse),('wse_max',wse_max),('depth',dep),('depth_max',dep_max)])
#g.write_cells_shp('/media/psf/Home/WORK/sim04/output_shp/sim04_output.shp',extra_fields=[('wse_max',wse_max),('depth_max',dep_max)])
#g.write_cells_shp('/mnt/TX_modeling_new/linux_modeling_110pc/DFM_OUTPUT_FlowFM_run3/output_shp/otuput_depth_110pc.shp',extra_fields=[('wse_max',wse_max),('depth_max',dep_max)])
#g.write_cells_shp('/mnt/TX_modeling_new/aws_modeling/DFM_OUTPUT_FlowFM/output_shp/baseline_output.shp',extra_fields=[('wse_max',wse_max),('depth_max',dep_max)])

# Run 1
#g.write_cells_shp('/mnt/TX_modeling_new/aws_modeling/aws_setup_032018/DFM_OUTPUT_FlowFM_Run1/output_shp/Run1_output.shp',extra_fields=  \
#    [('wse',wse),('wse0831',wse0831),('wse_max',wse_max),('depth',dep),('depth0831',dep0831),('depth_max',dep_max)])
# Run 2
#g.write_cells_shp('/mnt/TX_modeling_new/aws_modeling/aws_setup_0321/DFM_OUTPUT_FlowFM_Run2/output_shp/Run2_output.shp',extra_fields=  \
#    [('wse',wse),('wse0831',wse0831),('wse_max',wse_max),('depth',dep),('depth0831',dep0831),('depth_max',dep_max)])
# Run 4
#g.write_cells_shp('/mnt/TX_modeling_new/linux_modeling_110pc_WSE/DFM_OUTPUT_FlowFM_Run4/output_shp/Run4_output.shp',extra_fields=  \
#    [('wse',wse),('wse0831',wse0831),('wse_max',wse_max),('depth',dep),('depth0831',dep0831),('depth_max',dep_max)])
# Run 6
#g.write_cells_shp('/mnt/TX_modeling_new/aws_modeling/aws_setup_Run6_87pc/DFM_OUTPUT_FlowFM_Run6/output_shp/Run6_output.shp',extra_fields=  \
#    [('wse',wse),('wse0831',wse0831),('wse_max',wse_max),('depth',dep),('depth0831',dep0831),('depth_max',dep_max)])
# Run5 
#g.write_cells_shp('/mnt/output_shp_dflow/TX_new/Run5_output.shp',extra_fields=  \
#    [('wse',wse),('wse0831',wse0831),('wse_max',wse_max),('depth',dep),('depth0831',dep0831),('depth_max',dep_max)])

# NC modeling
g.write_cells_shp('/mnt/WORK/output_shp_dflow/NC/NC_output.shp',extra_fields=  \
    [('wse',wse),('wse1013',wse1013),('wse_max',wse_max),('depth',dep),('depth1013',dep1013),('depth_max',dep_max)])

