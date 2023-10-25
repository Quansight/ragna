# Contribute to Ragna

<!-- TODO: expand and add more narration -->

## Fork and clone the repository

```bash
git clone https://github.com/<your-username>/ragna.git
```

## Set up development environment

Create and activate a conda environment:

```bash
conda env create --file environment.yaml
conda activate ragna-dev
```

## Contribute code

Install Ragna in editable mode:

```bash
pip install --editable '.[complete]'
```

Verify your installation:

```bash
ragna --version
ragna ls
```

## Contribute documentation

Ragna uses MkDocs to build it's documentation.

You can contribute to narrative documentation at `docs/`, and configure the docs website
using `mkdocs.yml`

To start a development build that auto-refreshes on new changes, run the following from
the root directory:

```bash
mkdocs serve
```

This serves the docs website at [http://127.0.0.1:8000](http://127.0.0.1:8000).
