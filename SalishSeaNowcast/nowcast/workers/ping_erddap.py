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

"""Salish Sea nowcast worker that creates flag files to tell the ERDDAP
server to reload datasets for which new results have been downloaded.
"""
import logging
from pathlib import Path

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'dataset',
        choices={
            'nowcast', 'nowcast-green', 'forecast', 'forecast2',
            'download_weather',
        },
        help='''
        Type of dataset to notify ERDDAP of:
        'nowcast' means nowcast physics run,
        'nowcast-green' means nowcast green ocean run,
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        'download_weather' means atmospheric forcing downloaded & processed
        ''',
    )
    worker.run(ping_erddap, success, failure)


def success(parsed_args):
    logger.info(
        '{.dataset} ERDDAP dataset flag files created'.format(parsed_args),
        extra={'dataset': parsed_args.dataset})
    msg_type = 'success {.dataset}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{.dataset} ERDDAP dataset flag files creation failed'
        .format(parsed_args),
        extra={'dataset': parsed_args.dataset})
    msg_type = 'failure {.dataset}'.format(parsed_args)
    return msg_type


def ping_erddap(parsed_args, config, *args):
    dataset = parsed_args.dataset
    flag_path = Path(config['erddap']['flag_dir'])
    checklist = {dataset: []}
    try:
        for dataset_id in config['erddap']['datasetIDs'][dataset]:
            (flag_path/dataset_id).touch()
            logger.debug('{} touched'.format(flag_path/dataset_id))
            checklist[dataset].append(dataset_id)
    except KeyError:
        # run type is not in datasetIDs dict
        pass
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover
