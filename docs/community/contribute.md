# Contribution guidelines

Thanks for your interest in contributing to Ragna!

All Ragna development happens on [GitHub](https://github.com/Quansight/ragna).

If you'd like to contribute to an existing issue, make sure to comment on the issue to
communicate your interest. If you're interested in something new, open an issue first to
express interest and discuss the topic, implementation details, etc. with the Ragna
Development Team.

## Local development setup

To contribute to any part of the Ragna codebase (which includes documentation) you can
setup a local development space with the following instructions.

### Fork and clone the repository

You can refer to the GitHub documentation on how to
[fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) and
[clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
repositories.

Quick reference:

```bash
git clone https://github.com/<your-username>/ragna.git
```

### Set up development environment and run Ragna

We use [Pixi](https://pixi.sh/dev/) to manage development environments with Ragna.

Ragna has three main development environments: `dev-all-py310`, `dev-all-py311`, and
`dev-all-py312`, which use Python 3.10, 3.11, and 3.12, respectively. The environment
`dev-all` is the same as `dev-all-py310`. The environment `dev-all-py311` is used as an
example in the sections below, but you can use any of the three Python versions you
like.

To install and activate a development environment, run

```bash
pixi shell -e dev-all-py311
```

This will start a new shell and the executables like the `ragna` command will be
available.

Alternatively, to just run Ragna in a development environment without activating it in
your current shell, you can run

```bash
pixi run -e dev-all-py311 ragna deploy
```

In either case, you can verify that a development version of Ragna is correctly
installed with

```bash
pixi run -e dev-all-py311 ragna --version
# Ideal output: ragna <version-number> devXXXX from ...
```

### Testing, formatting, linting, and type checking

#### Testing

If you have activated a Pixi shell using `pixi shell -e dev-all-py311`, for example, you
can run Ragna tests with

```bash
pytest
```

If you want to run Ragna tests without activating a Pixi shell, you may run them with
either

```bash
pixi run -e dev-all-py311 pytest
```

or

```bash
pixi run -e dev-all-py311 test
```

#### Formatting

To run the [Ruff code formatter](https://docs.astral.sh/ruff/formatter/), you can run

```bash
ruff format ragna
```

if you have the Pixi shell activated, or, alternatively, if you don't want to activate
the Pixi shell, you can run either

```bash
pixi run -e dev-all-py311 ruff format ragna
```

or

```bash
pixi run -e dev-all-py311 ruff fmt
```

#### Linting

Similarly, the options for using the
[Ruff code linter](https://docs.astral.sh/ruff/linter/) are

```bash
ruff check --fix ragna
```

if you have the Pixi shell activated.

You can use

```bash
pixi run -e dev-all-py311 ruff check --fix ragna
```

or

```bash
pixi run -e dev-all-py311 lint
```

if you don't want to activate the Pixi shell.

#### Type checking

Checking type annotations with [Mypy](https://mypy-lang.org/) is again similar with

```bash
mypy
```

with the Pixi shell activated.

Use

```bash
pixi run -e dev-all-py311 mypy
```

or

```bash
pixi run -e dev-all-py311 types
```

if you don't want to activate the Pixi shell.

#### All of the above

To run all the above checks using one single command, you can run

```bash
pixi run -e dev-all-py311 all
```

with or without the Pixi shell activated.

### Setup pre-commit hooks (optional)

To maintain code standards, you can install some pre-commit hooks that check your
contributions when you commit them:

```bash
pre-commit install
```

These checks are also run in the CI on each pull request.

## Contribute documentation

Ragna uses the [Diátaxis framework](https://diataxis.fr/) and the
[Google developer documentation style guide](https://developers.google.com/style/) to
author documentation, [MkDocs](https://www.mkdocs.org/) to generate the documentation
website, and [ReadTheDocs](https://readthedocs.org/projects/ragna/) to serve the
website.

You can contribute to narrative documentation by adding and updating files in the `docs`
directory.

<!-- TODO: Add notes on contributing examples once we decide the workflow -->

To start a development build of the website that auto-refreshes on new changes, run the
following from the project root:

```bash
mkdocs serve
```

if you have a Pixi shell for a development environment (e.g. `dev-all`) activated.

Otherwise, you can run

```bash
pixi run -e dev-all mkdocs serve
```

These both serves the docs website at [http://127.0.0.1:8000](http://127.0.0.1:8000).

You must use a `dev-all*` environment to build the docs.

### View, add, or update images

Ragna tracks most image files with [`git-lfs`](https://git-lfs.com).

As a first-time user of `git-lfs`, set it up with:

```bash
git lfs install
```

To pull all image files to your local repository, run:

```bash
git lfs pull
```

All new or updated images will be tracked by `git-lfs`. To verify the files being
tracked, run:

```bash
git lfs ls-files
```

## Contribution best practices

- Before opening new issues, go through the tracker to ensure there aren't any previous
  issues related to your topic.
- Write clear and descriptive issues and include all the necessary context like library
  versions and the complete error traceback.
- Eagerly communicate if you are interested in contributing to any open issues.
- To contribute new features and enhancements, open issues to discuss the work before
  creating a pull request.
- Make sure to test your pull request locally, and include relevant unit tests and
  documentation.
