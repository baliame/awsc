import os
import sys

from awsc.version import VERSION

sys.path.insert(0, os.path.abspath("./awsc"))


project = "AWS Commander"
author = "Baliame"
copyright = "2022, Ákos Tóth"
version = VERSION
release = VERSION

extensions = ["sphinx.ext.autodoc", "numpydoc"]
autosummary_generate = True
templates_path = ["_templates"]
numpydoc_class_members_toctree = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
