#Define a function that gets the constituent data from the csv file

def get_data_from_csv(tidevar, constituent, depth):
    import pandas as pd
    from math import radians
    import numpy

    theta = radians(29) #rotation of the grid = 29 degrees
    
    #WATER LEVEL ELEVATION
    if tidevar == 'T':
        webtide = pd.read_csv('/ocean/klesouef/meopar/tools/I_ForcingFiles/Tidal Elevation Constituents T.csv',\
                              skiprows = 2)
        webtide = webtide.rename(columns={'Constituent': 'const', 'Longitude': 'lon', 'Latitude': 'lat', \
                                          'Amplitude (m)': 'amp', 'Phase (deg GMT)': 'pha'})

	#how long is the boundary?
	boundlen = len(depth[depth!=0])

	#along western boundary, etaZ1 and etaZ2 are 0 in masked cells
        amp_W = numpy.zeros((boundlen+10,1))
        pha_W = numpy.zeros((boundlen+10,1))

        #find the boundary
        I = numpy.where(depth!=0)
        
        #allocate the M2 phase and amplitude from Webtide to the boundary cells
        #(CHECK: Are these allocated in the right order?)
        amp_W[5:boundlen+5,0] = webtide[webtide.const==(constituent+':')].amp
        pha_W[5:boundlen+5,0] = webtide[webtide.const==(constituent+':')].pha
        
        #convert the phase and amplitude to cosine and sine format that NEMO likes
        Z1 = amp_W*numpy.cos(numpy.radians(pha_W))
        Z2 = amp_W*numpy.sin(numpy.radians(pha_W))

    #U VELOCITY
    if tidevar == 'U': 
        webtide = pd.read_csv('/ocean/klesouef/meopar/tools/I_ForcingFiles/Tidal Current Constituents U.csv',\
                                 skiprows = 2)
        webtide = webtide.rename(columns={'Constituent': 'const', 'Longitude': 'lon', 'Latitude': 'lat', \
                                          'U Amplitude (m)': 'ewamp', 'U Phase (deg GMT)': 'ewpha',\
                                          'V Amplitude (m)': 'nsamp', 'V Phase (deg GMT)': 'nspha'})

	#how long is the boundary?
	boundlen = len(depth[depth!=0])	

        #Convert amplitudes from north/south u/v into grid co-ordinates
        
        #Convert phase from north/south into grid co-ordinates (see docs/tides/tides_data_acquisition for details)
        ua_ugrid = numpy.array(webtide[webtide.const==(constituent+':')].ewamp)
        va_ugrid = numpy.array(webtide[webtide.const==(constituent+':')].nsamp)
        uphi_ugrid = numpy.radians(numpy.array(webtide[webtide.const==(constituent+':')].ewpha))
        vphi_ugrid = numpy.radians(numpy.array(webtide[webtide.const==(constituent+':')].nspha))
        
        uZ1 = ua_ugrid*numpy.cos(theta)*numpy.cos(uphi_ugrid) - va_ugrid*numpy.sin(theta)*numpy.sin(vphi_ugrid)
        uZ2 = ua_ugrid*numpy.cos(theta)*numpy.sin(uphi_ugrid) + va_ugrid*numpy.sin(theta)*numpy.sin(vphi_ugrid)
        
        #find the boundary
        I = numpy.where(depth!=0)
        
        #allocate the z1 and z2 I calculated from Webtide to the boundary cells
        #along western boundary, etaZ1 and etaZ2 are 0 in masked cells
        #(CHECK: Are these allocated in the right order?)
        Z1 = numpy.zeros((boundlen+10,1))
        Z2 = numpy.zeros((boundlen+10,1))
        Z1[5:boundlen+5,0] = uZ1
        Z2[5:boundlen+5,0] = uZ2
        
    #V VELOCITY
    if tidevar == 'V':
        webtide = pd.read_csv('/ocean/klesouef/meopar/tools/I_ForcingFiles/Tidal Current Constituents V.csv',\
                              skiprows = 2)
        webtide = webtide.rename(columns={'Constituent': 'const', 'Longitude': 'lon', 'Latitude': 'lat', \
                                          'U Amplitude (m)': 'ewamp', 'U Phase (deg GMT)': 'ewpha',\
                                          'V Amplitude (m)': 'nsamp', 'V Phase (deg GMT)': 'nspha'})
	#how long is the boundary?
	boundlen = len(depth[depth!=0])   
	print(boundlen) 

        #Convert phase from north/south into grid co-ordinates (see docs/tides/tides_data_acquisition for details)
        ua_vgrid = numpy.array(webtide[webtide.const==(constituent+':')].ewamp)
        va_vgrid = numpy.array(webtide[webtide.const==(constituent+':')].nsamp)
        uphi_vgrid = numpy.radians(numpy.array(webtide[webtide.const==(constituent+':')].ewpha))
        vphi_vgrid = numpy.radians(numpy.array(webtide[webtide.const==(constituent+':')].nspha))
        
        vZ1 = -ua_vgrid*numpy.sin(theta)*numpy.cos(uphi_vgrid) - va_vgrid*numpy.cos(theta)*numpy.sin(vphi_vgrid)
        vZ2 = -ua_vgrid*numpy.sin(theta)*numpy.sin(uphi_vgrid) + va_vgrid*numpy.cos(theta)*numpy.cos(vphi_vgrid)
        
        #find the boundary
        I = numpy.where(depth!=0)
        
        #allocate the z1 and z2 I calculated from Webtide to the boundary cells
        #along western boundary, etaZ1 and etaZ2 are 0 in masked cells
        #(CHECK: Are these allocated in the right order?)
        Z1 = numpy.zeros((boundlen+10,1))
        Z2 = numpy.zeros((boundlen+10,1))
        Z1[5:boundlen+5,0] = vZ1
        Z2[5:boundlen+5,0] = vZ2

    return Z1, Z2, I, boundlen

#Define a function that creates Netcdf files from the following information
# - choose variable (elevation ('T'), u ('U') or v ('V'))
# - choose constituent ('O1', 'P1', 'Q1', 'K1', 'K2', 'N2', 'M2', 'S2')
# - give z1 and z2 data
# - depth data

    
def create_tide_netcdf(tidevar,constituent,depth,number):
    import netCDF4 as NC
    import numpy

    #get the data from the csv file
    Z1, Z2, I, boundlen = get_data_from_csv(tidevar,constituent,depth)
        
    nemo = NC.Dataset('SalishSea'+number+'_west_tide_'+constituent+'_grid_'+tidevar+'.nc','w')
    nemo.description = 'Tide data from WebTide'
    
    # give the netcdf some dimensions
    nemo.createDimension('xb', boundlen+10)
    nemo.createDimension('yb', 1)
    
    # add in the counter around the boundary (taken from Susan's code in Prepare Tide Files)
    xb = nemo.createVariable('xb', 'int32', ('xb',),zlib=True)
    xb.units = 'non dim'
    xb.longname = 'counter around boundary'
    yb = nemo.createVariable('yb', 'int32', ('yb',),zlib=True)
    yb.units = 'non dim'
    xb[:] = numpy.arange(I[0][0]-5,I[0][-1]+6)
    yb[0] = 1
    
    # create i and j grid position
    nbidta = nemo.createVariable('nbidta', 'int32' , ('yb','xb'),zlib=True)
    nbidta.units = 'non dim'
    nbidta.longname = 'i grid position'
    nbjdta = nemo.createVariable('nbjdta', 'int32' , ('yb','xb'),zlib=True)
    nbjdta.units = 'non dim'
    nbjdta.longname = 'j grid position'
    nbrdta = nemo.createVariable('nbrdta', 'int32' , ('yb','xb'),zlib=True)
    nbrdta.units = 'non dim'
    
    # give values for West Boundary (this is where the webtide points go)
    nbidta[:] = 1
    nbjdta[:] = numpy.arange(I[0][0]-5,I[0][-1]+6)
    
    # give values for the corner
    nbrdta[:] = 1
    
    # give values for North Boundary (nothing here at the moment)
    #nbidta[0,a:] = numpy.arange(1,b+1)
    #nbjdta[0,a:] = a
       
    if tidevar=='T':
        z1 = nemo.createVariable('z1','float32',('yb','xb'),zlib=True)
        z1.units = 'm'
        z1.longname = 'tidal elevation: cosine'
        z2 = nemo.createVariable('z2','float32',('yb','xb'),zlib=True)
        z2.units = 'm'
        z2.longname = 'tidal elevation: sine'
        z1[0,0:boundlen+10] = Z1[:,0]
        z2[0,0:boundlen+10] = Z2[:,0]
	print(Z1.size)
	print(z1.size)
	print(z2.size)
        #z1[0,a:] = 0.
        #z2[0,a:] = 0.   
        
    if tidevar=='U':    
        u1 = nemo.createVariable('u1','float32',('yb','xb'),zlib=True)
        u1.units = 'm'
        u1.longname = 'tidal x-velocity: cosine'
        u2 = nemo.createVariable('u2','float32',('yb','xb'),zlib=True)
        u2.units = 'm'
        u2.longname = 'tidal x-velocity: sine'
        u1[0,0:boundlen+10] = Z1[:,0]
        u2[0,0:boundlen+10] = Z2[:,0]
        #u1[0,a:] = 0.
        #u2[0,a:] = 0.   
        
    if tidevar=='V':
        v1 = nemo.createVariable('v1','float32',('yb','xb'),zlib=True)
        v1.units = 'm'
        v1.longname = 'tidal y-velocity: cosine'
        v2 = nemo.createVariable('v2','float32',('yb','xb'),zlib=True)
        v2.units = 'm'
        v2.longname = 'tidal y-velocity: sine'
        v1[0,0:boundlen+10] = Z1[:,0]
        v2[0,0:boundlen+10] = Z2[:,0]
        #v1[0,a:] = 0.
        #v2[0,a:] = 0.   
    
    return Z1, Z2
    nemo.close()


def create_northern_tides(Z1,Z2,tidevar,constituent):
    import netCDF4 as NC
    import numpy as np
    from salishsea_tools import nc_tools
    
    nemo = NC.Dataset('SalishSea2_North_tide_'+constituent+'_grid_'+tidevar+'.nc', 'w', zlib=True)

    #start and end points
    starti = 32
    endi = 62
    lengthi = endi-starti
    #make the boundary 10 cells wide
    r = 10 

    # dataset attributes
    nc_tools.init_dataset_attrs(
        nemo, 
        title='Tidal Boundary Conditions for Northern Boundary', 
        notebook_name='johnstone_strait_tides', 
        nc_filepath='../../../nemo-forcing/open_boundaries/north/SalishSea2_North_tide_'+constituent+'_grid_'+tidevar+'.nc',
        comment='Tidal current and amplitude data from Thomson & Huggett 1980') 

    # dimensions (only need x and y, don't need depth or time_counter)
    nemo.createDimension('xbT', lengthi*r)
    nemo.createDimension('yb', 1)

    # variables
    # nbidta, ndjdta, ndrdta
    nbidta = nemo.createVariable('nbidta', 'int32' , ('yb','xbT'))
    nbidta.long_name = 'i grid position'
    nbidta.units = 1
    nbjdta = nemo.createVariable('nbjdta', 'int32' , ('yb','xbT'))
    nbjdta.long_name = 'j grid position'
    nbjdta.units = 1
    nbrdta = nemo.createVariable('nbrdta', 'int32' , ('yb','xbT'))
    nbrdta.long_name = 'position from boundary'
    nbrdta.units = 1
    
    # values
    # nbidta, nbjdta
    for ir in range(0,r):
        j = 897-ir
        nbidta[0,ir*lengthi:(ir+1)*lengthi] = range(starti,endi)
        nbjdta[0,ir*lengthi:(ir+1)*lengthi] = j
        nbrdta[0,ir*lengthi:(ir+1)*lengthi] = ir

    if tidevar=='T':
        z1 = nemo.createVariable('z1','float32',('yb','xbT'),zlib=True)
        z1.units = 'm'
        z1.long_name = 'tidal elevation: cosine'
        z2 = nemo.createVariable('z2','float32',('yb','xbT'),zlib=True)
        z2.units = 'm'
        z2.long_name = 'tidal elevation: sine'
        z1[0,:] = np.array([Z1]*lengthi*r)
        z2[0,:] = np.array([Z2]*lengthi*r)
        
    if tidevar=='U':    
        u1 = nemo.createVariable('u1','float32',('yb','xbT'),zlib=True)
        u1.units = 'm'
        u1.long_name = 'tidal x-velocity: cosine'
        u2 = nemo.createVariable('u2','float32',('yb','xbT'),zlib=True)
        u2.units = 'm'
        u2.long_name = 'tidal x-velocity: sine'
        u1[0,:] = np.repeat(Z1,10)
        u2[0,:] = np.repeat(Z2,10)
        
    if tidevar=='V':
        v1 = nemo.createVariable('v1','float32',('yb','xbT'),zlib=True)
        v1.units = 'm'
        v1.long_name = 'tidal y-velocity: cosine'
        v2 = nemo.createVariable('v2','float32',('yb','xbT'),zlib=True)
        v2.units = 'm'
        v2.long_name = 'tidal y-velocity: sine'
        v1[0,:] = np.repeat(Z1,10)
        v2[0,:] = np.repeat(Z2,10)

    nc_tools.check_dataset_attrs(nemo)
    nemo.close()










