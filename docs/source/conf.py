# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
# import os
# import sys
# import django

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Tetra"
copyright = "2022, Sam Willis"
author = "Sam Willis"

# -- Django information -----------------------------------------------------

# sys.path.insert(0, os.path.abspath(".."))
# os.environ["DJANGO_SETTINGS_MODULE"] = "demosite.demosite.settings"
# django.setup()

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    # "sphinxcontrib_django2",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("http://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/stable",
        "https://docs.djangoproject.com/en/stable/_objects",
    ),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

# TODO: @samwillis maybe copy logo into this folder? or keep it in one place?
html_logo = "../../demosite/demo/static/logo.svg"

# html_theme_options = {
#     "announcement": "<em>Important</em> announcement!",
# }

# TODO: @samwillis maybe you want to have a short subtitle here.
# sidebar title
# html_title = "Full stack reactive component framework"
html_title = " "

html_theme_options = {
    # TODO: change repo to https://github.com/samwillis/tetra
    "source_repository": "https://github.com/nerdoc/tetra/",
    # TODO: change branch to "main"
    "source_branch": "sphinx",
    "source_directory": "docs/",
}
