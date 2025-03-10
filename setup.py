from setuptools import setup, find_packages

setup(
    name="project_watch",
    version="0.1.0",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        "pylint",
        "pytest",
        "coverage",
    ],
    python_requires=">=3.11",
)
