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
        msg = socket.recv()
        message = lib.deserialize_message(msg)
        logger.info(
            'received message from {source}: {msg_type}'.format(**message))
        reply, next_step = parse_message(message)
        socket.send(reply)
        next_step()


def init_req_rep(port, context):
    socket = context.socket(zmq.REP)
    socket.bind('tcp://*:{}'.format(port))
    logger.info('bound to port {}'.format(port))
    return socket


def parse_message(message):
    if message['msg_type'] == 'end of nowcast':
        logger.info('nowcast completed for today')
        next_step = rotate_log_file
        reply = lib.serialize_message(mgr_name, 'acknowledged')
    return reply, next_step


def rotate_log_file():
    try:
        for handler in logger.handlers:
            logger.info('rotating log file')
            handler.doRollover()
            logger.info('log file rotated')
            logger.info('running in process {}'.format(os.getpid()))
    except AttributeError:
        # Logging handler has no rollover; probably a StreamHandler
        pass


if __name__ == '__main__':
    main()
