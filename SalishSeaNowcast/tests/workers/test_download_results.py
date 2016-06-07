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

"""Unit tests for Salish Sea NEMO nowcast download_results worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import arrow
import pytest

import nowcast.lib
from nowcast.workers import download_results


@patch('nowcast.workers.download_results.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch('nowcast.workers.download_results.worker_name')
    def test_instantiate_worker(self, m_name, m_worker):
        download_results.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker):
        download_results.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        download_results.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('run_type',)
        expected = {'nowcast', 'nowcast-green', 'forecast', 'forecast2'}
        assert kwargs['choices'] == expected
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker):
        download_results.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[2]
        assert args == ('--run-date',)
        assert kwargs['type'] == nowcast.lib.arrow_date
        assert kwargs['default'] == arrow.now('Canada/Pacific').floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        download_results.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            download_results.download_results,
            download_results.success,
            download_results.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('run_type, host_name', [
        ('nowcast', 'west.cloud-nowcast'),
        ('nowcast-green', 'salish-nowcast'),
        ('forecast', 'west.cloud-nowcast'),
        ('forecast2', 'west.cloud-nowcast'),
    ])
    def test_success_log_info(self, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        with patch('nowcast.workers.download_results.logger') as m_logger:
            download_results.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]['extra']['run_type'] == run_type
        assert m_logger.info.call_args[1]['extra']['host_name'] == host_name

    @pytest.mark.parametrize('run_type, host_name', [
        ('nowcast', 'west.cloud-nowcast'),
        ('nowcast-green', 'salish-nowcast'),
        ('forecast', 'west.cloud-nowcast'),
        ('forecast2', 'west.cloud-nowcast'),
    ])
    def test_success_msg_type(self, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        with patch('nowcast.workers.download_results.logger'):
            msg_typ = download_results.success(parsed_args)
        assert msg_typ == 'success {}'.format(run_type)


class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('run_type, host_name', [
        ('nowcast', 'west.cloud-nowcast'),
        ('nowcast-green', 'salish-nowcast'),
        ('forecast', 'west.cloud-nowcast'),
        ('forecast2', 'west.cloud-nowcast'),
    ])
    def test_failure_log_critical(self, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        with patch('nowcast.workers.download_results.logger') as m_logger:
            download_results.failure(parsed_args)
        assert m_logger.critical.called
        assert m_logger.critical.call_args[1]['extra']['run_type'] == run_type
        assert m_logger.critical.call_args[1]['extra']['host_name'] == host_name

    @pytest.mark.parametrize('run_type, host_name', [
        ('nowcast', 'west.cloud-nowcast'),
        ('nowcast-green', 'salish-nowcast'),
        ('forecast', 'west.cloud-nowcast'),
        ('forecast2', 'west.cloud-nowcast'),
    ])
    def test_failure_msg_type(self, run_type, host_name):
        parsed_args = Mock(run_type=run_type, host_name=host_name)
        with patch('nowcast.workers.download_results.logger'):
            msg_typ = download_results.failure(parsed_args)
        assert msg_typ == 'failure {}'.format(run_type)
