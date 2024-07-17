# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pytest-failure-tracker"
copyright = "2024, Krystian Safjan"
author = "Krystian Safjan"
release = "0.2.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    'myst_parser',
    # 'sphinx_markdown_tables'  # Optional: if you need table support in Markdown
]

#
myst_enable_extensions = ["colon_fence"]

templates_path = ["_templates"]
exclude_patterns = []

# Sphinx-copybutton config
# These options configure the extension to:
#
# Recognize "$ " as a prompt
# Use regular expressions for prompt detection
# Only copy lines starting with the prompt
# Remove the prompt when copying
# copybutton_prompt_text = "$ "
# copybutton_prompt_is_regexp = True
# copybutton_only_copy_prompt_lines = True
# copybutton_remove_prompts = True

# -- Options for HTML output -------------------------------------------------
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {}
html_title = "pytest-failure-tracker"
html_static_path = ["_static"]

# # Set the source_suffix for Markdown
# source_suffix = {
#     ".rst": "restructuredtext",
#     ".md": "markdown",
# }

# Define the GitHub doc root
github_doc_root = "https://izikeros.github.io/pytest-failure-tracker/"
