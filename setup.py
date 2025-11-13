"""Setup script for ntop-aerodeck."""
from setuptools import setup, find_packages

setup(
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "aerodeck": ["output/templates/*.html", "output/templates/*.md"],
    },
)
