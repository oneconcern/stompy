from osgeo import gdal


# This scripts only works when xyz is 'gridded' points
def csv2tif(source, target):
    cvs = gdal.Open(source)
    if cvs is None:
        print 'ERROR: Unable to open %s' % source
        return

    geotiff = gdal.GetDriverByName("GTiff")
    if geotiff is None:
        print 'ERROR: GeoTIFF driver not available.'
        return

    options = []
    geotiff.CreateCopy(target, cvs, 0, options)

source = 'data/depth.xyz'
target = 'data/depth.tif'

csv2tif(source, target)