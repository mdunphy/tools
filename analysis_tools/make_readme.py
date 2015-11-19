"""Salish Sea NEMO IPython Notebook collection README generator


Copyright 2013-2015 The Salish Sea MEOPAR Contributors
and The University of British Columbia

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import datetime
import json
import os
import re


nbviewer = 'http://nbviewer.ipython.org/urls'
repo = 'bitbucket.org/salishsea/tools/raw/tip'
repo_dir = 'analysis_tools'
url = os.path.join(nbviewer, repo, repo_dir)
title_pattern = re.compile('#{1,6} ?')
readme = """The IPython Notebooks in this directory provide discussion,
examples, and best practices for plotting various kinds of model results
from netCDF files. There are code examples in the notebooks and also
examples of the use of functions from the
[`salishsea_tools`](http://salishsea-meopar-tools.readthedocs.org/en/latest/SalishSeaTools/salishsea-tools.html)
package.
If you are new to the Salish Sea MEOPAR project or to IPython Notebook,
netCDF, and Matplotlib you should read the introductory notebooks
in the following order:

* [Exploring netCDF Files.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/analysis_tools/Exploring netCDF Files.ipynb)
* [Plotting Bathymetry Colour Meshes.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/analysis_tools/Plotting Bathymetry Colour Meshes.ipynb)
* [Plotting Tracers on Horizontal Planes.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/analysis_tools/Plotting Tracers on Horizontal Planes.ipynb)
* [Plotting Velocity Fields on Horizontal Planes.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/analysis_tools/Plotting Velocity Fields on Horizontal Planes.ipynb)
* [Plotting Velocities and Tracers on Vertical Planes.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/analysis_tools/Plotting Velocities and Tracers on Vertical Planes.ipynb)

The links above and below are to static renderings of the notebooks via
[nbviewer.ipython.org](http://nbviewer.ipython.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

"""
notebooks = (fn for fn in os.listdir('./') if fn.endswith('ipynb'))
for fn in notebooks:
    readme += '* ##[{fn}]({url}/{fn})  \n    \n'.format(fn=fn, url=url)
    with open(fn, 'rt') as notebook:
        contents = json.load(notebook)
    first_cell_type = contents['worksheets'][0]['cells'][0]['cell_type']
    if first_cell_type in 'markdown raw'.split():
        desc_lines = contents['worksheets'][0]['cells'][0]['source']
        for line in desc_lines:
            suffix = ''
            if title_pattern.match(line):
                line = title_pattern.sub('**', line)
                suffix = '**'
            if line.endswith('\n'):
                readme += (
                    '    {line}{suffix}  \n'
                    .format(line=line[:-1], suffix=suffix))
            else:
                readme += (
                    '    {line}{suffix}  '.format(line=line, suffix=suffix))
        readme += '\n' * 2
license = """
##License

These notebooks and files are copyright 2013-{this_year}
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
""".format(this_year=datetime.date.today().year)
with open('README.md', 'wt') as f:
    f.writelines(readme)
    f.writelines(license)
