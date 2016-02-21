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

"""Salish Sea NEMO nowcast worker that creates pages for the salishsea
site from page templates.
"""
from copy import copy
from glob import glob
import logging
import os
import shutil

import arrow
import mako.template

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)

# Number of days in index page grid
INDEX_GRID_COLS = 21


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'run_type',
        choices={'nowcast', 'nowcast-green', 'forecast', 'forecast2'},
        help='''
        Type of run to execute:
        'nowcast' means nowcast physics run,
        'nowcast-green' means nowcast green ocean run,
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        ''',
    )
    worker.arg_parser.add_argument(
        'page_type',
        choices=set(('index', 'publish', 'research',)),
        help='''
        Type of page to render from template to salishsea site prep directory.
        '''
    )
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date to execute the run for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.run(make_site_page, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} {0.page_type} {run_date} '
        'pages for salishsea site prepared'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'page_type': parsed_args.page_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.page_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} {0.page_type} {run_date} ''page preparation failed'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'page_type': parsed_args.page_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.page_type}'.format(parsed_args)
    return msg_type


def make_site_page(parsed_args, config, *args):
    run_type = parsed_args.run_type
    page_type = parsed_args.page_type
    run_date = parsed_args.run_date
    svg_file_roots = {
        'publish': [
            ('Threshold_website',
                'Marine and Atmospheric Conditions - Storm Surge Alerts'),
            ('PA_tidal_predictions', 'Tidal Predictions for Point Atkinson'),
            ('Vic_maxSSH', 'Victoria Sea Surface Height'),
            ('CP_maxSSH', 'Cherry Point Sea Surface Height'),
            ('PA_maxSSH', 'Point Atkinson Sea Surface Height'),
            ('Nan_maxSSH', 'Nanaimo Sea Surface Height'),
            ('CR_maxSSH', 'Campbell River Sea Surface Height'),
            ('NOAA_ssh', 'Sea Surface Height at Selected NOAA Stations'),
            ('WaterLevel_Thresholds', 'Storm Surge Alert Thresholds'),
            ('SH_wind', 'Sandheads Wind'),
            ('Avg_wind_vectors',
                'Winds from Atmospheric Forcing Averaged Over Run Duration'),
            ('Wind_vectors_at_max',
                'Instantaneous Winds from Atmospheric Forcing'),
        ],
        'research': [
            ('Salinity_on_thalweg', 'Salinity Field Along Thalweg'),
            ('Temperature_on_thalweg', 'Temperature Field Along Thalweg'),
            ('T_S_Currents_on_surface',
                'Surface Salinity, Temperature and Currents'),
            ('Currents_at_VENUS_East',
                'Model Currents at ONC VENUS East Node'),
            ('Currents_at_VENUS_Central',
                'Model Currents at ONC VENUS Central Node'),
            ('Compare_VENUS_East',
                'Salinity and Temperature at ONC VENUS East Node'),
            ('Compare_VENUS_Central',
                'Salinity and Temperature at ONC VENUS Central Node'),
        ],
    }
    # Functions to render rst files for various run types
    render_rst = {
        'nowcast': _render_nowcast_rst,
        'forecast': _render_forecast_rst,
        'forecast2': _render_forecast2_rst,
    }
    # Load template
    mako_file = os.path.join(
        config['web']['templates_path'],
        '{page_type}.mako'.format(page_type=page_type))
    tmpl = mako.template.Template(filename=mako_file, input_encoding='utf-8')
    logger.debug(
        '{run_type} {page_type}: read template: {mako_file}'
        .format(run_type=run_type, page_type=page_type, mako_file=mako_file),
        extra={
            'run_type': run_type,
            'page_type': page_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    # Render template to rst
    repo_name = config['web']['site_repo_url'].rsplit('/')[-1]
    repo_path = os.path.join(config['web']['www_path'], repo_name)
    results_pages_path = os.path.join(
        repo_path,
        config['web']['site_nemo_results_path'])
    checklist = {}
    if page_type != 'index':
        checklist.update(render_rst[run_type](
            tmpl, page_type, run_date, svg_file_roots, results_pages_path,
            config))
    # Render index page template to rst
    checklist.update(
        _render_index_rst(
            page_type, run_type, run_date, results_pages_path, config))
    # If appropriate copy rst file to forecast file
    if run_type in ('forecast', 'forecast2') and page_type == 'publish':
        rst_file = checklist['{} publish'.format(run_type)]
        forecast_file = os.path.join(
            repo_path, config['web']['site_storm_surge_path'], 'forecast.rst')
        shutil.copy2(rst_file, forecast_file)
        logger.debug(
            '{run_type} {page_type}: copied page to forecast: {forecast_file}'
            .format(
                run_type=run_type,
                page_type=page_type,
                forecast_file=forecast_file),
            extra={
                'run_type': run_type,
                'page_type': page_type,
                'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
            })
        checklist['most recent forecast'] = forecast_file
    return checklist


def _render_nowcast_rst(
    tmpl, page_type, run_date, svg_file_roots, rst_path, config,
):
    rst_filename = (
        '{page_type}_{dmy}.rst'
        .format(page_type=page_type,
                dmy=run_date.format('DDMMMYY').lower()))
    rst_file = os.path.join(rst_path, 'nowcast', rst_filename)
    figures_server = (
        'http://{domain}/{path}'
        .format(
            domain=config['web']['domain'],
            path=config['web']['figures']['server_path']))
    vars = {
        'run_date': run_date,
        'run_type': 'nowcast',
        'results_date': run_date,
        'run_title': 'Nowcast',
        'svg_file_roots': svg_file_roots[page_type],
        'figures_server': figures_server,
    }
    _tmpl_to_rst(tmpl, rst_file, vars, config)
    logger.debug(
        'nowcast {page_type}: rendered page: {rst_file}'
        .format(page_type=page_type, rst_file=rst_file), extra={
            'run_type': 'nowcast',
            'page_type': page_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    checklist = {'nowcast {}'.format(page_type): rst_file}
    return checklist


def _render_forecast_rst(
    tmpl, page_type, run_date, svg_file_roots, rst_path, config,
):
    results_date = run_date.replace(days=1)
    rst_filename = (
        '{page_type}_{dmy}.rst'
        .format(page_type=page_type,
                dmy=results_date.format('DDMMMYY').lower()))
    rst_file = os.path.join(rst_path, 'forecast', rst_filename)
    figures_server = (
        'http://{domain}/{path}'
        .format(
            domain=config['web']['domain'],
            path=config['web']['figures']['server_path']))
    vars = {
        'run_date': run_date,
        'run_type': 'forecast',
        'results_date': results_date,
        'run_title': 'Forecast',
        'svg_file_roots': svg_file_roots[page_type],
        'figures_server': figures_server,
    }
    _tmpl_to_rst(tmpl, rst_file, vars, config)
    logger.debug(
        'forecast {page_type}: rendered page: {rst_file}'
        .format(page_type=page_type, rst_file=rst_file), extra={
            'run_type': 'forecast',
            'page_type': page_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    checklist = {
        'forecast {}'.format(page_type): rst_file,
    }
    return checklist


def _render_forecast2_rst(
    tmpl, page_type, run_date, svg_file_roots, rst_path, config,
):
    results_date = run_date.replace(days=2)
    rst_filename = (
        '{page_type}_{dmy}.rst'
        .format(page_type=page_type,
                dmy=results_date.format('DDMMMYY').lower()))
    rst_file = os.path.join(rst_path, 'forecast2', rst_filename)
    figures_server = (
        'http://{domain}/{path}'
        .format(
            domain=config['web']['domain'],
            path=config['web']['figures']['server_path']))
    vars = {
        'run_date': run_date,
        'run_type': 'forecast2',
        'results_date': results_date,
        'run_title': 'Preliminary Forecast',
        'svg_file_roots': svg_file_roots[page_type],
        'figures_server': figures_server,
    }
    _tmpl_to_rst(tmpl, rst_file, vars, config)
    logger.debug(
        'forecast2 {page_type}: rendered page: {rst_file}'
        .format(page_type=page_type, rst_file=rst_file), extra={
            'run_type': 'forecast2',
            'page_type': page_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    checklist = {
        'forecast2 {}'.format(page_type): rst_file,
        'finish the day': True,
    }
    return checklist


def _render_index_rst(page_type, run_type, run_date, rst_path, config):
    mako_file = os.path.join(config['web']['templates_path'], 'index.mako')
    tmpl = mako.template.Template(filename=mako_file)
    logger.debug(
        '{run_type} {page_type}: read index page template: {mako_file}'
        .format(run_type=run_type, page_type=page_type, mako_file=mako_file),
        extra={
            'run_type': run_type,
            'page_type': page_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    # Calculate the date range to display in the grid and the number of
    # columns for the month headings of the grid
    fcst_date = (
        run_date.replace(days=+1) if run_type != 'forecast2'
        else run_date.replace(days=+2))
    dates = arrow.Arrow.range(
        'day', fcst_date.replace(days=-(INDEX_GRID_COLS - 1)), fcst_date)
    if dates[0].month != dates[-1].month:
        this_month_cols = dates[-1].day
        last_month_cols = INDEX_GRID_COLS - this_month_cols
    else:
        this_month_cols, last_month_cols = INDEX_GRID_COLS, 0
    # Replace dates for which there is no results page with None
    prelim_fcst_dates = _exclude_missing_dates(
        copy(dates), os.path.join(rst_path, 'forecast2', 'publish_*.rst'))
    nowcast_pub_dates = (
        copy(dates[:-1]) if run_type in 'nowcast forecast'.split()
        else copy(dates[:-2]))
    nowcast_pub_dates = _exclude_missing_dates(
        nowcast_pub_dates, os.path.join(rst_path, 'nowcast', 'publish_*.rst'))
    nowcast_res_dates = (
        copy(dates[:-1]) if run_type in 'nowcast forecast'.split()
        else copy(dates[:-2]))
    nowcast_res_dates = _exclude_missing_dates(
        nowcast_res_dates, os.path.join(rst_path, 'nowcast', 'research_*.rst'))
    fcst_dates = copy(dates[:-1]) if run_type != 'forecast' else copy(dates)
    fcst_dates = _exclude_missing_dates(
        fcst_dates,
        os.path.join(rst_path, 'forecast', '{}_*.rst'.format(page_type)))
    sal_comp_dates = (
        copy(dates[:-1]) if run_type in 'nowcast forecast'.split()
        else copy(dates[:-2]))
    sal_comp_fileroot = config['web']['salinity_comparison']['fileroot']
    sal_comp_dates = _exclude_missing_dates(
        sal_comp_dates,
        os.path.join(
            config['web']['salinity_comparison']['filesystem_path'],
            '{}_*.ipynb'.format(sal_comp_fileroot)))
    # Render the template using the calculated varible values to produce
    # the index rst file
    rst_file = os.path.join(rst_path, 'index.rst')
    vars = {
        'first_date': dates[0],
        'last_date': dates[-1],
        'this_month_cols': this_month_cols,
        'last_month_cols': last_month_cols,
        'prelim_fcst_dates': prelim_fcst_dates,
        'nowcast_pub_dates': nowcast_pub_dates,
        'nowcast_res_dates': nowcast_res_dates,
        'fcst_dates': fcst_dates,
        'sal_comp_dates': sal_comp_dates,
        'sal_comp_path': config['web']['salinity_comparison']['web_path'],
        'sal_comp_fileroot': sal_comp_fileroot,
    }
    _tmpl_to_rst(tmpl, rst_file, vars, config)
    logger.debug(
        '{run_type} {page_type}: rendered index page: {rst_file}'
        .format(run_type=run_type, page_type=page_type, rst_file=rst_file),
        extra={
            'run_type': run_type,
            'page_type': page_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    checklist = {
        '{run_type} {page_type} index page'
        .format(run_type=run_type, page_type=page_type): rst_file}
    return checklist


def _exclude_missing_dates(grid_dates, file_pattern):
    files = [os.path.basename(f) for f in glob(file_pattern)]
    file_date_strs = [
        os.path.splitext(f)[0].split('_')[1].title() for f in files]
    file_dates = [arrow.get(d, 'DDMMMYY').naive for d in file_date_strs]
    for i, d in enumerate(grid_dates):
        if d.naive not in file_dates:
            grid_dates[i] = None
    return grid_dates


def _tmpl_to_rst(tmpl, rst_file, vars, config):
    with open(rst_file, 'wt') as f:
        f.write(tmpl.render(**vars))
    lib.fix_perms(rst_file, grp_name=config['file group'])


if __name__ == '__main__':
    main()  # pragma: no cover
