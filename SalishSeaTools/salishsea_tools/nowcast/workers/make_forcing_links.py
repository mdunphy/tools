# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Salish Sea NEMO nowcast worker that creates the forcing file symlinks
for a nowcast run on the HPC/cloud facility where the run will be
executed.
"""
import argparse
import logging
import os
import traceback

import arrow
import zmq

from salishsea_tools.nowcast import lib
from salishsea_tools.nowcast.workers import (
    get_NeahBay_ssh,
    grib_to_netcdf,
    make_runoff_file,
)


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


def main():
    # Prepare the worker
    base_parser = lib.basic_arg_parser(
        worker_name, description=__doc__, add_help=False)
    parser = configure_argparser(
        prog=base_parser.prog,
        description=base_parser.description,
        parents=[base_parser],
    )
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.info('running in process {}'.format(os.getpid()))
    logger.info('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = make_forcing_links(
            parsed_args.host_name, parsed_args.run_type, parsed_args.run_date,
            config)
        logger.info(
            '{0.run_type} forcing file links on {0.host_name} created'
            .format(parsed_args))
        # Exchange success messages with the nowcast manager process
        msg_type = 'success {.run_type}'.format(parsed_args)
        lib.tell_manager(
            worker_name, msg_type, config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            '{0.run_type} forcing file links creation on {0.host_name} failed'
            .format(parsed_args))
        # Exchange failure messages with the nowcast manager process
        msg_type = 'failure {.run_type}'.format(parsed_args)
        lib.tell_manager(worker_name, msg_type, config, logger, socket)
    except SystemExit:
        # Normal termination
        pass
    except:
        logger.critical('unhandled exception:')
        for line in traceback.format_exc().splitlines():
            logger.error(line)
        # Exchange crash messages with the nowcast manager process
        lib.tell_manager(worker_name, 'crash', config, logger, socket)
    # Finish up
    context.destroy()
    logger.info('task completed; shutting down')


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        'host_name', help='Name of the host to upload forcing files to')
    parser.add_argument(
        'run_type', choices=set(('nowcast+', 'forecast2', 'ssh')),
        help='''
        Type of run to make links for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        ''',
    )
    parser.add_argument(
        '--run-date', type=lib.arrow_date, default=arrow.now(),
        help='''
        Date of the run to download results files from;
        use YYYY-MM-DD format.
        Defaults to %(default)s.
        ''',
    )
    return parser


def make_forcing_links(host_name, run_type, run_date, config):
    host = config['run'][host_name]
    ssh_client, sftp_client = lib.sftp(
        host_name, host['ssh key name']['nowcast'])  # nowcast: the project
    # Neah Bay sea surface height
    clear_links(sftp_client, host, 'open_boundaries/west/ssh/')
    for day in range(-1, 3):
        filename = get_NeahBay_ssh.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        dir = 'obs' if day == -1 else 'fcst'
        src = os.path.join(host['ssh_dir'], dir, filename)
        dest = os.path.join(
            host['nowcast_dir'], 'open_boundaries/west/ssh/', filename)
        create_symlink(sftp_client, host_name, src, dest)
    if run_type == 'ssh':
        sftp_client.close()
        ssh_client.close()
        return {host_name: True}
    # Rivers runoff
    clear_links(sftp_client, host, 'rivers/')
    src = host['rivers_month.nc']
    dest = os.path.join(host['nowcast_dir'], 'rivers/', os.path.basename(src))
    create_symlink(sftp_client, host_name, src, dest)
    src = os.path.join(
        host['rivers_dir'],
        make_runoff_file.FILENAME_TMPL.format(run_date.replace(days=-1).date())
    )
    for day in range(-1, 3):
        filename = make_runoff_file.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        dest = os.path.join(host['nowcast_dir'], 'rivers/', filename)
        create_symlink(sftp_client, host_name, src, dest)
    # Weather
    clear_links(sftp_client, host, 'NEMO-atmos/')
    NEMO_atmos_dir = os.path.join(host['nowcast_dir'], 'NEMO-atmos/')
    for linkfile in 'no_snow.nc weights'.split():
        src = host[linkfile]
        dest = os.path.join(NEMO_atmos_dir, os.path.basename(src))
        create_symlink(sftp_client, host_name, src, dest)
    if run_type == 'nowcast+':
        weather_start = -1
    else:
        weather_start = 0
    for day in range(weather_start, 3):
        filename = grib_to_netcdf.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        if run_type == 'nowcast+':
            dir = '' if day <= 0 else 'fcst'
        else:
            dir = 'fcst'
        src = os.path.join(host['weather_dir'], dir, filename)
        dest = os.path.join(NEMO_atmos_dir, filename)
        create_symlink(sftp_client, host_name, src, dest)
    sftp_client.close()
    ssh_client.close()
    return {host_name: True}


def clear_links(sftp_client, host, dir):
    links_dir = os.path.join(host['nowcast_dir'], dir)
    for linkname in sftp_client.listdir(links_dir):
        sftp_client.unlink(os.path.join(links_dir, linkname))
    logger.debug('{} symlinks cleared'.format(links_dir))


def create_symlink(sftp_client, host_name, src, dest):
    sftp_client.symlink(src, dest)
    logger.debug(
        '{src} symlinked as {dest} on {host}'
        .format(src=src, dest=dest, host=host_name))


if __name__ == '__main__':
    main()
