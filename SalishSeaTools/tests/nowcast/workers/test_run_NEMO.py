# Copyright 2013-2014 The Salish Sea MEOPAR contributors
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

"""Unit tests for the nowcast.run_NEMO module.
"""
from __future__ import division

from datetime import (
    date,
    timedelta,
)
import os

import pytest


@pytest.fixture()
def run_NEMO_module():
    from salishsea_tools.nowcast.workers import run_NEMO
    return run_NEMO


@pytest.mark.use_fixtures(['run_NEMO_module'])
class TestCalcNewNamelistLines(object):
    """Unit tests for calc_new_namelist_lines() function.
    """
    def test_nowcast_it000(self, run_NEMO_module):
        today = date(2014, 12, 14)
        lines = [
            '  nn_it000 = 1\n',
            '  nn_itend = 8640\n',
            '  nn_date0 = 20140910\n',
        ]
        new_lines, prev_itend = run_NEMO_module.calc_new_namelist_lines(
            lines, today)
        assert new_lines[0] == '  nn_it000 = 8641\n'

    def test_nowcast_itend(self, run_NEMO_module):
        today = date(2014, 12, 14)
        lines = [
            '  nn_it000 = 1\n',
            '  nn_itend = 8640\n',
            '  nn_date0 = 20140910\n',
        ]
        new_lines, prev_itend = run_NEMO_module.calc_new_namelist_lines(
            lines, today)
        assert new_lines[1] == '  nn_itend = 17280\n'

    def test_nowcast_prev_itend(self, run_NEMO_module):
        today = date(2014, 12, 14)
        lines = [
            '  nn_it000 = 1\n',
            '  nn_itend = 8640\n',
            '  nn_date0 = 20140910\n',
        ]
        new_lines, prev_itend = run_NEMO_module.calc_new_namelist_lines(
            lines, today)
        assert prev_itend == 8640

    def test_nowcast_no_update_after_today(self, run_NEMO_module):
        today = date(2014, 12, 14)
        lines = [
            '  nn_it000 = 1\n',
            '  nn_itend = 8640\n',
            '  nn_date0 = 20141214\n',
        ]
        new_lines, prev_itend = run_NEMO_module.calc_new_namelist_lines(
            lines, today)
        assert new_lines == lines

    def test_nowcast_no_update_after_today_prev_itend(self, run_NEMO_module):
        today = date(2014, 12, 14)
        lines = [
            '  nn_it000 = 8641\n',
            '  nn_itend = 17280\n',
            '  nn_date0 = 20141214\n',
        ]
        new_lines, prev_itend = run_NEMO_module.calc_new_namelist_lines(
            lines, today)
        assert prev_itend == 8640


@pytest.mark.use_fixtures(['run_NEMO_module'])
class TestGetNamelistValue(object):
    """Unit tests for get_namelist_value() function.
    """
    def test_get_value(self, run_NEMO_module):
        lines = ['  nn_it000 = 8641  ! first time step\n']
        line_index, value = run_NEMO_module.get_namelist_value(
            'nn_it000', lines)
        assert line_index == 0
        assert value == str(8641)

    def test_get_last_occurrence(self, run_NEMO_module):
        lines = [
            '  nn_it000 = 8641  ! first time step\n',
            '  nn_it000 = 8642  ! last time step\n',
        ]
        line_index, value = run_NEMO_module.get_namelist_value(
            'nn_it000', lines)
        assert line_index == 1
        assert value == str(8642)


def test_run_description_init_conditions(run_NEMO_module):
    today = date(2014, 10, 28)
    host = {
        'mpi decomposition': '7x16',
        'results': {'nowcast': '~/MEOPAR/SalishSea/nowcast/'},
        'run_prep_dirs': {'nowcast': '~/MEOPAR/nowcast/'},
    }
    run_desc = run_NEMO_module.run_description(
        host, 'nowcast', today, 'run_id', 42)
    expected = os.path.join(
        'SalishSea/nowcast/',
        (today - timedelta(days=1)).strftime('%d%b%y').lower(),
        'SalishSea_00000042_restart.nc',
    )
    assert run_desc['forcing']['initial conditions'].endswith(expected)
