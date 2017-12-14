import os
import datetime
import io # python io.
import numpy as np
import pandas as pd
import re
import xarray as xr
import six

import logging

log=logging.getLogger('delft.io')

from . import waq_scenario as waq
from ... import utils

def parse_his_file(fn):
    """
    you probably want mon_his_file_dataframe() or bal_his_file_dataframe()
    --
    parse mixed ascii/binary history files as output by delwaq.
    applies to both monitoring output and balance output.
        
    returns tuple:
      sim_descs - descriptive text from inp file.
      time0 - text line giving time origin and units
      regions - names of regions with numeric index (1-based as read from file)
      fields - names of fields, separate into substance and process
      frames - actual data, and timestamps
    """
    fp=open(fn,'rb') 

    sim_descs=np.fromfile(fp,'S40',4)
    time0=sim_descs[3]

    n_fields,n_regions=np.fromfile(fp,'i4',2)

    fdtype=np.dtype( [ ('sub','S10'),
                       ('proc','S10') ] )

    fields=np.fromfile( fp, fdtype, n_fields)

    regions=np.fromfile(fp,
                        [('num','i4'),('name','S20')],
                        n_regions)

    # assume that data is 'f4'
    # following other Delft output, probably each frame is prepended by
    # 'i4' time index
    frame_dtype=np.dtype( [('tsec','i4'),
                           ('data','f4',(n_regions,n_fields))] )
    frames=np.fromfile(fp,frame_dtype)

    return sim_descs,time0,regions,fields,frames

def bal_his_file_dataframe(fn):
    sim_descs,time0,regions,fields,frames = parse_his_file(fn)

    n_regions=len(regions)
    n_fields=len(fields)
    cols=[]
    tuples=[]

    for ri,region in enumerate(regions):
        for fi,field in enumerate(fields):
            tuples.append( (region['name'].strip(),
                            field['sub'].strip(),
                            field['proc'].strip()) )

    col_index=pd.MultiIndex.from_tuples(tuples,names=('region','sub','proc'))
    df=pd.DataFrame(data=frames['data'].reshape( (-1,n_regions*n_fields) ),
                    index=frames['tsec'],
                    columns=col_index)
    return df


def his_file_xarray(fn,region_exclude=None,region_include=None):
    """
    Read a delwaq balance file, return the result as an xarray.
    region_exclude: regular expression for region names to omit from the result
    region_include: regular expression for region names to include.  

    Defaults to returning all regions.
    """
    sim_descs,time_meta,regions,fields,frames = parse_his_file(fn)

    def decstrip(s):
        try:
            s=s.decode() # in case binary
        except AttributeError:
            pass
        return s.strip()

    ds=xr.Dataset()

    ds['descs']=( ('n_desc',), [decstrip(s) for s in sim_descs])

    time0,time_unit = parse_time0(time_meta)
    times=time0 + time_unit*frames['tsec']
    ds['time']=( ('time',), times)
    ds['tsec']=( ('time',), frames['tsec'])

    region_names=[decstrip(s) for s in regions['name']]
    subs=[decstrip(s) for s in np.unique(fields['sub'])]
    procs=[decstrip(s) for s in np.unique(fields['proc'])]

    if region_include:
        region_mask=np.array( [bool(re.match(region_include,region))
                               for region in region_names] )
    else:
        region_mask=np.ones(len(region_names),np.bool8)

    if region_exclude:
        skip=[bool(re.match(region_exclude,region))
              for region in region_names]
        region_mask &= ~np.array(skip)

    sub_proc=[]
    for s,p in fields:
        if decstrip(p):
            sub_proc.append("%s,%s"%(decstrip(s),decstrip(p)))
        else:
            sub_proc.append(decstrip(s))

    region_idxs=np.nonzero(region_mask)[0]
    ds['region']=( ('region',), [region_names[i] for i in region_idxs] )
    ds['sub']  =( ('sub',), subs)
    ds['proc'] =( ('proc',), procs)
    ds['field']=( ('field',), sub_proc)

    ds['bal']=( ('time','region','field'),
                frames['data'][:,region_mask,:] )
    return ds

# older name - xarray version doesn't discriminate between balance
# and monitoring output
bal_his_file_xarray=his_file_xarray

def mon_his_file_dataframe(fn):
    df=bal_his_file_dataframe(fn)
    df.columns=df.columns.droplevel(2) # drop process level
    return df


def inp_tok(fp):
    # tokenizer for parsing rules of delwaq inp file.
    # parses either single-quoted strings, or space-delimited literals.
    for line in fp:
        if ';' in line:
            line=line[ : line.index(';')]
        # pattern had been
        # r'\s*((\'[^\']+\')|([/:-a-zA-Z_#0-9\.]+))'
        # but that has a bad dash before a, and doesn't permit +, either.
        matches=re.findall(r'\s*((\'[^\']+\')|([-/:a-zA-Z_#+0-9\.]+))', line)
        for m in matches:
            yield m[0]


            
def parse_inp_monitor_locations(inp_file):
    """
    returns areas[name]=>[seg1,...] , transects[name]=>[+-exch1, ...]
    ONE-BASED return values.
    """
    with open(inp_file,'rt') as fp:
        tokr=inp_tok(fp)

        while next(tokr)!='#1':
            continue
        for _ in range(4):  # clock/date formats, integration float
            next(tokr)
        for t in tokr:
            if re.match(r'[-_a-zA-Z]+',t):
                continue
            break
        # t is now start timestep
        for _ in range(3):
            next(tokr) # stop, time step time step
        areas={}
        if int(next(tokr)) == 1: # monitoring points used
            nmon = int(next(tokr))
            for imon in range(nmon):
                name, segcount=next(tokr),int(next(tokr))
                segs=[int(next(tokr)) for iseg in range(segcount)]
                areas[name.strip("'")]=segs
        transects={} # name => list of signed, 1-based exchanges
        if int(next(tokr)) == 1: # transects used
            ntrans=int(next(tokr))
            for itrans in range(ntrans):
                name,style,ecount = next(tokr),next(tokr),int(next(tokr))
                exchs=[int(next(tokr)) for _ in range(ecount)]
                transects[name.strip("'")]=exchs
    return areas,transects

def parse_inp_transects(inp_file):
    # with open(inp_file,'rt') as fp:
    #     tokr=inp_tok(fp)
    # 
    #     while next(tokr)!='#1':
    #         continue
    #     for _ in range(4):  # clock/date formats, integration float
    #         next(tokr)
    #     for t in tokr:
    #         if re.match(r'[-_a-zA-Z]+',t):
    #             continue
    #         break
    #     # t is now start timestep
    #     for _ in range(3):
    #         next(tokr) # stop, time step time step
    #     if int(next(tokr)) == 1: # monitoring points used
    #         nmon = int(next(tokr))
    #         for imon in range(nmon):
    #             name, segcount=next(tokr),int(next(tokr))
    #             for iseg in range(segcount):
    #                 next(tokr)
    #     transects={} # name => list of signed, 1-based exchanges
    #     if int(next(tokr)) == 1: # transects used
    #         ntrans=int(next(tokr))
    #         for itrans in range(ntrans):
    #             name,style,ecount = next(tokr),next(tokr),int(next(tokr))
    #             exchs=[int(next(tokr)) for _ in range(ecount)]
    #             transects[name.strip("'")]=exchs
    
    areas,transects=parse_inp_monitor_locations(inp_file)
    
    return transects

def parse_time0(time0):
    """ return a np.datetime64 for the time stamp, and the time unit in seconds
    (almost always equal to 1 second)
    input format is: b'T0: 2012/08/07-00:00:00  (scu=       1s)'
    """
    try:
        time0=time0.decode()
    except AttributeError:
        pass

    m=re.match(r'T0:\s+(\S+)\s+\(scu=\s*(\d+)(\w+)\)',time0)
    dt = m.group(1)
    # make it clear it's UTC:
    dt=dt.replace('-','T').replace('/','-') + "Z"
    origin=np.datetime64(dt)
    unit=np.timedelta64(int(m.group(2)),m.group(3)) 

    return (origin, unit)


# just a start.  And really this stuff should be rolled into the Scenario
# class, so it builds up a Scenario
def parse_boundary_conditions(inp_file):
    with open(inp_file,'rt') as fp:
        tokr=inp_tok(fp)

        while next(tokr)!='#4':
            continue

        bcs=[]
        while 1:
            tok = next(tokr)
            if tok[0] in "-0123456789":
                n_thatcher = int(tok)
                break
            else:
                bc_id=str_or_num
                bc_typ=next(tokr)
                bc_grp=next(tokr)
                bcs.append( (bc_id,bc_typ,bc_grp) )


def read_pli(fn,one_per_line=True):
    """
    Parse a polyline file a la DFM inputs.
    Return a list of features:
    [  (feature_label, N*M values, N labels), ... ]
    where the first two columns are typically x and y, but there may be
    more columns depending on the usage.  If no labels are in the file,
    the list of labels will be all empty strings.

    Generally assumes that the file is honest about the number of fields,
    but some files (like boundary condition pli) will add a text label for 
    each node.

    one_per_line: for files which add a label to each node but say nothing of 
      this in the number of fields, one_per_line=True will assume that each line
      of the text file has exactly one node, and any extra text becomes the label.
    """
    features=[]
    
    with open(fn,'rt') as fp:
        if not one_per_line:
            toker=inp_tok(fp)
            token=lambda: six.next(toker)

            while True:
                try:
                    label=token()
                except StopIteration:
                    break
                nrows=int(token())
                ncols=int(token())
                geometry=[]
                node_labels=[]
                for row in range(nrows):
                    rec=[float(token()) for c in range(ncols)]
                    geometry.append(rec)
                    node_labels.append("") 
                features.append( (label, np.array(geometry), node_labels) )
        else: # line-oriented approach which can handle unannounced node labels
            while True:
                label=fp.readline().strip()
                if label=="":
                    break
                nrows,ncols = [int(s) for s in fp.readline().split()]
                geometry=[]
                node_labels=[]
                for row in range(nrows):
                    values=fp.readline().strip().split(None,ncols+1)
                    geometry.append( [float(s) for s in values[:ncols]] )
                    if len(values)>ncols:
                        node_labels.append(values[ncols])
                    else:
                        node_labels.append("")
                features.append( (label, np.array(geometry), node_labels) )
                
    return features

def write_pli(file_like,pli_data):
    """
    Reverse of read_pli.  
    file_like: a string giving the name of a file to be opened (clobbering
    an existing file), or a file-like object.
    pli_data: [ (label, N*M values, [optional N labels]), ... ]
    typically first two values of each row are x and y, and the rest depend on intended 
    usage of the file
    """
    if hasattr(file_like,'write'):
        fp=file_like
        do_close=False
    else:
        fp=open(file_like,'wt')
        do_close=True
        
    try:
        for feature in pli_data:
            label,data = feature[:2]
            data=np.asanyarray(data)
            if len(feature)==3:
                node_labels=feature[2]
            else:
                node_labels=[""]*len(data)
                
            fp.write("%s\n"%label)
            fp.write("     %d     %d\n"%data.shape)
            if len(data) != len(node_labels):
                raise Exception("%d nodes, but there are %d node labels"%(len(data),
                                                                          len(node_labels)))
            block="\n".join( [ "  ".join(["%15s"%d for d in row]) + "   " + node_label
                               for row,node_label in zip(data,node_labels)] )
            fp.write(block)
            fp.write("\n")
    finally:
        if do_close:
            fp.close()

def grid_to_pli_data(g,node_fields,labeler=None):
    """
    UnstructuredGrid => PLI translation
    translate the edges of g into a list of features as returned
    by read_pli()
    features are extracted as contiguous linestrings, as long as possible.
    node_fields is a list giving a subset of the grid's node fields to
    be written out, in addition to x and y.
    labeler: leave as None to get Lnnn style labels.  Otherwise, a function
       which takes the index, and returns a string for the label.
    """
    strings=g.extract_linear_strings()

    features=[]

    labeler=labeler or (lambda i: "L%04d"%i)

    for feat_i,nodes in enumerate(strings):
        label=labeler(feat_i)

        cols=[ g.nodes['x'][nodes,0], g.nodes['x'][nodes,1] ]

        for fld in node_fields:
            cols.append( g.nodes[fld][nodes] )
        feature=np.array( cols ).T
        features.append( (label,feature) )
    return features

def add_suffix_to_feature(feat,suffix):
    """
    Utility method, takes a feature as returned by read_pli
    (name,
     [ [x0,y0],[x1,y1],...],
     { [node_label0,node_label1,...] }  # optional
    )
    
    and adds a suffix to the name of the feature and the 
    names of nodes if they exist
    """
    name=feat[0]
    suffize=lambda s: s.replace(name,name+suffix)
    feat_suffix=[suffize(feat[0]), feat[1]] # points stay the same
    if len(feat)==3: # includes names for nodes
        feat_suffix.append( [suffize(s) for s in feat[2]] )
    return feat_suffix



def read_map(fn,hyd,use_memmap=True,include_grid=True):
    """
    Read binary D-Water Quality map output, returning an xarray dataset.

    fn: path to .map file
    hyd: path to .hyd file describing the hydrodynamics.
    use_memmap: use memory mapping for file access.  Currently
      this must be enabled.

    include_grid: the returned dataset also includes grid geometry, suitable
       for unstructured_grid.from_ugrid(ds)

    note that missing values at this time are not handled - they'll remain as
    the delwaq standard -999.0.
    """
    if not isinstance(hyd,waq.Hydro):
        hyd=waq.HydroFiles(hyd)

    nbytes=os.stat(fn).st_size # 420106552 

    with open(fn,'rb') as fp:

        # header line of 160 characters
        txt_header=fp.read(160)
        # print "Text header: ",txt_header

        # 4 bytes, maybe a little-endian int.  0x0e, that's 14, number of substances
        n_subs=np.fromfile(fp,np.int32,1)[0]
        # print "# substances: %d"%n_subs

        n_segs=np.fromfile(fp,np.int32,1)[0]
        # print "Nsegs: %d"%n_segs

        substance_names=np.fromfile(fp,'S20',n_subs)


        # not sure if there is a quicker way to get the number of layers
        hyd.infer_2d_elements()
        n_layers=1+hyd.seg_k.max()

        g=hyd.grid() # ignore message about ugrid.

        assert g.Ncells()*n_layers == n_segs

        # I'm hoping that now we get 4 byte timestamps in reference seconds,
        # and then n_subs,n_segs chunks.
        # looks that way.
        data_start=fp.tell()

    bytes_left=nbytes-data_start 
    framesize=(4+4*n_subs*n_segs)
    nframes,extra=divmod(bytes_left,framesize)
    if extra!=0:
        log.warning("Reading map file %s: bad length %d extra bytes (or %d missing)"%(
            fn,extra,framesize-extra))

    # Specify nframes in cases where the filesizes don't quite match up.
    mapped=np.memmap(fn,[ ('tsecs','i4'),
                          ('data','f4',(n_layers,hyd.n_2d_elements,n_subs))] ,
                     mode='r',
                     shape=(nframes,),
                     offset=data_start)

    ds=xr.Dataset()

    try:
        txt_header=txt_header.decode()
    except AttributeError:
        pass # Hopefully header is already a string
    ds.attrs['header']=txt_header

    # a little python 2/3 misery
    try:
        substance_names=[s.decode() for s in substance_names]
    except AttributeError:
        pass
    
    ds['sub']= ( ('sub',), [s.strip() for s in substance_names] )

    times=utils.to_dt64(hyd.time0) + np.timedelta64(1,'s') * mapped['tsecs']

    ds['time']=( ('time',), times)
    ds['t_sec']=( ('time',), mapped['tsecs'] )

    for idx,name in enumerate(ds.sub.values):
        ds[name]= ( ('time','layer','face'), 
                    mapped['data'][...,idx] )
        ds[name].attrs['_FillValue']=-999

    if include_grid:
        # not sure why this doesn't work.
        g.write_to_xarray(ds=ds)

    return ds

def map_add_z_coordinate(map_ds,total_depth='TotalDepth',coord_type='sigma',
                         layer_dim='layer'):
    """
    For an xarray representation of dwaq output, where the total depth
    has been recorded, add an inferred vertical coordinate in the dataset.
    This is necessary to allow the ugrid visit reader to understand
    the file.
    Currently only sigma coordinates, assumed to be evenly spaced, are
    supported.

    total_depth: Name of the xarray variable in map_ds holding total water column
    depth for each segment.
    coord_type: type of coordinate, currently must be "sigma".
    layer_dim: name of the vertical dimension in the data.

    Makes an arbitrary assumption that the first output time step is roughly
    mean sea level.  Obviously wrong, but a starting point.

    Modifies map_ds in place, also returning it.
    """
    assert coord_type=='sigma'

    bedlevel=-map_ds.TotalDepth.isel(**{layer_dim:0,'time':0,'drop':True})
    dry=(bedlevel==999)
    bedlevel[dry]=0.0
    map_ds['bedlevel']=bedlevel
    map_ds.bedlevel.attrs['units']='m'
    map_ds.bedlevel.attrs['positive']='up'
    map_ds.bedlevel.attrs['long_name']='Bed elevation relative to initial water level'

    tdepth=map_ds.TotalDepth.isel(**{layer_dim:0,'drop':True})
    eta=tdepth + map_ds.bedlevel
    eta.values[ tdepth.values==-999 ] = 0.0
    map_ds['eta']=eta
    map_ds.eta.attrs['units']='m'
    map_ds.eta.attrs['positive']='up'
    map_ds.eta.attrs['long_name']='Sea surface elevation relative initial time step'

    Nlayers=len(map_ds[layer_dim])
    map_ds['sigma']=(layer_dim,), (0.5+np.arange(Nlayers)) / float(Nlayers)
    map_ds.sigma.attrs['standard_name']="ocean_sigma_coordinate"
    map_ds.sigma.attrs['positive']='up'
    map_ds.sigma.attrs['units']=""
    map_ds.sigma.attrs['formula_terms']="sigma: sigma eta: eta  bedlevel: bedlevel"
    
    return map_ds

def dfm_wind_to_nc(wind_u_fn,wind_v_fn,nc_fn):
    """
    Transcribe DFM 'arcinfo' style gridded wind to
    CF compliant netcdf file (ready for import to erddap)

    wind_u_fn:
      path to the amu file for eastward wind
    wind_v_fn:
      path to the amv file for northward wind
    nc_fn:
      path to the netcdf file which will be created.
    """
    fp_u=open(wind_u_fn,'rt')
    fp_v=open(wind_v_fn,'rt')

    # read the header, gathering parameters in a dict.
    def parse_header(fp):
        params={}
        while 1:
            line=fp.readline().strip()
            if line.startswith('### START OF HEADER'):
                break
        for line in fp:
            line=line.strip()
            if line.startswith('#'):
                if line.startswith('### END OF HEADER'):
                    break
                continue # comment lines
            key,value = line.split('=',2)
            key=key.strip()
            value=value.strip()

            # some hardcoded data type conversion:
            if key in ['n_rows','n_cols']:
                value=int(value)
            elif key in ['dx','dy','x_llcorner','y_llcorner','NODATA_value']:
                value=float(value)
            params[key]=value
        return params

    fp_u.seek(0)
    fp_v.seek(0)
    u_header=parse_header(fp_u)
    v_header=parse_header(fp_v)

    # make sure they match up
    for k in u_header.keys():
        if k in ['quantity1']:
            continue
        assert u_header[k] == v_header[k]

    # use netCDF4 directly, so we can stream it to disk
    import netCDF4

    os.path.exists(nc_fn) and os.unlink(nc_fn)
    nc=netCDF4.Dataset(nc_fn,'w') # don't worry about netcdf versions quite yet

    xdim='x'
    ydim='y'
    tdim='time'

    nc.createDimension(xdim,u_header['n_cols'])
    nc.createDimension(ydim,u_header['n_rows'])
    nc.createDimension(tdim,None) # unlimited

    # assign some attributes while we're at it
    for k in ['FileVersion','Filetype','dx','dy','grid_unit','unit1','x_llcorner','y_llcorner']:
        setattr(nc,k,u_header[k])

    # cf conventions suggest this order of dimensions
    u_var = nc.createVariable('wind_u',np.float32,[tdim,ydim,xdim],
                              fill_value=u_header['NODATA_value'])
    v_var = nc.createVariable('wind_v',np.float32,[tdim,ydim,xdim],
                              fill_value=v_header['NODATA_value'])
    t_var = nc.createVariable('time',np.float64,[tdim])


    # install some metadata

    # parse the times into unix epochs for consistency
    t_var.units='seconds since 1970-01-01T00:00:00Z'
    t_var.calendar = "proleptic_gregorian"

    # Going to assume that we're working out of the same UTM 10:
    utm_var = nc.createVariable('UTM10',np.int32,[])
    utm_var.grid_mapping_name = "universal_transverse_mercator" 
    utm_var.utm_zone_number = 10
    utm_var.semi_major_axis = 6378137
    utm_var.inverse_flattening = 298.257 
    utm_var._CoordinateTransformType = "Projection" 
    utm_var._CoordinateAxisTypes = "GeoX GeoY" 
    utm_var.crs_wkt = """PROJCS["NAD83 / UTM zone 10N",
        GEOGCS["NAD83",
            DATUM["North_American_Datum_1983",
                SPHEROID["GRS 1980",6378137,298.257222101,
                    AUTHORITY["EPSG","7019"]],
                TOWGS84[0,0,0,0,0,0,0],
                AUTHORITY["EPSG","6269"]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.0174532925199433,
                AUTHORITY["EPSG","9122"]],
            AUTHORITY["EPSG","4269"]],
        PROJECTION["Transverse_Mercator"],
        PARAMETER["latitude_of_origin",0],
        PARAMETER["central_meridian",-123],
        PARAMETER["scale_factor",0.9996],
        PARAMETER["false_easting",500000],
        PARAMETER["false_northing",0],
        UNIT["metre",1,
            AUTHORITY["EPSG","9001"]],
        AXIS["Easting",EAST],
        AXIS["Northing",NORTH],
        AUTHORITY["EPSG","26910"]]
    """

    y_var=nc.createVariable('y',np.float64,[ydim])
    y_var.units='m'
    y_var.long_name="y coordinate of projection"
    y_var.standard_name="projection_y_coordinate"
    y_var[:]=u_header['y_llcorner'] + u_header['dy']*np.arange(u_header['n_rows'])

    x_var=nc.createVariable('x',np.float64,[xdim])
    x_var.units='m'
    x_var.long_name="x coordinate of projection"
    x_var.standard_name="projection_x_coordinate"
    x_var[:]=u_header['x_llcorner'] + u_header['dx']*np.arange(u_header['n_cols'])

    u_var.units='m s-1'
    u_var.grid_mapping='transverse_mercator'
    u_var.long_name='eastward wind from F Ludwig method'
    u_var.standard_name='eastward_wind'

    v_var.units='m s-1'
    v_var.grid_mapping='transverse_mercator'
    v_var.long_name='northward wind from F Ludwig method'
    v_var.standard_name='northward_wind'

    def read_frame(fp,header):
        # Assumes that the TIME line is alone,
        # but the pixel data isn't restricted to a particular number of elements per line.
        time_line=fp.readline()
        if not time_line:
            return None,None

        assert time_line.startswith('TIME')
        _,time_string=time_line.split('=',2)
        count=0
        items=[]
        expected=header['n_cols'] * header['n_rows']
        for line in fp:
            this_data=np.fromstring(line,sep=' ',dtype=np.float32)
            count+=len(this_data)
            items.append(this_data)
            if count==expected:
                break
            assert count<expected

        block=np.concatenate( items ).reshape( header['n_rows'],header['n_cols'] )

        time=utils.to_dt64(time_string)
        return time,block

    frame_i=0
    while 1:
        u_time,u_block = read_frame(fp_u,u_header)
        v_time,v_block = read_frame(fp_v,v_header)
        if u_time is None or v_time is None:
            break

        assert u_time==v_time

        if frame_i%96==0:
            print("%d frames, %s most recent"%(frame_i,u_time))
        u_var[frame_i,:,:] = u_block
        v_var[frame_i,:,:] = v_block
        t_var[frame_i] = u_time

        # t... come back to it.
        frame_i+=1

    nc.close()


def dataset_to_dfm_wind(ds,period_start,period_stop,target_filename_base,
                        extra_header=None,min_records=1):
    """
    Write wind in an xarray dataset to a pair of gridded meteo files for DFM.

    ds:
      xarray dataset.  Currently fairly brittle assumptions on the format of
      this dataset, already in the proper coordinates system, coordinates of x and 
      y, and the wind variables named wind_u and wind_v.
    period_start,period_stop: 
      include data from the dataset on or after period_start, and up to period_stop.
    target_filename_base:
      the path and filename for output, without the .amu and .amv extensions.
    extra_header: 
      extra text to place in the header.  This is included as is, with the exception that
      a newline will be added if it's missing

    returns the number of available records overlapping the requested period.
    If that number is less than min_records, no output is written.
    """
    time_idx_start, time_idx_stop = np.searchsorted(ds.time,[period_start,period_stop])

    record_count=time_idx_stop-time_idx_start
    if record_count<min_records:
        return record_count
    
    # Sanity checks that there was actually some overlapping data.
    # maybe with min_records, this can be relaxed?  Unsure of use case there.
    assert time_idx_start+1<len(ds.time)
    assert time_idx_stop>0
    assert time_idx_start<time_idx_stop
        
    nodata=-999

    if extra_header is None:
        extra_header=""
    else:
        extra_header=extra_header.rstrip()+"\n"
        
    header_template="""### START OF HEADER
# Created with %(creator)s
%(extra_header)sFileVersion = 1.03
Filetype = meteo_on_equidistant_grid
NODATA_value = %(nodata)g
n_cols = %(n_cols)d
n_rows = %(n_rows)d
grid_unit = m
x_llcorner = %(x_llcorner)g
y_llcorner = %(y_llcorner)g
dx = %(dx)g
dy = %(dy)g
n_quantity = 1
quantity1 = %(quantity)s
unit1 = m s-1
### END OF HEADER
"""

    fp_u=open(target_filename_base+".amu",'wt')
    fp_v=open(target_filename_base+".amv",'wt')

    base_fields=dict(creator="stompy",nodata=nodata,
                     n_cols=len(ds.x),n_rows=len(ds.y),
                     dx=np.median(np.diff(ds.x)),
                     dy=np.median(np.diff(ds.y)),
                     x_llcorner=ds.x[0],
                     y_llcorner=ds.y[0],
                     extra_header=extra_header,
                     quantity='x_wind')

    for fp,quant in [ (fp_u,'x_wind'),
                      (fp_v,'y_wind') ]:
        # Write the headers:
        fields=dict(quantity=quant)
        fields.update(base_fields)
        header=header_template%fields
        fp.write(header)

    for time_idx in range(time_idx_start, time_idx_stop):
        if (time_idx-time_idx_start) % 96 == 0:
            print("Written %d/%d time steps"%( time_idx-time_idx_start,time_idx_stop-time_idx_start))
        u=ds.wind_u.isel(time=time_idx)
        v=ds.wind_v.isel(time=time_idx)
        t=ds.time.isel(time=time_idx)

        # write a time line formatted like this:
        # TIME=00000.000000 hours since 2012-08-01 00:00:00 +00:00
        time_line="TIME=%f seconds since 1970-01-01 00:00:00 +00:00"%utils.to_unix(t.values)

        for fp,data in [ (fp_u,u),
                         (fp_v,v) ]:
            # double check order.
            fp.write(time_line) ; fp.write("\n")
            for row in data.values:
                fp.write(" ".join(["%g"%rowcol for rowcol in row]))
                fp.write("\n")

    fp_u.close()
    fp_v.close()
    return record_count

class SectionedConfig(object):
    """ 
    Handles reading and writing of config-file like formatted files.
    Follows some of the API of the standard python configparser
    """
    inline_comment_prefixes=('#',';')
    
    def __init__(self,filename=None,text=None):
        """ 
        filename: path to file to open and parse
        text: a string containing the entire file to parse
        """
        self.sources=[] # maintain a list of strings identifying where values came from
        self.rows=[]    # full text of each line
        
        if filename is not None:
            self.read(filename)

        if text is not None:
            fp = StringIO(text)
            self.read(fp,'text')

    def read(self, filename, label=None):
        if six.PY2:
            file_base = file
        else:
            file_base = io.IOBase
            
        if isinstance(filename, file_base):
            label = label or 'n/a'
            fp=filename
            filename=None
        else:
            fp = open(filename,'rt')
            label=label or filename

        self.sources.append(label)

        for line in fp:
            # save original text so we can write out a new mdu with
            # only minor changes
            # the rstrip()s leave trailing whitespace, but strip newline or CR/LF
            self.rows.append(line.rstrip("\n").rstrip("\r"))
        if filename:
            fp.close()

    def entries(self):
        """ 
        Generator which iterates over rows, parsing them into index, section, key, value, comment.

        key is always present, but might indicate a section by including square
        brackets.
        value may be a string, or None.  Strings will be trimmed
        comment may be a string, or None.  It includes the leading comment character.
        """
        section=None
        for idx,row in enumerate(self.rows):
            parsed=self.parse_row(row)
            
            if parsed[0] is None: # blank line
                continue # don't send back blank rows
            
            if parsed[0][0]=='[':
                section=parsed[0]

            yield [idx,section] + list(parsed)
                
    def parse_row(self,row):
        section_patt=r'^(\[[A-Za-z0-9 ]+\])([#;].*)?$'
        value_patt = r'^([A-Za-z0-9_]+)\s*=([^#;]*)([#;].*)?$'
        blank_patt = r'^\s*([#;].*)?$'
        
        m_sec = re.match(section_patt, row)
        if m_sec is not None:
            return m_sec.group(1), None, m_sec.group(2)

        m_val = re.match(value_patt, row)
        if m_val is not None:
            return m_val.group(1), m_val.group(2).strip(), m_val.group(3)

        m_cmt = re.match(blank_patt, row)
        if m_cmt is not None:
            return None,None,m_cmt.group(1)

        print("Failed to parse row:")
        print(row)

    def get_value(self,sec_key):
        """
        return the string-valued settings for a given key.  
        if they key is not found, returns None.  
        If the key is present but with no value, returns the empty string
        """
        section='[%s]'%sec_key[0].lower()
        key = sec_key[1].lower()

        for row_idx,row_sec,row_key,row_value,row_comment in self.entries():
            if (row_key.lower() == key) and (section.lower() == row_sec.lower()):
                return row_value
        else:
            return None

    def set_value(self,sec_key,value):
        # set value and optionally comment.
        # sec_key: tuple of section and key (section without brackets)
        # value: either the value (a string, or something that can be converted via str())
        #   or a tuple of value and comment, without the leading comment character
        section='[%s]'%sec_key[0].lower()
        key=sec_key[1]
        
        if isinstance(value,tuple):
            value,comment=value
            comment='# ' + comment
        else:
            comment=None

        value=self.val_to_str(value)
        
        for row_idx,row_sec,row_key,row_value,row_comment in self.entries():
            if (row_key.lower() == key.lower()) and (section.lower() == row_sec.lower()):
                comment = comment or row_comment or ""
                self.rows[row_idx] = "%-18s= %-20s %s"%(row_key,value,comment)
                return

        # have to append it
        if section!=row_sec:
            self.rows.append(section)
        self.rows.append("%s = %s %s"%(row_key,value,comment or ""))
        
    def __setitem__(self,sec_key,value):
        self.set_value(sec_key,value)
    def __getitem__(self,sec_key): 
        return self.get_value(sec_key)
    
    def val_to_str(self,value):
        # make sure that floats are formatted with plenty of digits:
        # and handle annoyance of standard Python types vs. numpy types
        # But None stays None, as it gets handled specially elsewhere
        if value is None:
            return None
        if isinstance(value,float) or isinstance(value,np.floating):
            return "%.12g"%value
        else:
            return str(value)

    def write(self,filename):
        """
        Write this config out to a text file
        filename: defaults to self.filename
        check_changed: if True, and the file already exists and is not materially different,
          then do nothing.  Good for avoiding unnecessary changes to mtimes.
        backup: if true, copy any existing file to <filename>.bak
        """
        with open(filename,'wt') as fp:
            for line in self.rows:
                fp.write(line)
                fp.write("\n")
    
class MDUFile(SectionedConfig):
    """
    Read/write MDU files, with an interface similar to python's
    configparser, but better support for discerning and retaining
    comments
    """
    def time_range(self):
        """
        return tuple of t_ref,t_start,t_stop
        as np.datetime64
        """
        t_ref=utils.to_dt64( datetime.datetime.strptime(self['time','RefDate'],'%Y%m%d') )

        if self['time','Tunit'].lower() == 'm':
            tunit=np.timedelta64(1,'m')
        else:
            raise Exception("TODO: allow other time units")

        t_start = t_ref+int(self['time','tstart'])*tunit
        t_stop = t_ref+int(self['time','tstop'])*tunit
        return t_ref,t_start,t_stop
