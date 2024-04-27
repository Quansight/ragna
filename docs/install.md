# Installation

## Prerequisites

You need Python 3.9 or above in your working environment to use Ragna.

## Install Ragna

You can install Ragna and all recommended dependencies with:

```bash
pip install 'ragna[all]'
```

If you want to install a minimal version[^1]:

```bash
pip install ragna
```

[^1]:
    The minimal version is for users who want fine-grained control over the dependencies
    needed for the builtin components.

And, upgrade to latest versions with:

```bash
pip install --upgrade ragna
```

Alternatively, you can install `ragna` with conda from conda-forge:

```bash
conda install ragna -c conda-forge
```

## Verify your installation

```
ragna --version
```

## Backwards compatibility

As an early-stage project and as long as we are on a `0.` version, we allow ourselves
the **option to break backwards compatibility**. This is done to accommodate feature
requests that require large refactorings, which inadvertently happen in the beginning.
The amount and severity of the breaking changes should diminish as the project matures.
All such changes will be announced in the [release notes](references/release-notes.md).
At some point, we'll release a `1.0.0` version and switch to
[SemVer](https://semver.org/), imposing strict backwards compatibility rules onto
ourselves.
