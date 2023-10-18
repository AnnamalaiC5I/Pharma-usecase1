from demo_project.common import Task
#from databricks_registry_webhooks import RegistryWebhooksClient, JobSpec, HttpUrlSpec
import boto3
import pandas as pd
from pyspark.sql import SparkSession
from io import BytesIO
from sklearn.metrics import confusion_matrix, accuracy_score
import numpy as np
from databricks import feature_store
from demo_project.tasks.utils import push_df_to_s3, read_data_from_s3
from pyspark.dbutils import DBUtils



fs = feature_store.FeatureStoreClient()

class ModelInference(Task):


    def _inference_data(self):
              
              spark = SparkSession.builder.appName("CSV Loading Example").getOrCreate()

              dbutils = DBUtils(spark)

              aws_access_key = dbutils.secrets.get(scope="secrets-scope", key="aws-access-key")
              aws_secret_key = dbutils.secrets.get(scope="secrets-scope", key="aws-secret-key")
              db_host = dbutils.secrets.get(scope="secrets-scope", key="databricks-host")
              db_token = dbutils.secrets.get(scope="secrets-scope", key="databricks-token")
              current_branch = dbutils.secrets.get(scope="secrets-scope", key="current_branch")

              s3 = boto3.resource("s3",aws_access_key_id=aws_access_key, 
                      aws_secret_access_key=aws_secret_key, 
                      region_name='us-west-2')
              
              bucket_name =  self.conf['s3']['bucket_name']
              x_test_key = self.conf['preprocessed'][current_branch]['x_test']

              y_test_key = self.conf['preprocessed'][current_branch]['y_test']

              x_test = read_data_from_s3(s3,bucket_name,x_test_key)

              print("X test")
              print(x_test)

              y_test = read_data_from_s3(s3,bucket_name,y_test_key)

              print("Y test")
              print(y_test)

              spark = SparkSession.builder.appName("CSV Loading Example").getOrCreate()

              rows = x_test.count()[0]
              random_patient_ids = np.random.randint(10000, 99999, size=rows)

              x_test['PATIENT_ID'] = random_patient_ids

              spark_test = spark.createDataFrame(x_test)

              test_pred = fs.score_batch(f"models:/pharma_{current_branch}/latest", spark_test)

              ans_test = test_pred.toPandas()

              y_test = y_test.reset_index()

              y_test.drop('index',axis=1,inplace=True)

              ans_test['actual'] = y_test

              output_df = ans_test[['prediction','actual']]

              print(confusion_matrix(output_df['prediction'],output_df['actual']))

              print(accuracy_score(output_df['prediction'],output_df['actual'])*100)


    def launch(self):
         
         self._inference_data()


def entrypoint():  
    
    task = ModelInference()
    task.launch()

if __name__ == '__main__':
    entrypoint()