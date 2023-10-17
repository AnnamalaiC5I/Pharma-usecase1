import pandas as pd

from demo_project.common import Task

from sklearn.model_selection import train_test_split

import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score
import warnings
import os
import boto3
import pickle



from io import BytesIO
from urllib.parse import urlparse
import mlflow

from mlflow.tracking.client import MlflowClient

from databricks.feature_store import feature_table, FeatureLookup

from pyspark.sql import SparkSession

from databricks import feature_store

from pyspark.dbutils import DBUtils

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, r2_score, auc, roc_curve

warnings.filterwarnings('ignore')

fs = feature_store.FeatureStoreClient()

spark = SparkSession.builder.appName("CSV Loading Example").getOrCreate()

dbutils = DBUtils(spark)
current_branch = dbutils.secrets.get(scope="secrets-scope", key="current_branch")

class Trainmodel(Task):
    

    def train_model(self, X_train, X_test, y_train, y_test, training_set, fs):
                        
                        mlflow.set_experiment(self.conf['Mlflow'][current_branch]['experiment_name'])
                        with mlflow.start_run(run_name=self.conf['Mlflow'][current_branch]['run_name']) as run:
                        
                                LR_Classifier = LogisticRegression(
                                                        C=self.conf['LogisticReg']['C'],
                                                        penalty=self.conf['LogisticReg']['penalty'],
                                                        solver=self.conf['LogisticReg']['solver'],
                                                        class_weight=self.conf['LogisticReg']['class_weight']
                                                        )
                                LR_Classifier.fit(X_train, y_train)
                                y_pred = LR_Classifier.predict(X_test)
                        
                                #mlflow.log_metric("test_mse", mean_squared_error(y_test, y_pred))
                                #mlflow.log_metric("test_r2_score", r2_score(y_test, y_pred))
                                fpr, tpr, threshold = roc_curve(y_test,y_pred)
                                roc_auc = auc(fpr, tpr)
                                f1_train = f1_score(y_test,y_pred)
                                mlflow.log_metric("train_f1score",f1_train)
                                mlflow.log_metric("roc_auc",roc_auc)
                        
                                fs.log_model(
                                model=LR_Classifier,
                                artifact_path="health_prediction",
                                flavor=mlflow.sklearn,
                                training_set=training_set,
                                registered_model_name="pharma_model",
                                )
    

    def push_df_to_s3(self,df,s3_object_key,access_key,secret_key):
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()

            s3 = boto3.resource("s3",aws_access_key_id=access_key, 
                      aws_secret_access_key=secret_key, 
                      region_name='ap-south-1')

            
            s3.Object(self.conf['s3']['bucket_name'], s3_object_key).put(Body=csv_content)

            return {"df_push_status": 'success'}

    def load_data(self, table_name, lookup_key,target, inference_data_df):
                    # In the FeatureLookup, if you do not provide the `feature_names` parameter, all features except primary keys are returned
                    model_feature_lookups = [FeatureLookup(table_name=table_name, lookup_key=lookup_key)]
                
                    # fs.create_training_set looks up features in model_feature_lookups that match the primary key from inference_data_df
                    training_set = fs.create_training_set(inference_data_df, model_feature_lookups, label=target,exclude_columns=lookup_key)
                    training_pd = training_set.load_df().toPandas()
                
                    # Create train and test datasets
                    X = training_pd.drop(target, axis=1)
                    y = training_pd[target]
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=self.conf['ModelTraining']['test_split'], random_state=42)

                    X_train_pre, X_val, y_train_pre, y_val = train_test_split(X_train, y_train, test_size=self.conf['ModelTraining']['validation_split'], random_state=43)
                    return X_train_pre, X_test, y_train_pre, y_test, X_val, y_val, training_set

    def _train_model(self):
                
                

                aws_access_key = dbutils.secrets.get(scope="secrets-scope", key="aws-access-key")
                aws_secret_key = dbutils.secrets.get(scope="secrets-scope", key="aws-secret-key")
                
                
                s3 = boto3.resource("s3",aws_access_key_id=aws_access_key, 
                      aws_secret_access_key=aws_secret_key, 
                      region_name='ap-south-1')
                
                bucket_name =  self.conf['s3']['bucket_name']
                csv_file_key = self.conf['preprocessed'][current_branch]['preprocessed_df_path']

                
                s3_object = s3.Object(bucket_name, csv_file_key)
                
                csv_content = s3_object.get()['Body'].read()

                df_input = pd.read_csv(BytesIO(csv_content))

                

                df_input_spark = spark.createDataFrame(df_input)

                inference_data_df = df_input_spark.select(self.conf['feature-store']['lookup_key'], self.conf['features']['target'])

                X_train, X_test, y_train, y_test, X_val, y_val, training_set = self.load_data(self.conf['feature-store'][current_branch]['table_name'], self.conf['feature-store']['lookup_key'],self.conf['features']['target'],inference_data_df)
        
                client = MlflowClient()
 

                self.train_model(X_train, X_val, y_train, y_val, training_set, fs)

                self.push_df_to_s3(X_test,self.conf['preprocessed'][current_branch]['x_test'],aws_access_key,aws_secret_key)

                self.push_df_to_s3(y_test,self.conf['preprocessed'][current_branch]['y_test'],aws_access_key,aws_secret_key)


                print("Model training is done")


                


    def launch(self):
         
         self._train_model()

    

def entrypoint():  
    
    task = Trainmodel()
    task.launch()

if __name__ == '__main__':
    entrypoint()