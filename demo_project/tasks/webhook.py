from demo_project.common import Task

import json
import pandas as pd
import requests
import zipfile

from io import BytesIO

import boto3

from pyspark.sql import SparkSession
from pyspark.dbutils import DBUtils


import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from mlflow.utils.rest_utils import http_request
import json
def client():
  return mlflow.tracking.MlflowClient()
 
host_creds = client()._tracking_client.store.get_host_creds()


def mlflow_call_endpoint(endpoint, method, body='{}'):
  if method == 'GET':
      response = http_request(
          host_creds=host_creds, endpoint="/api/2.0/mlflow/{}".format(endpoint), method=method, params=json.loads(body))
  else:
      response = http_request(
          host_creds=host_creds, endpoint="/api/2.0/mlflow/{}".format(endpoint), method=method, 
          json=json.loads(body))
  return response.json()

class Datadrift(Task):


    def _data_drift(self):


        spark = SparkSession.builder.appName("CSV Loading Example").getOrCreate()

        dbutils = DBUtils(spark)

        aws_access_key = dbutils.secrets.get(scope="secrets-scope", key="aws-access-key")
        aws_secret_key = dbutils.secrets.get(scope="secrets-scope", key="aws-secret-key")
        db_host = dbutils.secrets.get(scope="secrets-scope", key="databricks-host")
        db_token = dbutils.secrets.get(scope="secrets-scope", key="databricks-token")
        current_branch = dbutils.secrets.get(scope='secrets-scope',key='current_branch')

        s3 = boto3.resource("s3",aws_access_key_id=aws_access_key, 
                      aws_secret_access_key=aws_secret_key, 
                      region_name='us-west-2')
              
        bucket_name =  self.conf['s3']['bucket_name']
        json_key = self.conf['Terraform']['json']
        
        key = current_branch+'_'+json_key
        s3_object = s3.Object(bucket_name, key)
                
        json_content = s3_object.get()['Body'].read().decode('utf-8')
        json_data = json.loads(json_content)

        job_id = json_data['id']

        print(json_content)

        lists = {
            "model_name":f"pharma_{current_branch}",
            "events": "MODEL_VERSION_TRANSITIONED_TO_PRODUCTION"
        }
        js_list_res = mlflow_call_endpoint('registry-webhooks/list', 'GET', json.dumps(lists))

        if js_list_res:
              print("Webhook is already created")

        else:
                diction = {
                                "job_spec": {
                                    "job_id": job_id,
                                    "access_token": db_token,
                                    "workspace_url": db_host
                                },
                                "events": [
                                    "MODEL_VERSION_TRANSITIONED_TO_PRODUCTION"
                                ],
                                "model_name": f"pharma_{current_branch}",
                                "description": "Webhook for Deployment Pipeline",
                                "status": "ACTIVE"
                                }

                job_json= json.dumps(diction)
                js_res = mlflow_call_endpoint('registry-webhooks/create', 'POST', job_json)
                print(js_res)

                print("Webhook Created for deployment job")

        

              
              

    def launch(self):
         
         self._data_drift()


def entrypoint():  
    
    task = Datadrift()
    task.launch()

if __name__ == '__main__':
    entrypoint()