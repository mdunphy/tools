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

"""Unit tests for Salish Sea NEMO nowcast get_NeahBay_ssh worker.
"""
import datetime
from unittest.mock import (
    Mock,
    patch,
)

import pytz

from nowcast.workers import get_NeahBay_ssh


@patch('nowcast.workers.get_NeahBay_ssh.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch('nowcast.workers.get_NeahBay_ssh.worker_name')
    def test_instantiate_worker(self, m_name, m_worker):
        get_NeahBay_ssh.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_run_type_arg(self, m_worker):
        get_NeahBay_ssh.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'nowcast', 'forecast', 'forecast2'}
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        get_NeahBay_ssh.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            get_NeahBay_ssh.get_NeahBay_ssh,
            get_NeahBay_ssh.success,
            get_NeahBay_ssh.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self):
        parsed_args = Mock(run_type='nowcast')
        with patch('nowcast.workers.get_NeahBay_ssh.logger') as m_logger:
            get_NeahBay_ssh.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self):
        parsed_args = Mock(run_type='nowcast')
        with patch('nowcast.workers.get_NeahBay_ssh.logger') as m_logger:
            msg_typ = get_NeahBay_ssh.success(parsed_args)
        assert msg_typ == 'success nowcast'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_critical(self):
        parsed_args = Mock(run_type='nowcast')
        with patch('nowcast.workers.get_NeahBay_ssh.logger') as m_logger:
            get_NeahBay_ssh.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self):
        parsed_args = Mock(run_type='nowcast')
        with patch('nowcast.workers.get_NeahBay_ssh.logger') as m_logger:
            msg_typ = get_NeahBay_ssh.failure(parsed_args)
        assert msg_typ == 'failure nowcast'


class TestUTCNowToRunDate:
    """Unit tests for _utc_now_to_run_date() function.
    """
    def test_nowcast(self):
        utc_now = datetime.datetime(
            2014, 12, 25, 17, 52, 42, tzinfo=pytz.timezone('UTC'))
        run_day = get_NeahBay_ssh._utc_now_to_run_date(
            utc_now, 'nowcast')
        assert run_day == datetime.date(2014, 12, 25)

    def test_forecast(self):
        utc_now = datetime.datetime(
            2014, 12, 25, 19, 54, 42, tzinfo=pytz.timezone('UTC'))
        run_day = get_NeahBay_ssh._utc_now_to_run_date(
            utc_now, 'forecast')
        assert run_day == datetime.date(2014, 12, 25)

    def test_forecast2(self):
        utc_now = datetime.datetime(
            2014, 12, 26, 12, 53, 42, tzinfo=pytz.timezone('UTC'))
        run_day = get_NeahBay_ssh._utc_now_to_run_date(
            utc_now, 'forecast2')
        assert run_day == datetime.date(2014, 12, 25)
