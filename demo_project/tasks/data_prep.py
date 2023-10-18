import pandas as pd
from demo_project.common import Task
from sklearn.preprocessing import OrdinalEncoder
import warnings
import boto3
import urllib
import pickle
from pyspark.sql import SparkSession
from io import BytesIO
from databricks.feature_store.online_store_spec import AmazonDynamoDBSpec
from demo_project.tasks.utils import push_df_to_s3, read_data_from_s3, preprocess
from databricks import feature_store
from pyspark.dbutils import DBUtils

# Example usage:

spark = SparkSession.builder.appName("CSV Loading Example").getOrCreate()

dbutils = DBUtils(spark)

current_branch = dbutils.secrets.get(scope="secrets-scope", key="current_branch")


#warnings
warnings.filterwarnings('ignore')


class DataPrep(Task):


    def _preprocess_data(self):
                
                

                aws_access_key = dbutils.secrets.get(scope="secrets-scope", key="aws-access-key")
                aws_secret_key = dbutils.secrets.get(scope="secrets-scope", key="aws-secret-key")
                
                
                access_key = aws_access_key 
                secret_key = aws_secret_key

                print(f"Access key and secret key are {access_key} and {secret_key}")

               
                s3 = boto3.resource("s3",aws_access_key_id=aws_access_key, 
                      aws_secret_access_key=aws_secret_key, 
                      region_name='ap-south-1')
                
                bucket_name =  self.conf['s3']['bucket_name']
                csv_file_key = self.conf['s3'][current_branch]['file_path']

                df_input = read_data_from_s3(s3,bucket_name, csv_file_key)

                df_input = df_input.reset_index()
        

                df_feature, df_input = preprocess(spark,self.conf,df_input,current_branch)   

                df_spark = spark.createDataFrame(df_feature)

                fs = feature_store.FeatureStoreClient()

                fs.create_table(
                        name=self.conf['feature-store'][current_branch]['table_name'],
                        primary_keys=[self.conf['feature-store']['lookup_key']],
                        df=df_spark,
                        schema=df_spark.schema,
                        description="health features"
                    )
                s3_object_key = self.conf['preprocessed'][current_branch]['preprocessed_df_path'] 
                push_status = push_df_to_s3(df_input,s3_object_key,access_key,secret_key,self.conf)
                print(push_status)

                print("Feature Store is created")

                online_store_spec = AmazonDynamoDBSpec(
                        region="us-west-2",
                        write_secret_prefix="feature-store-example-write/dynamo",
                        read_secret_prefix="feature-store-example-read/dynamo",
                        table_name = self.conf['feature-store'][current_branch]['online_table_name']
                        )
                
                fs.publish_table(self.conf['feature-store'][current_branch]['table_name'], online_store_spec)

                   
            

    def launch(self):
         
         self._preprocess_data()

   

def entrypoint():  
    
    task = DataPrep()
    task.launch()


if __name__ == '__main__':
    entrypoint()