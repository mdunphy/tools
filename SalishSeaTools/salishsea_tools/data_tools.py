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

"""Functions for loading and processing observational data
"""
from collections import namedtuple
import datetime as dtm
import os

import arrow
import dateutil.parser as dparser
import numpy as np
import scipy.interpolate
import scipy.io


def load_ADCP(
        daterange, station='central',
        adcp_data_dir='/ocean/dlatorne/MEOPAR/ONC_ADCP/',
):
    """Returns the ONC ADCP velocity profiles at a given station
    over a specified daterange.
    
    :arg sequence daterange: Start and end datetimes for the requested data
                             range
                             (e.g. ['yyyy mmm dd', 'yyyy mmm dd']).

    :arg str station: Requested profile location ('central', 'east', or 'ddl')

    :returns: :py:attr:`datetime` attribute holds a :py:class:`numpy.ndarray`
              of data datatime stamps,
              :py:attr:`depth` holds the depth at which the ADCP sensor is
              deployed,
              :py:attr:`u` and :py:attr:`v` hold :py:class:`numpy.ndarray`
              of the zonal and meridional velocity profiles at each datetime.
    :rtype: 4 element :py:class:`collections.namedtuple`
    """
    startdate = dparser.parse(daterange[0])
    enddate = dparser.parse(daterange[1])
    grid = scipy.io.loadmat(
        os.path.join(adcp_data_dir, 'ADCP{}.mat'.format(station)))
    # Generate datetime array
    mtimes = grid['mtime'][0]
    datetimes = np.array([dtm.datetime.fromordinal(int(mtime)) +
                          dtm.timedelta(days=mtime % 1) -
                          dtm.timedelta(days=366) for mtime in mtimes])
    # Find daterange indices
    indexstart = abs(datetimes - startdate).argmin()
    indexend = abs(datetimes - enddate).argmin()
    # Extract time, depth, and velocity vectors
    datetime = datetimes[indexstart:indexend + 1]
    u0 = grid['utrue'][:, indexstart:indexend + 1] / 100  # to m/s
    v0 = grid['vtrue'][:, indexstart:indexend + 1] / 100  # to m/s
    depth = grid['chartdepth'][0]
    u = np.ma.masked_invalid(u0)
    v = np.ma.masked_invalid(v0)
    adcp_data = namedtuple('ADCP_data', 'datetime, depth, u, v')
    return adcp_data(datetime, depth, u, v)


def interpolate_to_depth(
    var, var_depths, interp_depths, var_mask=0, var_depth_mask=0,
):
    """Calculate the interpolated value of var at interp_depth using linear
    interpolation.

    :arg var: Depth profile of a model variable or data quantity.
    :type var: :py:class:`numpy.ndarray`

    :arg var_depths: Depths at which the model variable or data quantity has
                     values.
    :type var_depths: :py:class:`numpy.ndarray`

    :arg interp_depths: Depth(s) at which to calculate the interpolated value
                        of the model variable or data quantity.
    :type var_mask: :py:class:`numpy.ndarray` or number

    :arg var_mask: Mask to use for the model variable or data quantity.
                   For model results it is best to use the a 1D slice of the
                   appropriate mesh mask array;
                   e.g. :py:attr:`tmask` for tracers.
                   Masking the model variable or data quantity increases the
                   accuracy of the interpolation.
                   If var_mask is not provided the model variable or data
                   quantity is zero-masked.
    :type var_mask: :py:class:`numpy.ndarray` or number

    :arg var_depth_mask: Mask to use for the depths.
                         For model results it is best to use the a 1D slice
                         of the appropriate mesh mask array;
                         e.g. :py:attr:`tmask` for tracers.
                         Masking the depths array increases the accuracy of
                         the interpolation.
                         If var_depth_mask is not provided the depths array
                         is zero-masked.
    :type var_mask: :py:class:`numpy.ndarray` or number

    :returns: Value(s) of var linearly interpolated to interp_depths.
    :rtype: :py:class:`numpy.ndarray` or number
    """
    var_mask = (
        var_mask if hasattr(var_mask, 'shape') else var_mask == var_mask)
    var_depth_mask = (
        var_depth_mask if hasattr(var_depth_mask, 'shape')
        else var_depth_mask == var_depth_mask)
    depth_interp = scipy.interpolate.interp1d(
        np.ma.array(var_depths, mask=var_depth_mask),
        np.ma.array(var, mask=var_mask))
    return depth_interp(interp_depths)


def onc_datetime(date_time, timezone='Canada/Pacific'):
    """Return a string representation of a date/time in the particular
    ISO-8601 extended format required by the Ocean Networks Canada (ONC)
    data web services API.

    :arg date_time: Date/time to transform into format required by
                    ONC data web services API.
    :type date_time: str
                     or :py:class:`datetime.datetime`
                     or :py:class:`arrow.Arrow`

    :arg str timezone: Timezone of date_time.

    :returns: UTC date/time formatted as :kbd:`YYYY-MM-DDTHH:mm:ss.SSSZ`
    :rtype: str
    """
    d = arrow.get(date_time)
    d_tz = arrow.get(d.datetime, timezone)
    d_utc = d_tz.to('utc')
    return '{}Z'.format(d_utc.format('YYYY-MM-DDTHH:mm:ss.SSS'))
