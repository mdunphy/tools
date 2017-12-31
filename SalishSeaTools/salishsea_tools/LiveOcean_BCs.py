# Copyright 2013-2018 The Salish Sea NEMO Project and
# The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# A module to interpolate Live Ocean results onto Salish Sea NEMO grid and
# save boundary forcing files.

import datetime
import logging
import os

import mpl_toolkits.basemap as Basemap
import netCDF4 as nc
import numpy as np
import xarray as xr
from salishsea_tools import LiveOcean_grid as grid
from salishsea_tools import gsw_calls
from scipy import interpolate

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------- Interpolation functions ------------------------
def load_SalishSea_boundary_grid(imin, imax, rim, meshfilename):
    """Load the Salish Sea NEMO model boundary depth, latitudes and longitudes.

    :arg imin int: first grid point of western boundary

    :arg imax int: one past last grid point of western boundary

    :arg rim int: rim width, note rim starts at second grid point

    :arg fname str: name of boundary file

    :returns: numpy arrays depth, lon, lat and a tuple shape
    """

    with nc.Dataset(meshfilename) as meshfile:
        lonBC = meshfile.variables['nav_lon'][imin:imax, 1:rim + 1]
        latBC = meshfile.variables['nav_lat'][imin:imax, 1:rim + 1]
        depBC = meshfile.variables['gdept_1d'][0]

    shape = lonBC.shape

    return depBC, lonBC, latBC, shape


def load_LiveOcean(
    date,
    LO_dir='/results/forcing/LiveOcean/downloaded/',
    LO_file='low_passed_UBC.nc'
):
    """Load a time series of Live Ocean results represented by a date,
    location and filename

    :arg date: date as yyyy-mm-dd
    :type date: str

    :arg LO_dir: directory of Live Ocean file
    :type LO_dir: str

    :arg LO_file: Live Ocean filename
    :type LO_file: str

    :returns: xarray dataset of Live Ocean results
    """
    # Choose file and load
    sdt = datetime.datetime.strptime(date, '%Y-%m-%d')
    file = os.path.join(LO_dir, sdt.strftime('%Y%m%d'), LO_file)

    G, S, T = grid.get_basic_info(file)  # note: grid.py is from Parker
    d = xr.open_dataset(file)

    # Determine z-rho (depth)
    zeta = d.zeta.values[0]
    z_rho = grid.get_z(G['h'], zeta, S)
    # Add z_rho to dataset
    zrho_DA = xr.DataArray(
        np.expand_dims(z_rho, 0),
        dims=['ocean_time', 's_rho', 'eta_rho', 'xi_rho'],
        coords={
            'ocean_time': d.ocean_time.values[:],
            's_rho': d.s_rho.values[:],
            'eta_rho': d.eta_rho.values[:],
            'xi_rho': d.xi_rho.values[:]
        },
        attrs={
            'units': 'metres',
            'positive': 'up',
            'long_name': 'Depth at s-levels',
            'field': 'z_rho ,scalar'
        }
    )
    d = d.assign(z_rho=zrho_DA)

    return d


def interpolate_to_NEMO_depths(
    dataset, depBC, var_names=['salt', 'temp', 'NO3']
):
    """ Interpolate variables in var_names from a Live Ocean dataset to NEMO
    depths. LiveOcean land points (including points lower than bathymetry) are
    set to np.nan and then masked.

    :arg dataset: Live Ocean dataset
    :type dataset: xarray Dataset

    :arg depBC: NEMO model depths
    :type depBC: 1D numpy array

    :arg var_names: list of Live Ocean variable names to be interpolated,
                    e.g ['salt', 'temp']
    :type var_names: list of str

    :returns: dictionary containing interpolated numpy arrays for each variable
    """
    interps = {}
    for var_name in var_names:
        var_interp = np.zeros(dataset[var_name][0].shape)
        for j in range(var_interp.shape[1]):
            for i in range(var_interp.shape[2]):
                LO_depths = dataset.z_rho.values[0, :, j, i]
                var = dataset[var_name].values[0, :, j, i]
                var_interp[:, j, i] = np.interp(
                    -depBC, LO_depths, var, left=np.nan
                )
                # NEMO depths are positive, LiveOcean are negative
        interps[var_name] = np.ma.masked_invalid(var_interp)

    return interps


def remove_south_of_Tatoosh(interps, imask=6, jmask=17):
    """Removes points south of Tatoosh point because the water masses there
    are different"

    :arg interps: dictionary of 3D numpy arrays.
                  Key represents the variable name.
    :type var_arrrays: dictionary

    :arg imask: longitude points to be removed
    :type imask: int

    :arg jmask: latitude points to be removed
    :type jmask: int

    :returns: interps with values south-west of Tatoosh set to Nan.
    """

    for var in interps.keys():
        for i in range(6):
            for j in range(17):
                interps[var][:, i, j] = np.nan

    interps[var] = np.ma.masked_invalid(interps[var][:])

    return interps


def fill_box(interps, maxk=35):
    """Fill all NaN in the LiveOcean with nearest points (constant depth),
    go as far down as maxk

    :arg interps: dictionary of 3D numpy arrays.
                  Key represents the variable name.
    :type interps: dictionary

    :arg maxk: maximum Live Ocean depth with data
    :type maxk: int

    :returns interps with filled values
    """

    for var in interps.keys():
        for k in range(maxk):
            array = np.ma.masked_invalid(interps[var][k])
            xx, yy = np.meshgrid(
                range(interps[var].shape[2]), range(interps[var].shape[1])
            )
            x1 = xx[~array.mask]
            y1 = yy[~array.mask]
            newarr = array[~array.mask]
            interps[var][k] = interpolate.griddata((x1, y1),
                                                   newarr.ravel(), (xx, yy),
                                                   method='nearest')
    return interps


def convect(sigma, interps):
    """Convect interps based on density (sigma).
    Ignores variations in cell depths and convects vertically

    :arg interps: dictionary of 3D numpy arrays.
                  Key represents the variable name.
    :type interps: dictionary

    :arg sigma: sigma-t, density, 3D array
    :type sigma: numpy array

    :returns sigma, interps stabilized
    """

    var_names = interps.keys()
    kmax, imax, jmax = sigma.shape
    good = False
    while not good:
        good = True
        for k in range(kmax - 1):
            for i in range(imax):
                for j in range(jmax):
                    if sigma[k, i, j] > sigma[k + 1, i, j]:
                        good = False
                        for var in var_names:
                            interps[var][k, i, j], interps[var][
                                k + 1, i, j
                            ] = interps[var][k + 1, i, j], interps[var][k, i, j
                                                                        ]
                        sigma[k, i, j], sigma[k + 1, i, j] = sigma[
                            k + 1, i, j
                        ], sigma[k, i, j]
    return sigma, interps


def extend_to_depth(interps, maxk=35):
    """Fill all values below level with LiveOcean data with data from above
    start at maxk

    :arg interps: dictionary of 3D numpy arrays.
                  Key represents the variable name.
    :type interps: dictionary

    :arg maxk: maximum Live Ocean depth with data
    :type maxk: int

    :returns interps extended to depth
    """

    for var in interps.keys():
        interps[var][maxk:] = interps[var][maxk - 1]

    return interps


def interpolate_to_NEMO_lateral(interps, dataset, NEMOlon, NEMOlat, shape):
    """Interpolates arrays in interps laterally to NEMO grid.
    Assumes these arrays have already been interpolated vertically.
    Note that by this point interps should be a full array

    :arg interps: dictionary of 4D numpy arrays.
                  Key represents the variable name.
    :type interps: dictionary

    :arg dataset: LiveOcean results. Used to look up lateral grid.
    :type dataset: xarray Dataset

    :arg NEMOlon: array of NEMO boundary longitudes
    :type NEMOlon: 1D numpy array

    :arg NEMOlat: array of NEMO boundary longitudes
    :type NEMOlat: 1D numpy array

    :arg shape: the lateral shape of NEMO boundary area.
    :type shape: 2-tuple

    :returns: a dictionary, like var_arrays, but with arrays replaced with
              interpolated values
    """
    # LiveOcean grid
    lonsLO = dataset.lon_rho.values[0, :]
    latsLO = dataset.lat_rho.values[:, 0]
    # interpolate each variable
    interpl = {}
    for var in interps.keys():
        var_new = np.zeros((interps[var].shape[0], shape[0], shape[1]))
        for k in range(var_new.shape[0]):
            var_grid = interps[var][k, :, :]
            var_new[k, ...] = Basemap.interp(
                var_grid, lonsLO, latsLO, NEMOlon, NEMOlat
            )
        interpl[var] = var_new
    return interpl


def calculate_Si_from_NO3(NO3):
    """Use a simple fit to calculate Si from NO3

    :arg NO3: 3-D array of nitate values
    :type NO3: array

    :returns: a 3-D array of silicon values
    """
    a, b, c = 0, 1.03, 0.015
    Si = a + b * NO3 + c * NO3**2

    return Si


def prepare_dataset(interpl, var_meta, LO_to_NEMO_var_map, depBC, time):
    """Prepare xarray dataset for Live Ocean file

    :arg interpl: dictionary of 4D numpy arrays.
                  Key represents the variable name.
    :type interpl: dictionary SSS

    :arg var_meta: metadata for each variable in var_arrays.
                   Keys are NEMO variable names.
    :type var_meta: a dictionary of dictionaries with key-value pairs of
                    metadata

    :arg LO_to_NEMO_var_map: a dictionary mapping between LO variable names
                             (keys) and NEMO variable names (values)
    :type LO_to_NEMO_var_map: a dictionary with string key-value pairs

    :arg depBC: NEMO model depths
    :type depBC: 1D numpy array

    :arg time: time from Live Ocean dataset
    :type time: float

    returns dataset
    """

    # Add some global attributes
    ds_attrs = {
        'acknowledgements':
            'Live Ocean http://faculty.washington.edu/pmacc/LO/LiveOcean.html',
        'creator_email':
            'sallen@eoas.ubc.ca',
        'creator_name':
            'Salish Sea MEOPAR Project Contributors',
        'creator_url':
            'https://salishsea-meopar-docs.readthedocs.org/',
        'institution':
            'UBC EOAS',
        'institution_fullname': (
            'Earth, Ocean & Atmospheric Sciences,'
            ' University of British Columbia'
        ),
        'summary': (
            'Temperature, Salinity and Nitrate from the Live Ocean model'
            ' interpolated in space onto the Salish Sea NEMO Model'
            ' western open boundary. Silicon from Nitrate.'
        ),
        'source': (
            'http://nbviewer.jupyter.org/urls/bitbucket.org/'
            'salishsea/.../LiveOceanNew'
        ),
        'history': (
            '[{}] File creation.'
            .format(datetime.datetime.today().strftime('%Y-%m-%d'))
        )
    }

    da = {}
    for var in interpl.keys():
        da[var] = xr.DataArray(
            data=interpl[var],
            name=LO_to_NEMO_var_map[var],
            dims=('time_counter', 'deptht', 'yb', 'xbT'),
            coords={
                'time_counter': time,
                'deptht': depBC,
                'yb': [1],
                'xbT': np.arange(interpl[var].shape[3])
            },
            attrs=var_meta[LO_to_NEMO_var_map[var]]
        )

    ds = xr.Dataset(
        data_vars={
            'vosaline': da['salt'],
            'votemper': da['temp'],
            'NO3': da['NO3'],
            'Si': da['Si']
        },
        coords={
            'time_counter': time,
            'deptht': depBC,
            'yb': [1],
            'xbT': np.arange(interpl['salt'].shape[3])
        },
        attrs=ds_attrs
    )

    return ds


def write_out_file(ds, date, basename, bc_dir):
    """Write out the Live Ocean Data File

    :arg ds: xarray dataset containing data
    :type ds: xarray dataset

    :arg date: date for file
    :type date: str

    :arg basename: basename for file
    :type basename: str

    :arg bc_dir: directory for boundary condition file
    :type bc_dir: str
    """

    sdt = datetime.datetime.strptime(date, '%Y-%m-%d')
    filename = '{}_{}.nc'.format(basename, sdt.strftime('y%Ym%md%d'))
    filepath = os.path.join(bc_dir, filename)
    encoding = {var: {'zlib': True} for var in ds.data_vars}
    encoding['time_counter'] = {'units': 'minutes since 1970-01-01 00:00'}

    ds.to_netcdf(
        path=filepath,
        unlimited_dims=('time_counter'),
        encoding=encoding,
    )
    logger.debug('Saved {}'.format(filename))

    return filepath


# ------------------ Creation of files ------------------------------


def create_LiveOcean_TS_BCs(
    date,
    basename='LiveOcean_v201712',
    meshfilename='/results/nowcast-sys/grid/mesh_mask201702.nc',
    bc_dir='/results/forcing/LiveOcean/boundary_conditions/',
    LO_dir='/results/forcing/LiveOcean/downloaded/',
):
    """Create a Live Ocean boundary condition file for date
    for use in the NEMO model.

    :arg str date: date in format 'yyyy-mm-dd'

    :arg str basename: the base name of the saved files.
                       Eg. basename='LO', file_frequency='daily' saves files as
                       'LO_yYYYYmMMdDD.nc'

    :arg str bc_dir: the directory in which to save the results.

    :arg str LO_dir: the directory in which Live Ocean results are stored.

    :returns: Boundary conditions files that were created.
    :rtype: list
    """

    # Create metadeta for temperature and salinity
    # (Live Ocean variables, NEMO grid)
    var_meta = {
        'vosaline': {
            'grid': 'SalishSea2',
            'long_name': 'Practical Salinity',
            'units': 'psu'
        },
        'votemper': {
            'grid': 'SalishSea2',
            'long_name': 'Potential Temperature',
            'units': 'deg C'
        },
        'NO3': {
            'grid': 'SalishSea2',
            'long_name': 'Nitrate',
            'units': 'muM'
        },
        'Si': {
            'grid': 'SalishSea2',
            'long_name': 'Nitrate',
            'units': 'muM'
        },
    }

    # Mapping from LiveOcean TS names to NEMO TS names
    LO_to_NEMO_var_map = {
        'salt': 'vosaline',
        'temp': 'votemper',
        'NO3': 'NO3',
        'Si': 'Si'
    }

    # Load BC information
    depBC, lonBC, latBC, shape = load_SalishSea_boundary_grid(
        imin=376 - 1, imax=470, rim=10, meshfilename=meshfilename
    )

    # Load the Live Ocean File
    d = load_LiveOcean(date)

    # Depth interpolation
    interps = interpolate_to_NEMO_depths(d, depBC)

    # Change to TEOS-10
    var_meta, interps['salt'], interps['temp'] = _convert_TS_to_TEOS10(
        var_meta, interps['salt'], interps['temp']
    )

    # Remove South of Tatoosh
    interps = remove_south_of_Tatoosh(interps)

    # Fill whole LiveOcean data box horizontally
    interps = fill_box(interps)

    # Caculate the density (sigma) and convect
    sigma = gsw_calls.generic_gsw_caller(
        'gsw_sigma0.m', [interps['salt'][:], interps['temp'][:]]
    )
    sigma, interps = convect(sigma, interps)

    # Fill Live Ocean Vertically
    interps = extend_to_depth(interps)

    # Interpolate Laterally onto NEMO grid
    interpl = interpolate_to_NEMO_lateral(interps, d, lonBC, latBC, shape)

    # Convect Again
    sigmal = gsw_calls.generic_gsw_caller(
        'gsw_sigma0.m', [interpl['salt'][:], interpl['temp'][:]]
    )
    sigmal, interpl = convect(sigmal, interpl)

    # Rework indexes for NEMO
    for var in interpl.keys():
        interpl[var] = np.swapaxes(interpl[var], 1, 2)
        interpl[var] = interpl[var].reshape(
            1, interpl[var].shape[0], 1,
            interpl[var].shape[2] * interpl[var].shape[1]
        )

    # Calculate Si from NO3
    interpl['Si'] = calculate_Si_from_NO3(interpl['NO3'])

    # Prepare dataset
    ts = d.ocean_time.data
    ds = prepare_dataset(interpl, var_meta, LO_to_NEMO_var_map, depBC, ts)

    # Write out file
    filepath = write_out_file(ds, date, basename, bc_dir)
    return filepath


def _convert_TS_to_TEOS10(var_meta, sal, temp):
    """Convert Practical Salinity and potential temperature to Reference
       Salinity and Conservative Temperature using gsw matlab functions.

    :arg var_meta: dictionary of metadata for salinity and temperature.
                   Must have keys vosaline and votemper, each with a sub
                   dictionary with keys long_name and units
    :type var_meta: dictionary of dictionaries

    :arg sal: salinity data
    :type sal: numpy array

    :arg temp: temperature daya
    :type temp: numpy array

    :returns: updated meta data, salinity and temperature"""
    # modify metadata
    new_meta = var_meta.copy()
    new_meta['vosaline']['long_name'] = 'Reference Salinity'
    new_meta['vosaline']['units'] = 'g/kg'
    new_meta['votemper']['long_name'] = 'Conservative Temperature'
    # Convert salinity from practical to reference salinity
    sal_ref = gsw_calls.generic_gsw_caller('gsw_SR_from_SP.m', [
        sal[:],
    ])
    # Convert temperature from potential to conservative
    temp_cons = gsw_calls.generic_gsw_caller(
        'gsw_CT_from_pt.m', [
            sal_ref[:],
            temp[:],
        ]
    )
    return new_meta, sal_ref, temp_cons
