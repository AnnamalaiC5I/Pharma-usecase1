import logging
from pathlib import Path

import mlflow
from pyspark.sql import SparkSession
from demo_project.tasks.sample_etl_task import SampleETLTask
from demo_project.tasks.sample_ml_task import SampleMLTask


def test_jobs(spark: SparkSession, tmp_path: Path):
   pass


