"""
This file configures the Python package with entrypoints used for future runs on Databricks.

Please follow the `entry_points` documentation for more details on how to configure the entrypoint:
* https://setuptools.pypa.io/en/latest/userguide/entry_point.html
"""

from setuptools import find_packages, setup
from demo_project import __version__

PACKAGE_REQUIREMENTS = ["pyyaml"]

# packages for local development
# please note that these packages are already available in DBR, there is no need to install them on DBR.
LOCAL_REQUIREMENTS = [
    "pyspark==3.2.1",
    "boto3",
    #"protobuf==3.20.1",
    "delta-spark==1.1.0",
    "scikit-learn==1.2.0",
    "databricks-sdk",
    "databricks-feature-store",
    "evidently",
    "pandas==1.5.3",
    "mlflow",
    "urllib3"
]

TEST_REQUIREMENTS = [
    # development & testing tools
    "pytest",
    "coverage[toml]",
    "pytest-cov",
    "dbx>=0.8"
]

setup(
    name="demo_project",
    packages=find_packages( exclude=["tests", "tests.*"]),
    setup_requires=["setuptools","wheel"],
    install_requires=LOCAL_REQUIREMENTS,
    extras_require={"local": LOCAL_REQUIREMENTS, "test": TEST_REQUIREMENTS},
    entry_points = {
        "console_scripts": [
            "data_prep = demo_project.tasks.data_prep:entrypoint",
            "model_train = demo_project.tasks.model_train:entrypoint", 
            "model_inference = demo_project.tasks.model_inference:entrypoint",
            "webhook = demo_project.tasks.webhook:entrypoint"
    ]},
    version=__version__,
    description="",
    author="",
)
