import matplotlib
matplotlib.use("Agg")
from stompy.grid.convert_sun_to_dfm import convert_mesh_suntans_to_dfm
from stompy.grid.tom import Tom
from stompy.grid.tom import ExitException
import sys

# part of step 3
from stompy.model.delft import dfm_grid
import numpy as np
from stompy.spatial import field
import os
import time

start = time.time()

if __name__ == '__main__':


	# Step 1: Create SUNTANS mesh
	suntans_files_loc = "TX_mesh" 
	os.chdir(suntans_files_loc)

	try:
	    Tom().run(sys.argv)
	except ExitException as exc:
	    sys.exit(exc.value)

	print " ------ STEP 1 complete: SUNTANS mesh generated -------"
	

	# Step 2: convert SUNTANS mesh to dfm mesh
	
	suntans_file_name = "TX_test2_net.nc"
	#output_name = suntans_files_loc+"/"+suntans_file_name
	output_name = suntans_file_name

	if os.path.exists(output_name):
		os.remove(output_name)

	convert_mesh_suntans_to_dfm(output_name)

	print " ------ STEP 2 complete: SUNTANS mesh converted to dflow Mesh -------"
	

	# Step 3: burn DEM to the mesh!

	# g=dfm_grid.DFMGrid("../../TX_mesh/TX_test2_net.nc")
	g=dfm_grid.DFMGrid(output_name)
	
	# Load the bathy:
	tiff_name = "shp/"+"TX_UTM15.tif"
	dem=field.GdalGrid(tiff_name)

	# dem.plot() # plot it just to make sure...
	
	# There are some other more specific ways of pulling data out of the
	# DEM, but this is a good starting point -
	depths=dem(g.nodes['x'])
	
	# Be sure to check for NaN
	assert np.sum( np.isnan( depths )) ==0
	
	# Add it to the grid:
	g.add_node_field('depth',depths)
	# or just g.nodes['depth']=depths if that field already exists.
	
	# Write back out
	output_DEM_name = "TX_mesh_DEM_net.nc"
	if os.path.exists(output_DEM_name):
		os.remove(output_DEM_name)

	dfm_grid.write_dfm(g,output_DEM_name)
	
	print " ------ STEP 3 complete: Dem embedded to the mesh -------"

end = time.time()
elapsed = (end-start)/60.0
print("elapsed time is %.2f minutes" % elapsed)