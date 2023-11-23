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

<!-- Add conda and conda-forge if/when available -->

## Verify your installation

```
ragna --version
```
