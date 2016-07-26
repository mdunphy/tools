# Copyright 2016 The Salish Sea NEMO Project and
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

"""Functions for common model visualisations
"""

from matplotlib import patches
import matplotlib.pyplot as plt
import numpy as np

from salishsea_tools import geo_tools


def contour_thalweg(
    axes, var, bathy, lons, lats, mesh_mask, mesh_mask_depth_var, clevels,
    cmap='hsv', land_colour='burlywood', xcoord_distance=True,
    thalweg_file='/data/nsoontie/MEOPAR/tools/bathymetry/thalweg_working.txt'
):
    """Contour the data stored in var along the domain thalweg.

    :arg axes: Axes instance to plot thalweg contour on.
    :type axes: :py:class:`matplotlib.axes.Axes`

    :arg var: Salish Sea NEMO model results variable to be contoured
    :type var: :py:class:`numpy.ndarray`

    :arg bathy: Salish Sea NEMO model bathymetry data
    :type bathy: :py:class:`numpy.ndarray`

    :arg lons: Salish Sea NEMO model longitude grid data
    :type lons: :py:class:`numpy.ndarray`

    :arg lats: Salish Sea NEMO model latitude grid data
    :type lats: :py:class:`numpy.ndarray`

    :arg mesh_mask: Salish Sea NEMO model mesh_mask data
    :type mesh_mask: :py:class:`netCDF4.Dataset`

    :arg str mesh_mask_depth_var: name of depth variable in :kbd:`mesh_mask`
                                  that is appropriate for :kbd:`var`.

    :arg clevels: argument for determining contour levels. Choices are
                  1. 'salinity' or 'temperature' for pre-determined levels
                  used in nowcast.
                  2. an integer N, for N automatically determined levels.
                  3. a sequence V of contour levels, which must be in
                  increasing order.
    :type clevels: str or int or iterable

    :arg str cmap: matplotlib colormap

    :arg str land_colour: matplotlib colour for land

    :arg xcoord_distance: plot along thalweg distance (True) or index (False)
    :type xcoord_distance: boolean

    :arg thalweg_pts_file: Path and file name to read the array of
                           thalweg grid points from.
    :type thalweg_pts_file: str

    :returns: matplotlib colorbar object
    """
    thalweg_pts = np.loadtxt(thalweg_file, delimiter=' ', dtype=int)
    depth = mesh_mask.variables[mesh_mask_depth_var][:]
    dep_thal, distance, var_thal = load_thalweg(
        depth[0, ...], var, lons, lats, thalweg_pts)
    if xcoord_distance:
        xx_thal = distance
        axes.set_xlabel('Distance along thalweg [km]')
    else:
        xx_thal, _ = np.meshgrid(np.arange(var_thal.shape[-1]), dep_thal[:, 0])
        axes.set_xlabel('Thalweg index')
    # Determine contour levels
    clevels_default = {
        'salinity': [
            26, 27, 28, 29, 30, 30.2, 30.4, 30.6, 30.8, 31, 32, 33, 34
        ],
        'temperature': [
            6.9, 7, 7.5, 8, 8.5, 9, 9.8, 9.9, 10.3, 10.5, 11, 11.5, 12,
            13, 14, 15, 16, 17, 18, 19
        ]
    }
    if isinstance(clevels, str):
        try:
            clevels = clevels_default[clevels]
        except KeyError:
            raise KeyError('no default clevels defined for {}'.format(clevels))
    # Prepare for plotting by filling in grid points just above bathymetry
    var_plot = _fill_in_bathy(var_thal, mesh_mask, thalweg_pts)
    mesh = axes.contourf(xx_thal, dep_thal, var_plot, clevels, cmap=cmap,
                         extend='both')
    _add_bathy_patch(xx_thal, bathy, thalweg_pts, axes, color=land_colour)
    cbar = plt.colorbar(mesh, ax=axes)
    axes.set_ylabel('Depth [m]')
    return cbar


def _add_bathy_patch(xcoord, bathy, thalweg_pts, ax, color, zmin=450):
    """Add a polygon shaped as the land in the thalweg section

    :arg xcoord: x grid along thalweg
    :type xcoord: 2D numpy array

    :arg bathy: Salish Sea NEMO model bathymetry data
    :type bathy: :py:class:`numpy.ndarray`

    :arg thalweg_pts: Salish Sea NEMO model grid indices along thalweg
    :type thalweg_pts: 2D numpy array

    :arg ax:  Axes instance to plot thalweg contour on.
    :type ax: :py:class:`matplotlib.axes.Axes`

    :arg str color: color of bathymetry patch

    :arg zmin: minimum depth for plot in meters
    :type zmin: float
    """
    # Look up bottom bathymetry along thalweg
    thalweg_bottom = bathy[thalweg_pts[:, 0], thalweg_pts[:, 1]]
    # Construct bathy polygon
    poly = np.zeros((thalweg_bottom.shape[0]+2, 2))
    poly[0, :] = 0, zmin
    poly[1:-1, 0] = xcoord[0, :]
    poly[1:-1:, 1] = thalweg_bottom
    poly[-1, :] = xcoord[0, -1], zmin
    ax.add_patch(patches.Polygon(poly, facecolor=color, edgecolor=color))


def load_thalweg(depths, var, lons, lats, thalweg_pts):
    """Returns depths, cummulative distance and variable along thalweg.

    :arg depths: depth array for variable. Can be 1D or 3D.
    :type depths: :py:class:`numpy.ndarray`

    :arg var: 3D Salish Sea NEMO model results variable
    :type var: :py:class:`numpy.ndarray`

    :arg lons: Salish Sea NEMO model longitude grid data
    :type lons: :py:class:`numpy.ndarray`

    :arg lats: Salish Sea NEMO model latitude grid data
    :type lats: :py:class:`numpy.ndarray`

    :arg thalweg_pts: Salish Sea NEMO model grid indices along thalweg
    :type thalweg_pts: 2D numpy array

    :returns: dep_thal, xx_thal, var_thal, all the same shape
              (depth, thalweg length)
    """

    lons_thal = lons[thalweg_pts[:, 0], thalweg_pts[:, 1]]
    lats_thal = lats[thalweg_pts[:, 0], thalweg_pts[:, 1]]
    var_thal = var[:, thalweg_pts[:, 0], thalweg_pts[:, 1]]

    xx_thal = geo_tools.distance_along_curve(lons_thal, lats_thal)
    xx_thal = xx_thal + np.zeros(var_thal.shape)

    if depths.ndim > 1:
        dep_thal = depths[:, thalweg_pts[:, 0], thalweg_pts[:, 1]]
    else:
        _, dep_thal = np.meshgrid(xx_thal[0, :], depths)
    return dep_thal, xx_thal, var_thal


def _fill_in_bathy(variable, mesh_mask, thalweg_pts):
    """For each horizontal point in variable, fill in first vertically masked
    point with the value just above.
    Use mbathy in mesh_mask file to determine level of vertical masking

    :arg variable: the variable to be filled
    :type variable: 2D numpy array

    :arg mesh_mask: Salish Sea NEMO model mesh_mask data
    :type mesh_mask: :py:class:`netCDF4.Dataset`

    :arg thalweg_pts: Salish Sea NEMO model grid indices along thalweg
    :type thalweg_pts: 2D numpy array

    :returns: newvar, the filled numpy array
    """
    mbathy = mesh_mask.variables['mbathy'][0, :, :]
    newvar = np.copy(variable)

    mbathy = mbathy[thalweg_pts[:, 0], thalweg_pts[:, 1]]
    for i, level in enumerate(mbathy):
        newvar[level, i] = variable[level-1, i]
    return newvar


def plot_tracers(time_ind, ax, qty, DATA, clim=[0, 35, 1], cmap='jet', zorder=0):
    """Plot a horizontal slice of NEMO tracers as filled contours.
    
    *This function could be generalized in the following ways:*
    1. vertical/horizontal cross-sections
    2. grid/map coordinates
    3. contourf/pcolormesh
    4. non-ERDDAP flexibility
    
    :arg time_ind: Time index to plot from timeseries
        (ex. 'YYYY-mmm-dd HH:MM:SS', format is flexible)
    :type time_ind: str
    
    :arg ax: Axis object
    :type ax: :py:class:`matplotlib.pyplot.axes`
    
    :arg qty: Tracer quantity to be plotted (one of 'salinity', 'temperature')
    :type qty: str
    
    :arg DATA: NEMO model results dataset
    :type DATA: :py:class:`xarray.Dataset`
    
    :arg clim: Contour limits and spacing (ex. [min, max, spacing])
    :type clim: list or tuple of float
    
    :arg cmap: Colormap
    :type cmap: str
    
    :arg zorder: Plotting layer specifier
    :type zorder: integer
    
    :returns: Filled contour object
    :rtype: :py:class:`matplotlib.pyplot.contourf`
    """
    
    # NEMO horizontal tracers
    C = ax.contourf(DATA['lon'], DATA['lat'],
        np.ma.masked_values(DATA[qty].sel(time=time_ind, method='nearest'), 0),
        range(clim[0], clim[1], clim[2]), cmap=cmap, zorder=zorder)
    
    return C


def plot_velocity(time_ind, ax, DATA, model='NEMO', spacing=5,
        processed=False, color='black', scale=10, headwidth=1, zorder=5):
    """Plot a horizontal slice of NEMO or GEM velocities as quiver objects.
    Accepts subsampled u and v fields via the **processed** keyword
    argument.
    
    *This function could be generalized in the following ways:*
    1. vertical/horizontal cross-sections
    2. grid/map coordinates
    3. quiver/streamfunction
    4. non_ERDDAP flexibility
    
    :arg time_ind: Time index to plot from timeseries
        (ex. 'YYYY-mmm-dd HH:MM:SS', format is flexible)
    :type time_ind: str
    
    :arg ax: Axis object
    :type ax: :py:class:`matplotlib.pyplot.axes`
    
    :arg DATA: Model results dataset
    :type DATA: :py:class:`xarray.Dataset`
    
    :arg model: Specify model (either NEMO or GEM)
    :type model: str
    
    :arg spacing: Vector spacing
    :type spacing: integer
    
    :arg processed: If True, only coordinate variables will be spaced
    :type processed: bool
    
    :arg color: Vector face color
    :type color: str
    
    :arg scale: Vector length (factor of 1/scale)
    :type scale: integer
    
    :arg headwidth: Vector width
    :type headwidth: integer
    
    :arg zorder: Plotting layer specifier
    :type zorder: integer
    
    :returns: Matplotlib quiver object
    :rtype: :py:class:`matplotlib.pyplot.quiver`
    """
    
    # Determine whether to space vectors
    spc = spacing
    if processed: spc = 1
    
    if model is 'NEMO':
        u = 'u_vel'
        v = 'v_vel'
        start = 1
    elif model is 'GEM':
        u = 'u_wind'
        v = 'v_wind'
        start = 0
    else:
        raise ValueError('Unknown model type: {}'.format(model))
    
    # NEMO horizontal currents
    Q = ax.quiver(
        DATA['lon'][start::spacing, start::spacing],
        DATA['lat'][start::spacing, start::spacing],
        np.ma.masked_values(
            DATA[u].sel(time=time_ind, method='nearest'), 0)[::spc, ::spc],
        np.ma.masked_values(
            DATA[v].sel(time=time_ind, method='nearest'), 0)[::spc, ::spc],
        color=color, edgecolor='k', scale=scale, linewidth=0.5,
        headwidth=headwidth, zorder=zorder)
    
    return Q


def plot_drifters(time_ind, ax, drifters, zorder=15):
    """
    """
    
    # Define color palette
    palette = ['blue', 'teal', 'cyan', 'green', 'lime', 'darkred', 'red',
               'orange', 'magenta', 'purple', 'black', 'dimgray', 'saddlebrown',
               'blue', 'teal', 'cyan', 'green', 'lime', 'darkred', 'red',
               'orange', 'magenta', 'purple', 'black', 'dimgray', 'saddlebrown']
    
    # Plot drifters
    L = collections.OrderedDict()
    P = collections.OrderedDict()
    for i, drifter in enumerate(drifters.keys()):
        # Compare timestep with available drifter data
        dtime = [pd.Timestamp(t.to_pandas()).to_datetime() - time_ind
                 for t in drifters[drifter].time[[0, -1]]]
        # Show drifter track if data is within time threshold
        if (dtime[0].total_seconds() < 3600 and   # 1 hour before deployment
            dtime[1].total_seconds() > -86400):   # 24 hours after failure
            L[drifter] = ax.plot(
                drifters[drifter].lon.sel(time=time_ind, method='nearest'),
                drifters[drifter].lat.sel(time=time_ind, method='nearest'),
                '-', linewidth=2, color=palette[i], zorder=zorder)
            P[drifter] = ax.plot(
                drifters[drifter].lon.sel(time=time_ind, method='nearest'),
                drifters[drifter].lat.sel(time=time_ind, method='nearest'),
                'o', color=palette[i], zorder=zorder+1)
        else: # Hide if outside time threshold
            L[drifter] = ax.plot(
                [], [], '-', linewidth=2, color=palette[i], zorder=zorder)
            P[drifter] = ax.plot(
                [], [], 'o', color=palette[i], zorder=zorder+1)
    
    return L, P
