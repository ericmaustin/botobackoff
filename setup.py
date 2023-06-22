from setuptools import setup, find_packages

# read the contents of your README file
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="botobackoff",
    description="boto3 retry and backoff utility",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Eric Austin",
    url="https://github.com/ericmaustin/botobackoff",
    license="MIT",
    author_email="eric.m.austin@gmail.com",
    python_requires=">=3.7",
    version="0.0.2",
    include_package_data=True,
    packages=find_packages(),
    install_requires=[
        "boto3>=1.16.0",
        "botocore"
    ]
)