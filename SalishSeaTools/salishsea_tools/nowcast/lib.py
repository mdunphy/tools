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

"""Salish Sea NEMO nowcast library functions for use by manager and workers.
"""
import argparse
import logging
import logging.handlers
import os
import signal
import subprocess
import sys
import time

import requests
import yaml
import zmq


class WorkerError(Exception):
    """Raised when a worker encounters an error or exception that it can'try:
    recover from.
    """


def get_module_name():
    """Return the name of the module with the path and the extension stripped.

    Example::

      get_module_name('foo/bar/baz.py')

    returns 'baz'.

    Typically used to create a module-level :data:`worker_name` variable::

      worker_name = lib.get_module_name()

    :returns: The name portion of the module filename.
    """
    return os.path.splitext(os.path.basename(sys.argv[0]))[0]


def basic_arg_parser(worker_name, description=None, add_help=True):
    """Return a command-line argument parser w/ handling for always-used args.

    The returned parser provides help messages, and handles the
    :option:`config_file` argument, and the :option:`--debug` option.
    It can be used as the parser for a worker,
    or as a parent parser if the worker has additional arguments
    and/or options.

    :arg worker_name: Name of the worker that the parser is for;
                      used to buid the usage message.
    :type worker_name: str

    :arg description: Brief description of what the worker does that
                      will be displayed in help messages.
    :type description: str

    :arg add_help: Add a `-h/--help` option to the parser.
                   Disable this if you are going to use the returned
                   parser as a parent parser to facilitate adding more
                   args/options.
    :type add_help: boolean

    :returns: :class:`argparse.ArgumentParser` instance
    """
    parser = argparse.ArgumentParser(
        description=description, add_help=add_help)
    parser.prog = (
        'python -m salishsea_tools.nowcast.workers.{}'.format(worker_name))
    parser.add_argument(
        'config_file',
        help='''
        Path/name of YAML configuration file for Salish Sea NEMO nowcast.
        '''
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='''
        Send logging output to the console instead of the log file;
        intended only for use when the worker is run in foreground
        from the command-line.
        ''',
    )
    return parser


def load_config(config_file):
    """Load the YAML config_file and return its contents as a dict.

    :arg config_file: Path/name of YAML configuration file for
                      Salish Sea NEMO nowcast.
    :type config_file: str

    :returns: config dict
    """
    with open(config_file, 'rt') as f:
        config = yaml.load(f)
    return config


def configure_logging(config, logger, debug):
    """Set up logging configuration.

    This function assumes that the logger instance has been created
    in the module from which the function is called.
    That is typically done with a module-level commands like::

      worker_name = lib.get_module_name()

      logger = logging.getLogger(worker_name)

    :arg config: Configuration data structure.
    :type config: dict

    :arg logger: Logger to be configured.
    :type logger: :obj:`logging.Logger` instance

    :arg debug: Debug mode; log to console instead of to file.
    :type debug: boolean
    """
    logger.setLevel(logging.DEBUG)
    handler = (
        logging.StreamHandler() if debug
        else logging.handlers.RotatingFileHandler(
            config['logging']['log_file'],
            backupCount=config['logging']['backup_count']))
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        config['logging']['message_format'],
        datefmt=config['logging']['datetime_format'])
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def install_signal_handlers(logger, context):
    """Install handlers to cleanly deal with interrupt and terminate signals.

    This function assumes that the logger and context instances
    have been created in the module from which the function is called.
    That is typically done with a module-level commands like::

      worker_name = lib.get_module_name()

      logger = logging.getLogger(worker_name)

      context = zmq.Context()

    :arg logger: Logger instance.
    :type logger: :class:`logging.Logger` instance

    :arg context: ZeroMQ context instance.
    :type context: :class:`zmq.Context` instance
    """
    def sigint_handler(signal, frame):
        logger.info(
            'interrupt signal (SIGINT or Ctrl-C) received; shutting down')
        context.destroy()
        sys.exit(0)

    def sigterm_handler(signal, frame):
        logger.info(
            'termination signal (SIGTERM) received; shutting down')
        context.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)


def init_zmq_req_rep_worker(context, config, logger):
    """Initialize a ZeroMQ request/reply (REQ/REP) worker.

    :arg context: ZeroMQ context instance.
    :type context: :class:`zmq.Context` instance

    :arg config: Configuration data structure.
    :type config: dict

    :arg logger: Logger instance.
    :type logger: :class:`logging.Logger` instance

    :returns: ZeroMQ socket for communication with nowcast manager process.
    """
    socket = context.socket(zmq.REQ)
    port = config['ports']['req_rep']
    socket.connect('tcp://localhost:{}'.format(port))
    logger.info('connected to port {}'.format(port))
    return socket


def serialize_message(source, msg_type, payload=None):
    """Transform message dict into byte-stream suitable for sending.

    :arg source: Name of the worker or manager sending the message;
                 typically :data:`worker_name`.
    :arg source: str

    :arg msg_type: Key of a message type that is defined for source
                   in the configuration data structure.
    :type msg_type: str

    :arg payload: Content of message;
                  must be serializable by YAML such that it can be
                  deserialized by :func:`yaml.safe_load`.
    :type payload: Python object

    :returns: Message dict serialized using YAML.
    """
    message = {
        'source': source,
        'msg_type': msg_type,
        'payload': payload,
    }
    return yaml.dump(message)


def deserialize_message(message):
    """Transform received message from byte-stream to dict.

    :arg message: Message dict serialized using YAML.
    :type message: bytes
    """
    return yaml.safe_load(message)


def get_web_data(
    url,
    logger,
    filepath=None,
    first_retry_delay=2,        # seconds
    retry_backoff_factor=2,
    retry_time_limit=60 * 60,   # seconds
):
    """Download content from url, optionally storing it in filepath.

    If the first download attempt fails, retry at intervals until the
    retry_time_limit is exceeded. The first retry occurs after
    first_retry_delay seconds. The delay until the next retry is
    calculated by multiplying the previous delay by retry_backoff_factor.

    So, with the default arugment values, the first retry will occur
    2 seconds after the download fails, and subsequent retries will
    occur at 4, 8, 16, 32, 64, ..., 2048 seconds after each failure.

    :arg url: URL to download content from.
    :type url: str

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg filepath: File path/name in which to store the downloaded content;
                   defaults to :py:obj:`None`, in which case the content
                   is returned.
    :type filepath: str

    :arg first_retry_delay: Number of seconds to wait before doing the
                            first retry after the initial download
                            attempt fails.
    :type first_retry_delay: int or float

    :arg retry_backoff_factor: Multiplicative factor that increases the
                               time interval between retries.
    :type retry_backoff_factor: int or float

    :arg retry_time_limit: Maximum number of seconds for the final retry
                           wait interval.
                           The actual wait time is less than or equal to
                           the limit so it may be significantly less than
                           the limit;
                           e.g. with the default argument values the final
                           retry wait interval will be 2048 seconds.
    :type retry_time_limit: int or float

    :returns: Downloaded content text if filepath is :py:obj:`None`,
              otherwise :py:obj:`requests.Response.headers` dict.

    :raises: :py:class:`salishsea_tools.nowcast.lib.WorkerError`
    """
    response = requests.get(url, stream=filepath is not None)
    try:
        response.raise_for_status()
        return _handle_url_content(response, filepath)
    except requests.exceptions.HTTPError as e:
        logger.warning('received {0.message} from {0.request.url}'.format(e))
        delay = first_retry_delay
        retries = 0
        while delay <= retry_time_limit:
            logger.debug('waiting {} seconds until retry'.format(delay))
            time.sleep(delay)
            response = requests.get(url, stream=filepath is not None)
            try:
                response.raise_for_status()
                return _handle_url_content(response, filepath)
            except requests.exceptions.HTTPError as e:
                logger.warning(
                    'received {0.message} from {0.request.url}'.format(e))
                delay *= retry_backoff_factor
                retries += 1
        logger.error(
            'giving up; download from {} failed {} times'
            .format(url, retries + 1))
        raise WorkerError


def _handle_url_content(response, filepath=None):
    """Return HTTP response content as text or store it as bytes in filepath.

    :arg response: HTTP response object.
    :type response: :py:class:`requests.Response`

    :arg filepath: File path/name in which to store the downloaded content;
                   defaults to :py:obj:`None`, in which case the content
                   is returned.
    :type filepath: str

    :returns: Downloaded content text if filepath is :py:obj:`None`,
              otherwise :py:obj:`requests.Response.headers` dict.
    """
    if filepath is None:
        # Return the content as text
        return response.text
    # Store the streamed content in filepath and return the headers
    with open(filepath, 'wb') as f:
        for block in response.iter_content(1024):
            if not block:
                break
            f.write(block)
    return response.headers


def run_in_subprocess(cmd, output_logger, error_logger):
    """Run the wgrib2 command (cmd) in a subprocess and log its stdout
    and stderr to the wgrib2 logger. Catch errors from the subprocess,
    log them to the primary logger, and raise the exception for handling
    somewhere higher in the call stack.

    :arg cmd: Command and its arguments/options to run in subprocess.
    :type cmd: list

    :arg output_logger: Logger object to send command output to when
                        command is successful.
    :type output_logger: :class:`logging.Logger`

    :arg error_logger: Logger object to send error message(s) to when
                        command returns non-zero status cdoe.
    :type error_logger: :class:`logging.Logger`

    :raises: :py:class:`salishsea_tools.nowcast.lib.WorkerError`
    """
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        for line in output.split('\n'):
            if line:
                output_logger(line)
    except subprocess.CalledProcessError as e:
        error_logger(
            'subprocess {cmd} failed with return code {status}'
            .format(cmd=cmd, status=e.returncode))
        for line in e.output.split('\n'):
            if line:
                error_logger(line)
        raise WorkerError
