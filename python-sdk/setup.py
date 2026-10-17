#!/usr/bin/env python3
from pathlib import Path
from setuptools import setup, find_packages

readme_file = Path(__file__).parent / "README.md"
long_desc = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="asteroidos",
    version="0.1.0",
    description="Python SDK and CLI for developing, building, packaging, and deploying AsteroidOS applications.",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "asteroidos": ["templates/**/*"],
    },
    entry_points={
        "console_scripts": [
            "asteroidos = asteroidos.cli:main",
        ],
    },
    python_requires=">=3.8",
)

