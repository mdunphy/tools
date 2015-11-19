# Copyright 2013-2015 The Salish Sea MEOPAR Contributors
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

"""SalishSeaCmd combine sub-command plug-in unit tests
"""
from unittest.mock import (
    Mock,
    patch,
)

import cliff.app
import cliff.command
import pytest


@pytest.fixture
def api_module():
    from salishsea_cmd import api
    return api


@pytest.mark.usefixture('api_module')
class TestCombine(object):
    @patch('salishsea_cmd.api._run_subcommand')
    def test_combine_default_args(self, m_run_subcommand, api_module):
        app, app_args = Mock(spec=cliff.app.App), []
        api_module.combine(app, app_args, 'run_desc_file', 'results_dir')
        m_run_subcommand.assert_called_once_with(
            app, app_args, ['combine', 'run_desc_file', 'results_dir'])

    @patch('salishsea_cmd.api._run_subcommand')
    def test_combine_keep_proc_results_arg(self, m_run_subcommand, api_module):
        app, app_args = Mock(spec=cliff.app.App), []
        api_module.combine(
            app, app_args, 'run_desc_file', 'results_dir',
            keep_proc_results=True)
        m_run_subcommand.assert_called_once_with(
            app, app_args,
            ['combine', 'run_desc_file', 'results_dir', '--keep-proc-results'])

    @patch('salishsea_cmd.api._run_subcommand')
    def test_combine_no_compress_arg(self, m_run_subcommand, api_module):
        app, app_args = Mock(spec=cliff.app.App), []
        api_module.combine(
            app, app_args, 'run_desc_file', 'results_dir',
            no_compress=True)
        m_run_subcommand.assert_called_once_with(
            app, app_args,
            ['combine', 'run_desc_file', 'results_dir', '--no-compress'])

    @patch('salishsea_cmd.api._run_subcommand')
    def test_combine_compress_restart_arg(self, m_run_subcommand, api_module):
        app, app_args = Mock(spec=cliff.app.App), []
        api_module.combine(
            app, app_args, 'run_desc_file', 'results_dir',
            compress_restart=True)
        m_run_subcommand.assert_called_once_with(
            app, app_args,
            ['combine', 'run_desc_file', 'results_dir', '--compress-restart'])

    @patch('salishsea_cmd.api._run_subcommand')
    def test_combine_delete_restart_arg(self, m_run_subcommand, api_module):
        app, app_args = Mock(spec=cliff.app.App), []
        api_module.combine(
            app, app_args, 'run_desc_file', 'results_dir',
            delete_restart=True)
        m_run_subcommand.assert_called_once_with(
            app, app_args,
            ['combine', 'run_desc_file', 'results_dir', '--delete-restart'])

    @patch('salishsea_cmd.api._run_subcommand')
    def test_combine_all_args(self, m_run_subcommand, api_module):
        app, app_args = Mock(spec=cliff.app.App), []
        api_module.combine(
            app, app_args, 'run_desc_file', 'results_dir',
            keep_proc_results=True, no_compress=True, compress_restart=True,
            delete_restart=True)
        m_run_subcommand.assert_called_once_with(
            app, app_args,
            ['combine', 'run_desc_file', 'results_dir', '--keep-proc-results',
             '--no-compress', '--compress-restart', '--delete-restart'])


@pytest.mark.usefixture('api_module')
class TestRunDescription(object):
    def test_no_arguments(self, api_module):
        run_desc = api_module.run_description()
        expected = {
            'config_name': 'SalishSea',
            'run_id': None,
            'walltime': None,
            'paths': {
                'NEMO-code': None,
                'forcing': None,
                'runs directory': None,
            },
            'grid': {
                'coordinates': 'coordinates_seagrid_SalishSea.nc',
                'bathymetry': 'bathy_meter_SalishSea2.nc',
            },
            'forcing': {
                'atmospheric': '/home/dlatorne/MEOPAR/CGRF/NEMO-atmos/',
                'initial conditions': None,
                'open boundaries': 'open_boundaries/',
                'rivers': 'rivers/',
            },
            'namelists': [
                'namelist.time',
                'namelist.domain',
                'namelist.surface',
                'namelist.lateral',
                'namelist.bottom',
                'namelist.tracers',
                'namelist.dynamics',
                'namelist.compute.12x27',
            ],
        }
        assert run_desc == expected

    def test_all_arguments(self, api_module):
        run_desc = api_module.run_description(
            run_id='foo',
            walltime='1:00:00',
            NEMO_code='../../NEMO-code/',
            forcing='../../NEMO-forcing/',
            runs_dir='../../SalishSea/',
            init_conditions='../../22-25Sep/SalishSea_00019008_restart.nc',
        )
        expected = {
            'config_name': 'SalishSea',
            'run_id': 'foo',
            'walltime': '1:00:00',
            'paths': {
                'NEMO-code': '../../NEMO-code/',
                'forcing': '../../NEMO-forcing/',
                'runs directory': '../../SalishSea/',
            },
            'grid': {
                'coordinates': 'coordinates_seagrid_SalishSea.nc',
                'bathymetry': 'bathy_meter_SalishSea2.nc',
            },
            'forcing': {
                'atmospheric': '/home/dlatorne/MEOPAR/CGRF/NEMO-atmos/',
                'initial conditions': '../../22-25Sep/SalishSea_00019008_restart.nc',
                'open boundaries': 'open_boundaries/',
                'rivers': 'rivers/',
            },
            'namelists': [
                'namelist.time',
                'namelist.domain',
                'namelist.surface',
                'namelist.lateral',
                'namelist.bottom',
                'namelist.tracers',
                'namelist.dynamics',
                'namelist.compute.12x27',
            ],
        }
        assert run_desc == expected


@pytest.mark.usefixture('api_module')
class TestRunSubcommand(object):
    def test_command_not_found_raised(self, api_module):
        app = Mock(spec=cliff.app.App)
        app_args = Mock(debug=True)
        with pytest.raises(ValueError):
            return_code = api_module._run_subcommand(app, app_args, [])
            assert return_code == 2

    @patch('salishsea_cmd.api.log.error')
    def test_command_not_found_logged(self, m_log, api_module):
        app = Mock(spec=cliff.app.App)
        app_args = Mock(debug=False)
        return_code = api_module._run_subcommand(app, app_args, [])
        assert m_log.called
        assert return_code == 2

    @patch('salishsea_cmd.api.cliff.commandmanager.CommandManager')
    @patch('salishsea_cmd.api.log.exception')
    def test_command_exception_logged(self, m_log, m_cmd_mgr, api_module):
        app = Mock(spec=cliff.app.App)
        app_args = Mock(debug=True)
        cmd_factory = Mock(spec=cliff.command.Command)
        cmd_factory().take_action.side_effect = Exception
        m_cmd_mgr().find_command.return_value = (cmd_factory, 'bar', 'baz')
        api_module._run_subcommand(app, app_args, ['foo'])
        assert m_log.called

    @patch('salishsea_cmd.api.cliff.commandmanager.CommandManager')
    @patch('salishsea_cmd.api.log.error')
    def test_command_exception_logged_as_error(
        self,
        m_log,
        m_cmd_mgr,
        api_module,
    ):
        app = Mock(spec=cliff.app.App)
        app_args = Mock(debug=False)
        cmd_factory = Mock(spec=cliff.command.Command)
        cmd_factory().take_action.side_effect = Exception
        m_cmd_mgr().find_command.return_value = (cmd_factory, 'bar', 'baz')
        api_module._run_subcommand(app, app_args, ['foo'])
        assert m_log.called
