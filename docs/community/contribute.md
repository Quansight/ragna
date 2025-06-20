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

We use [Pixi](https://pixi.sh/dev/) to manage development environments with Ragna. The
main development environment is `all-py310`, which should be used for most use cases and
is used in the sections below.

To install a development environment, run

```bash
pixi install --environment all-py310 --frozen
```

You can then run Ragna with

```bash
pixi run --environment all-py310 ragna deploy
```

You can verify that a development version of Ragna is correctly installed with

```bash
pixi run --environment all-py310 ragna --version
# Ideal output: ragna <version-number> devXXXX from ...
```

### Testing, formatting, linting, and type checking

#### Setup pre-commit hooks

To maintain code standards, we use pre-commit hooks that check contributions before they
are committed. To install them, run:

```bash
pre-commit install --install-hooks
```

These checks are used to run the code formatter and linter. They are also run in the CI
on each pull request.

#### Testing

You can run Ragna tests with

```bash
pixi run --environment all-py310 test
```

#### Formatting & Linting

To run the [Ruff code formatter and checker](https://docs.astral.sh/ruff/formatter/), as
well as other useful formatting and linting tools, you can use

```bash
pixi run --environment all-py310 pre-commit
```

#### Type checking

You can check type annotations with [Mypy](https://mypy-lang.org/) using

```bash
pixi run --environment all-py310 types
```

or

```bash
pixi run --environment all-py310 mypy
```

#### All of the above

To run all the above checks using a single command as they would be run on the CI, you
can use

```bash
pixi run ---environment all-py310 ci
```

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
pixi run --environment all-py310 mkdocs serve
```

This serves the docs website at [http://127.0.0.1:8000](http://127.0.0.1:8000).

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
