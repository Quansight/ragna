# Contribute

## Fork and clone the repository

```bash
git clone ...
```

## Set up development environment

Create and activate a conda environment:

```bash
conda env create --file environment.yaml
conda activate ragna-dev
```

Install Ragna in editable mode:

```bash
pip install --editable '.[complete]'
```

## Verify the installation

```bash
ragna --version
ragna ls
```

## Contribute documentation

Ragna uses Sphinx to build it's documentation.

You can contribute to the documentation at `docs/source`,
and start a development build that auto-refreshes on new changes with:

```bash
sphinx-autobuild docs/source docs/build/html
```

which serves the docs website at [http://127.0.0.1:8000](http://127.0.0.1:8000).
