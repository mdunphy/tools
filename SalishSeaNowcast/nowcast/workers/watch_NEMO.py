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

"""Salish Sea NEMO nowcast worker that monitors and reports on the
progress of a run on the ONC cloud computing facility or salish.
"""
import logging
import os
from pathlib import Path
import time

from salishsea_tools.namelist import namelist2dict

from nowcast import lib
from nowcast.nowcast_worker import (
    NowcastWorker,
    WorkerError,
)


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


POLL_INTERVAL = 5 * 60  # seconds


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'host_name',
        help='Name of the host to monitor the run on')
    worker.arg_parser.add_argument(
        'run_type',
        choices={'nowcast', 'nowcast-green', 'forecast', 'forecast2'},
        help='''
        Type of run to monitor:
        'nowcast' means nowcast physics run,
        'nowcast-green' means nowcast green ocean run,
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        ''',
    )
    worker.arg_parser.add_argument(
        'pid', type=int,
        help='PID of the NEMO run bash script to monitor.'
    )
    worker.arg_parser.add_argument(
        '--shared-storage', action='store_true',
        help='''
        Indicates that the NEMO run is on a machine (e.g. salish) that
        shares storage with the machine on which the nowcast manager is
        running. That affects how log messages are handled.
        ''',
    )
    worker.run(watch_NEMO, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} NEMO run on {0.host_name} completed'.format(parsed_args),
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} NEMO run on {0.host_name} failed'.format(parsed_args),
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def watch_NEMO(parsed_args, config, tell_manager):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    pid = parsed_args.pid
    shared_storage = parsed_args.shared_storage
    # Ensure that the run is in progress
    if not _pid_exists(pid):
        _log_msg(
            '{}: NEMO run pid {} on {} does not exist'
            .format(run_type, pid, host_name),
            'error', tell_manager, shared_storage)
        raise WorkerError
    # Get monitored run info from manager and namelist
    run_info = tell_manager('need', 'NEMO run')
    run_dir = Path(run_info[run_type]['run dir'])
    try:
        namelist = namelist2dict(str(run_dir/'namelist_cfg'))
        NEMO36 = True
    except FileNotFoundError:
        # NEMO-3.4
        namelist = namelist2dict(str(run_dir/'namelist'))
        NEMO36 = False
    it000 = namelist['namrun'][0]['nn_it000']
    itend = namelist['namrun'][0]['nn_itend']
    date0 = namelist['namrun'][0]['nn_date0']
    rdt = namelist['namdom'][0]['rn_rdt']
    # Watch for the run bash script process to end
    while _pid_exists(pid):
        try:
            with (run_dir/'time.step').open('rt') as f:
                time_step = int(f.read().strip())
            model_seconds = (
                (time_step - it000) * rdt if NEMO36
                else time_step * rdt)
            model_time = (
                date0.replace(seconds=model_seconds)
                .format('YYYY-MM-DD HH:mm:ss UTC'))
            fraction_done = (time_step - it000) / (itend - it000)
            msg = (
                '{} on {}: timestep: {} = {}, {:.1%} complete'
                .format(
                    run_type, host_name, time_step, model_time, fraction_done))
        except FileNotFoundError:
            # time.step file not found; assume that run is young and it
            # hasn't been created yet, or has finished and it has been
            # moved to the results directory
            msg = (
                '{} on {}: time.step not found; continuing to watch...'
                .format(run_type, host_name))
        _log_msg(msg, 'info', tell_manager, shared_storage)
        time.sleep(POLL_INTERVAL)
    ## TODO: confirm that the run and subsequent results gathering
    ## completed successfully
    return {run_type: {
        'host': host_name,
        'run date': run_info[run_type]['run date'],
        'completed': True,
    }}


def _log_msg(msg, level, tell_manager, shared_storage):
    logger.log(getattr(logging, level.upper()), msg)
    if not shared_storage:
        tell_manager('log.{}'.format(level), msg)


def _pid_exists(pid):
    """Check whether pid exists in the current process table.

    From: http://stackoverflow.com/a/6940314
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # PermissionError clearly means there's a process to deny access to
        return True
    except OSError:
        raise
    return True


if __name__ == '__main__':
    main()  # pragma: no cover
