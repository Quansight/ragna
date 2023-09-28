# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import datetime
import importlib.metadata

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Ragna"
metadata = importlib.metadata.metadata("Ragna")

author = ", ".join(
    author_email.split("<", 1)[0].strip()
    for author_email in metadata["Author-email"].split(",")
)
copyright = f"{datetime.datetime.today().year}, {author}"

release = metadata["Version"]
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # https://myst-parser.readthedocs.io/en/latest/intro.html
    "myst_parser",
    # https://sphinx-design.readthedocs.io/en/latest/index.html
    "sphinx_design",
    # https://sphinx-inline-tabs.readthedocs.io/en/latest/
    "sphinx_inline_tabs",
    # https://sphinx-copybutton.readthedocs.io/en/latest/
    "sphinx_copybutton",
    # https://sphinxext-opengraph.readthedocs.io/en/latest/
    "sphinxext.opengraph",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# https://pradyunsg.me/furo/
html_theme = "furo"
html_static_path = ["_static"]
