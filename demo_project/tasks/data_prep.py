import pandas as pd
import numpy as np
from sklearn import datasets
from demo_project.common import Task
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
import warnings
import os
import boto3
import urllib
import pickle
from pyspark.sql import SparkSession
from io import BytesIO
from databricks.feature_store.online_store_spec import AmazonDynamoDBSpec
import uuid

from databricks import feature_store

from sklearn.model_selection import train_test_split

from databricks.feature_store import feature_table, FeatureLookup

import os
import datetime
from pyspark.dbutils import DBUtils

# Example usage:

spark = SparkSession.builder.appName("CSV Loading Example").getOrCreate()

dbutils = DBUtils(spark)

current_branch = dbutils.secrets.get(scope="secrets-scope", key="current_branch")


#warnings
warnings.filterwarnings('ignore')


class DataPrep(Task):

    def push_df_to_s3(self,df,access_key,secret_key):
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()

            s3 = boto3.resource("s3",aws_access_key_id=access_key, 
                      aws_secret_access_key=secret_key, 
                      region_name='ap-south-1')

            s3_object_key = self.conf['preprocessed'][current_branch]['preprocessed_df_path'] 
            s3.Object(self.conf['s3']['bucket_name'], s3_object_key).put(Body=csv_content)

            return {"df_push_status": 'success'}

    def _preprocess_data(self):
                
                

                aws_access_key = dbutils.secrets.get(scope="secrets-scope", key="aws-access-key")
                aws_secret_key = dbutils.secrets.get(scope="secrets-scope", key="aws-secret-key")
                
                
                access_key = aws_access_key 
                secret_key = aws_secret_key

                print(f"Access key and secret key are {access_key} and {secret_key}")

                
                
                encoded_secret_key = urllib.parse.quote(secret_key,safe="")

               
                s3 = boto3.resource("s3",aws_access_key_id=aws_access_key, 
                      aws_secret_access_key=aws_secret_key, 
                      region_name='ap-south-1')
                
                bucket_name =  self.conf['s3']['bucket_name']
                csv_file_key = self.conf['s3'][current_branch]['file_path']

                s3_object = s3.Object(bucket_name, csv_file_key)
                
                csv_content = s3_object.get()['Body'].read()

                df_input = pd.read_csv(BytesIO(csv_content))

                df_input = df_input.reset_index()
        
                numerical_cols = self.conf['features']['numerical_cols']
                

                categorical_cols = self.conf['features']['categorical_cols']

                df_encoded = df_input.copy()
                for col in df_encoded.select_dtypes(include=['object']):
                    df_encoded[col] = df_encoded[col].astype('category').cat.codes

                ordinal_cols = self.conf['features']['ordinal_cols']

                # Columns for one-hot encoding
                onehot_cols = self.conf['features']['onehot_cols']
                
                ordinal_encoder = OrdinalEncoder()
                df_input[ordinal_cols] = ordinal_encoder.fit_transform(df_input[ordinal_cols])

                onehot_encoded_data = pd.get_dummies(df_input[onehot_cols], drop_first=True)


                df_input = pd.concat([df_input.drop(onehot_cols, axis=1), onehot_encoded_data], axis=1)

                encoders_dict = {
                        'ordinal_encoder': ordinal_encoder,
                        # Add more encoders as needed
                    }
                
                pickled_data = pickle.dumps(encoders_dict)
                pkl_path = self.conf['preprocessed'][current_branch]['encoders_path']
                #s3.Object(bucket_name, pkl_path).put(Body=pickled_data)
                # push_status = self.push_df_to_s3(df_input)
                # print(push_status)

                df_input.rename(columns = {'index':'PATIENT_ID','Height_(cm)':'Height','Weight_(kg)':'Weight',
                'Diabetes_No, pre-diabetes or borderline diabetes':'Diabetes_No_pre-diabetes_or_borderline_diabetes',
                'Diabetes_Yes, but female told only during pregnancy':'Diabetes_Yes_but_female_told_only_during_pregnancy'}, inplace = True)


                spark.sql(f"CREATE DATABASE IF NOT EXISTS {self.conf['feature-store'][current_branch]['table_name']}")
                # Create a unique table name for each run. This prevents errors if you run the notebook multiple times.
                table_name = self.conf['feature-store'][current_branch]['table_name']
                print(table_name)

                df_feature = df_input.drop(self.conf['features']['target'],axis=1)

                df_spark = spark.createDataFrame(df_feature)

                fs = feature_store.FeatureStoreClient()

                fs.create_table(
                        name=table_name,
                        primary_keys=[self.conf['feature-store']['lookup_key']],
                        df=df_spark,
                        schema=df_spark.schema,
                        description="health features"
                    )
                
                push_status = self.push_df_to_s3(df_input,access_key,secret_key)
                print(push_status)

                print("Feature Store is created")

                online_store_spec = AmazonDynamoDBSpec(
                        region="us-west-2",
                        write_secret_prefix="feature-store-example-write/dynamo",
                        read_secret_prefix="feature-store-example-read/dynamo",
                        table_name = self.conf['feature-store'][current_branch]['online_table_name']
                        )
                
                fs.publish_table(table_name, online_store_spec)

                   
            

    def launch(self):
         
         self._preprocess_data()

   

def entrypoint():  
    
    task = DataPrep()
    task.launch()


if __name__ == '__main__':
    entrypoint()