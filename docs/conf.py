#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Salish Sea MEOPAR tools documentation build configuration file
#
# This file is execfile()d with the current directory set to
# its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import datetime
import os
import sys
from unittest import mock

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../SalishSeaNowcast'))
sys.path.insert(0, os.path.abspath('../SalishSeaCmd'))
sys.path.insert(0, os.path.abspath('../SalishSeaTools'))


# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings.
# They can be extensions coming with Sphinx
# (named 'sphinx.ext.*')
# or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

intersphinx_mapping = {
    'docs': ('http://salishsea-meopar-docs.readthedocs.org/en/latest/', None),
}

todo_include_todos = True

# Mock interface for importing packages with C-extensions that aren't installed
# in the docs build environment
# (especially that on readthedocs.org build servers)
MOCK_MODULES = [
    'angles',
    'driftwood.formatters',
    'matplotlib',
    'matplotlib.backends',
    'matplotlib.cm',
    'matplotlib.colors',
    'matplotlib.dates',
    'matplotlib.gridspec',
    'matplotlib.ticker',
    'matplotlib.patches',
    'matplotlib.pyplot',
    'netCDF4',
    'numpy',
    'pandas',
    'paramiko',
    'pytz',
    'requests',
    'scipy',
    'scipy.optimize',
    'zmq',
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = mock.Mock()
sys.modules['numpy'].pi = 3.1415927

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Salish Sea MEOPAR Tools'
copyright = (
    '2013-{:%Y}, '
    'Salish Sea MEOPAR Project Contributors '
    'and The University of British Columbia'
    .format(datetime.date.today())
)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = ''

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = '_static/MEOPAR_favicon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

# Output file base name for HTML help builder.
htmlhelp_basename = 'SalishSea-MEOPAR-toolsdoc'


# -- Options for LaTeX output -------------------------------------------------

# Grouping the document tree into LaTeX files.
# List of tuples
# (source start file, target name, title,
#  author, documentclass [howto/manual]).
latex_documents = [(
    'index',
    'SalishSea-MEOPAR-toolsdoc.tex',
    'Salish Sea MEOPAR Tools Documentation',
    'Salish Sea MEOPAR Project Contributors',
    'manual',
)]
