# Copyright 2013-2016 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Functions for calculating time-dependent scale factors and depth.

Functions developed/tested in this notebook:
http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-nancy/raw/tip/notebooks/energy_flux/Time-dependent%20depth%20and%20scale%20factors%20-%20development.ipynb

Examples of plotting with output:
http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-nancy/raw/tip/notebooks/energy_flux/Plotting%20with%20time%20dependent%20depths.ipynb

NKS nsoontie@eos.ubc.ca 08-2016
"""

from salishsea_tools import geo_tools
import numpy as np
import progressbar


def calculate_H(e3t0, tmask):
    """Calculate the initial water column thickness (H).

    :arg e3t0: initial vertical scale factors on T-grid.
               Dimensions: (depth, y, x).
    :type e3t0: :py:class:`numpy.ndarray`

    :arg tmask: T-grid mask. Dimensions: (depth, y, x)
    :type tmask: :py:class:`numpy.ndarray`

    :returns: the initial water column thickness. Dimensions: (y, x)

    """

    H = np.sum(e3t0*tmask, axis=0)

    return H


def calculate_adjustment_factor(H, ssh):
    """Calculate the time-dependent adjustment factor for variable volume in
    NEMO. adj = (1+ssh/H) and e3t_t = e3t_0*adj

    :arg H:  Water column thicnkess. Dimension: (y, x)
    :type H: :py:class:`numpy.array`

    :arg ssh: the model sea surface height. Dimensions: (time, y, x)
    :type ssh: :py:class:`numpy.ndarray`

    :returns: the adjustment factor with dimensions (time, y, x)
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        one_over_H = 1 / H
    one_over_H = np.nan_to_num(one_over_H)
    adj = (1 + ssh * one_over_H)
    return adj


def calculate_time_dependent_grid(
    e3t0,
    tmask,
    ssh,
    input_vars,
):
    """ Calculate the time dependent vertical grids and scale factors for
    variable volume in NEMO.

    :arg e3t0: initial vertical scale factors on T-grid.
               Dimensions: (depth, y, x).
    :type e3t0: :py:class:`numpy.ndarray`

    :arg tmask: T-grid mask. Dimensions: (depth, y, x)
    :type tmask: :py:class:`numpy.ndarray`

    :arg ssh: the model sea surface height. Dimensions: (time, y, x)
    :type ssh: :py:class:`numpy.ndarray`

    :arg input_vars: A dictionary of the initial grids/scale factors to be
                     translated into time_dependent. Example keys can be
                     'e3t_0', 'gdept_0', 'e3w_0', 'gdepw_0'. A dictionary with
                     corresponding time-dependent grids is returned, where the
                     keys are now 'e3t_t', 'gdept_t', 'e3w_0', 'gdepw_0'.
    :typ input_vars: dictionary
    :type return_vars: list of strings

    :returns: A dictionary containing the desired time dependent vertical
              scale factors on t and w grids and depths on t and w grids.
              Dimensions of each: (time, depth, y, x)
    """
    # adjustment factors
    H = calculate_H(e3t0, tmask)
    adj = calculate_adjustment_factor(H, ssh)
    adj = np.expand_dims(adj, axis=1)  # expand to give depth dimension
    # Time-dependent grids
    return_vars = {}
    for key in input_vars:
        return_key = '{}t'.format(key[0:-1])
        return_vars[return_key] = input_vars[key] * adj

    return return_vars


def time_dependent_grid_U(e3u0, e1u, e2u, e1t, e2t, umask, ssh, input_vars,
                          return_ssh=False):
    """Calculate time-dependent vertical grid spacing and depths on U-grid for
    variabe volume in NEMO.

    :arg e3u0: initial vertical scale factors on U-grid.
               Dimensions: (depth, y, x).
    :type e3u0: :py:class:`numpy.ndarray`

    :arg e1u: x-direction scale factors on U-grid.
              Dimensions: (y, x).
    :type e1u: :py:class:`numpy.ndarray`

    :arg e2u: y-direction scale factors on U-grid.
              Dimensions: (y, x).
    :type e2u: :py:class:`numpy.ndarray`

    :arg e1t: x-direction scale factors on T-grid.
              Dimensions: (y, x).
    :type e1t: :py:class:`numpy.ndarray`

    :arg e2t: y-direction scale factors on T-grid.
               Dimensions: (y, x).
    :type e2t: :py:class:`numpy.ndarray`

    :arg umask: U-grid mask. Dimensions: (depth, y, x)
    :type umask: :py:class:`numpy.ndarray`

    :arg ssh: the model sea surface height on T-grid. Dimensions: (time, y, x)
    :type ssh: :py:class:`numpy.ndarray`

    :arg input_vars: A dictionary of the initial grids/scale factors to be
                     translated into time-dependent. Example keys can be
                     'e3u_0', 'gdepu_0'. A dictionary with
                     corresponding time-dependent grids is returned, where the
                     keys are now 'e3u_t', 'gdepu_t'.
    :type input_vars: dictionary

    :arg return_ssh: Specifies whether the ssh interpolated to the U-grid
                     should be returned (ssh_u)
    :type return_ssh: boolean

    :returns: A dictionary containing the desired time dependent vertical
              scale factors on depths on u grid.
              Dimensions of each: (time, depth, y, x).
              If returned, ssh_u has dimensions (time, y, x)"""
    ssh_u = np.zeros_like(ssh)
    e1e2u = e1u * e2u
    e1e2t = e1t * e2t
    # Interpolate ssh to u grid
    ssh_u[:, :, 0:-1] = 0.5 * umask[0, :, 0:-1] / e1e2u[:, 0:-1] * (
        e1e2t[:, 0:-1] * ssh[:, :, 0:-1] + e1e2t[:, 1:] * ssh[:, :, 1:]
        )
    H = calculate_H(e3u0, umask)
    adj = calculate_adjustment_factor(H, ssh_u)
    adj = np.expand_dims(adj, axis=1)
    # Time-dependent grids
    return_vars = {}
    for key in input_vars:
        return_key = '{}t'.format(key[0:-1])
        return_vars[return_key] = input_vars[key] * adj
    if return_ssh:
        return_vars['ssh_u'] = ssh_u
    return return_vars


def time_dependent_grid_V(e3v0, e1v, e2v, e1t, e2t, vmask, ssh, input_vars,
                          return_ssh=False):
    """Calculate time-dependent vertical grid spacing and depths on V-grid for
    variabe volume in NEMO.

    :arg e3v0: initial vertical scale factors on V-grid.
               Dimensions: (depth, y, x).
    :type e3v0: :py:class:`numpy.ndarray`

    :arg e1v: x-direction scale factors on V-grid.
              Dimensions: (y, x).
    :type e1v: :py:class:`numpy.ndarray`

    :arg e2v: y-direction scale factors on V-grid.
              Dimensions: (y, x).
    :type e2v: :py:class:`numpy.ndarray`

    :arg e1t: x-direction scale factors on T-grid.
              Dimensions: (y, x).
    :type e1t: :py:class:`numpy.ndarray`

    :arg e2t: y-direction scale factors on T-grid.
               Dimensions: (y, x).
    :type e2t: :py:class:`numpy.ndarray`

    :arg vmask: V-grid mask. Dimensions: (depth, y, x)
    :type vmask: :py:class:`numpy.ndarray`

    :arg ssh: the model sea surface height on T-grid. Dimensions: (time, y, x)
    :type ssh: :py:class:`numpy.ndarray`

    :arg input_vars: A dictionary of the initial grids/scale factors to be
                     translated into time_dependent. Example keys can be
                     'e3v_0', 'gdepv_0'. A dictionary with
                     corresponding time-dependent grids is returned, where the
                     keys are now 'e3v_t', 'gdepv_t'.
    :type input_vars: dictionary

    :arg return_ssh: Specifies whether the ssh interpolated to the V-grid
                     should be returned (ssh_v)
    :type return_ssh: boolean

    :returns: A dictionary containing the desired time dependent vertical
              scale factors and depths on v grid.
              Dimensions of each: (time, depth, y, x).
              If returned, ssh_uvhas dimensions (time, y, x)"""
    ssh_v = np.zeros_like(ssh)
    e1e2v = e1v * e2v
    e1e2t = e1t * e2t
    # Interpolate ssh to V-grid
    ssh_v[:, 0:-1, :] = 0.5 * vmask[0, 0:-1, :] / e1e2v[0:-1, :] * (
        e1e2t[0:-1, :] * ssh[:, 0:-1, :] +
        e1e2t[1:, :] * ssh[:, 1:, :]
        )
    H = calculate_H(e3v0, vmask)
    adj = calculate_adjustment_factor(H, ssh_v)
    adj = np.expand_dims(adj, axis=1)
    # Time-dependent grids
    return_vars = {}
    for key in input_vars:
        return_key = '{}t'.format(key[0:-1])
        return_vars[return_key] = input_vars[key] * adj
    if return_ssh:
        return_vars['ssh_v'] = ssh_v

    return return_vars


def build_GEM_mask(grid_GEM, grid_NEMO, mask_NEMO):
    """
    """

    # Preallocate
    ngrid_GEM = grid_GEM['x'].shape[0] * grid_GEM['y'].shape[0]
    mask_GEM = np.zeros(ngrid_GEM, dtype=int)

    # Evaluate each point on GEM grid
    with progressbar.ProgressBar(max_value=ngrid_GEM) as bar:
        for index, coords in enumerate(zip(
            grid_GEM['nav_lon'].values.reshape(ngrid_GEM) - 360,
            grid_GEM['nav_lat'].values.reshape(ngrid_GEM)
        )):

            j, i = geo_tools.find_closest_model_point(
                coords[0], coords[1],
                grid_NEMO['nav_lon'], grid_NEMO['nav_lat'],
            )
            if j is np.nan or i is np.nan:
                mask_GEM[index] = 0
            else:
                mask_GEM[index] = mask_NEMO[j, i].values

            # Update progress bar
            bar.update(index)

    # Reshape
    mask_GEM = mask_GEM.reshape(grid_GEM['nav_lon'].shape)

    return mask_GEM
