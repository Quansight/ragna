from setuptools import find_packages, setup

# Read requirements from requirements.txt
with open("requirements-base.txt") as f:
    install_requires = f.read().splitlines()
    print(f)

setup(
    name="ragna-base",
    description="RAG orchestration framework",
    license="BSD 3-Clause License",
    author="Ragna Development Team",
    author_email="connect@quansight.com",
    url="https://ragna.chat",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    packages=find_packages(),
    scripts=["ragna/__main__.py"],
    install_requires=install_requires,  # Use dependencies from requirements.txt
    setup_requires=[
        "setuptools>=45",
        "setuptools_scm[toml]>=6.2",
    ],
    extras_require={
        "optional": [],
    },
    package_data={},
    include_package_data=True,
    entry_points={},
    # Ruff configuration
    ruff={
        "lint": {
            "select": [
                "E",
                "F",
                # import sorting
                "I001",
            ],
            # Ignore line too long, because due to black, the error can only occur for strings
            "ignore": ["E501"],
            "per-file-ignores": {
                # ignore unused imports and imports not at the top of the file in __init__.py files
                "__init__.py": ["F401", "E402"],
                # The examples often have imports below the top of the file to follow the narrative
                "docs/examples/**/*.py": ["E402", "F704", "I001"],
                "docs/tutorials/**/*.py": ["E402", "F704", "I001"],
            },
        }
    },
    # Pytest configuration
    pytest={
        "ini_options": {
            "minversion": "6.0",
            "addopts": "-ra --tb=short --asyncio-mode=auto",
            "testpaths": ["tests"],
            "filterwarnings": [
                "error",
                "ignore::ResourceWarning",
                # httpx 0.27.0 deprecated some functionality that the test client of starlette /
                # FastApi use. This should be resolved by the next release of these libraries.
                # See https://github.com/encode/starlette/issues/2524
                "ignore:The 'app' shortcut is now deprecated:DeprecationWarning",
            ],
            "xfail_strict": True,
        }
    },
    # Mypy configuration
    mypy={
        "files": "ragna",
        "plugins": ["sqlmypy"],
        "show_error_codes": True,
        "pretty": True,
        "disallow_untyped_calls": True,
        "disallow_untyped_defs": True,
        "disallow_incomplete_defs": True,
        "allow_redefinition": True,
        "no_implicit_optional": True,
        "warn_redundant_casts": True,
        "warn_unused_ignores": True,
        "warn_return_any": True,
        "warn_unused_configs": True,
        "overrides": [
            {
                "module": ["ragna.deploy._ui.*"],
                "disallow_untyped_calls": False,
                "disallow_untyped_defs": False,
                "disallow_incomplete_defs": False,
            },
            {
                "module": [
                    "docx",
                    "fitz",
                    "ijson",
                    "lancedb",
                    "param",
                    "pptx",
                    "pyarrow",
                    "sentence_transformers",
                ],
                "ignore_missing_imports": True,
            },
            {
                "module": ["ragna.deploy._api.orm"],
                "disable_error_code": ["var-annotated"],
            },
            {
                "module": ["ragna.source_storages.*", "ragna.assistants.*"],
                "disable_error_code": ["override"],
            },
        ],
    },
)
