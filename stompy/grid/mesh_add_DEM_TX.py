# Load existing grid:
from stompy.model.delft import dfm_grid
import numpy as np

g=dfm_grid.DFMGrid("../../TX_mesh/TX_test2_net.nc")
from stompy.spatial import field

# Load the bathy:
dem=field.GdalGrid('../../TX_mesh/shp/TX_UTM15.tif')

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
dfm_grid.write_dfm(g,'../../TX_mesh/TX_mesh_DEM_net.nc')
