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

"""Salish Sea NEMO nowcast manager.
"""
import logging
import os

import zmq

from salishsea_tools.nowcast import lib


mgr_name = lib.get_module_name()

logger = logging.getLogger(mgr_name)

context = zmq.Context()

checklist = {}


def main():
    parser = lib.basic_arg_parser(mgr_name, description=__doc__)
    parser.prog = 'python -m salishsea_tools.nowcast.{}'.format(mgr_name)
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.info('running in process {}'.format(os.getpid()))
    logger.info('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = init_req_rep(config['ports']['req_rep'], context)
    while True:
        logger.info('listening...')
        message = socket.recv()
        reply, next_step, next_step_args = parse_message(config, message)
        socket.send(reply)
        next_step(*next_step_args)


def init_req_rep(port, context):
    socket = context.socket(zmq.REP)
    socket.bind('tcp://*:{}'.format(port))
    logger.info('bound to port {}'.format(port))
    return socket


def parse_message(config, message):
    msg = lib.deserialize_message(message)
    # Unpack message items
    worker = msg['source']
    msg_type = msg['msg_type']
    payload = msg['payload']
    # Set default reply message, next processing step function,
    # and its arguments
    reply_ack = lib.serialize_message(mgr_name, 'ack')
    next_step = do_nothing
    next_step_args = []
    if msg_type not in config['msg_types'][worker]:
        logger.error(
            'undefined message type received from {worker}: {msg_type}'
            .format(worker=worker, msg_type=msg_type))
        reply = lib.serialize_message(mgr_name, 'undefined msg')
    else:
        logger.info(
            'received message from {worker}: ({msg_type}) {msg_words}'
            .format(worker=worker,
                    msg_type=msg_type,
                    msg_words=config['msg_types'][worker][msg_type]))
    if msg_type.startswith('success'):
        if worker == 'download_weather' and msg_type.endswith('06'):
            reply = reply_ack
        if worker == 'download_weather' and msg_type.endswith('18'):
            reply = reply_ack
            next_step = launch_worker
            next_step_args = ['grib_to_netcdf', config]
        if worker == 'get_NeahBay_ssh':
            reply = reply_ack
            next_step = update_checklist
            next_step_args = [worker, 'sshNeahBay', payload]
        if worker == 'make_runoff_file':
            reply = reply_ack
            next_step = update_checklist
            next_step_args = [worker, 'rivers', payload]
        if worker == 'grib_to_netcdf':
            reply = reply_ack
            next_step = update_checklist
            next_step_args = [worker, 'weather forcing', payload]
    if msg_type.startswith('failure'):
        if worker == 'download_weather' and msg_type.endswith('06'):
            reply = reply_ack
        if worker == 'download_weather' and msg_type.endswith('18'):
            reply = reply_ack
        if worker == 'get_NeahBay_ssh':
            reply = reply_ack
        if worker == 'make_runoff_file':
            reply = reply_ack
        if worker == 'grib_to_netcdf':
            reply = reply_ack
    if msg_type == 'the end':
        logger.info('worker-automated parts of nowcast completed for today')
        reply = reply_ack
        next_step = finish_automation
        next_step_args = [config]
    return reply, next_step, next_step_args


def do_nothing(*args):
    pass


def update_checklist(worker, key, worker_checklist):
    checklist.update({key: worker_checklist})
    logger.info(
        'checklist updated with {} items from {} worker'.format(key, worker))


def launch_worker(worker, config):
    cmd = [
        config['python'], '-m',
        'salishsea_tools.nowcast.workers.{}'.format(worker),
        config['config_file'],
    ]
    logger.info('launching {} worker'.format(worker))
    lib.run_in_subprocess(cmd, logger.debug, logger.error)


def finish_automation(config):
    checklist = {}
    logger.info('checklist cleared')
    rotate_log_file(config)


def rotate_log_file(config):
    try:
        for handler in logger.handlers:
            logger.info('rotating log file')
            handler.doRollover()
            # 436 == octal 664 == 'rw-rw-r--'
            os.chmod(config['logging']['log_file'], 436)
            logger.info('log file rotated')
            logger.info('running in process {}'.format(os.getpid()))
    except AttributeError:
        # Logging handler has no rollover; probably a StreamHandler
        pass


if __name__ == '__main__':
    main()
