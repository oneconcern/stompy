# Read .his file from delft model

import xarray as xr
from stompy.model.delft import dfm_grid

file_name = 'FlowFM_0000_his.nc'
map_output=xr.open_dataset(file_name)

print map_output.station_id.values[0]

# continue on jupyter notebook