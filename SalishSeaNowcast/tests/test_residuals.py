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

"""Unit tests for Salish Sea NEMO nowcast residuals module.
"""
from datetime import datetime

import pytest
import pytz


@pytest.fixture
def residuals_module(scope='module'):
    from nowcast import residuals
    return residuals


class TestToDatetime:
    """Unit tests for _to_datetime() function.
    """
    @pytest.mark.parametrize('datestr, year, isDec, isJan, expected', [
        ('02/29 00Z', 2016, False, False,
            datetime(2016, 2, 29, 0, 0, tzinfo=pytz.timezone('UTC'))),
        ('01/01 00Z', 2015, True, False,
            datetime(2016, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC'))),
        ('12/31 00Z', 2016, False, True,
            datetime(2015, 12, 31, 0, 0, tzinfo=pytz.timezone('UTC'))),
    ])
    def test_to_datetie(
        self, datestr, year, isDec, isJan, expected, residuals_module,
    ):
        dt = residuals_module._to_datetime(datestr, year, isDec, isJan)
        assert dt == expected
