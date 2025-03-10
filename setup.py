from setuptools import setup, find_packages

setup(
    name="project_watch",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "pylint",
        "pytest",
        "coverage",
    ],
    python_requires=">=3.11",
)
