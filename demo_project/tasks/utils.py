from io import BytesIO
import boto3
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder

def push_df_to_s3(df,s3_object_key,access_key,secret_key,conf):
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()

            s3 = boto3.resource("s3",aws_access_key_id=access_key, 
                      aws_secret_access_key=secret_key, 
                      region_name='ap-south-1')

            #s3_object_key = conf['preprocessed'][branch]['preprocessed_df_path'] 
            s3.Object(conf['s3']['bucket_name'], s3_object_key).put(Body=csv_content)

            return {"df_push_status": 'success'}

def read_data_from_s3(s3,bucket_name, csv_file_key):
        
        s3_object = s3.Object(bucket_name, csv_file_key)

        csv_content = s3_object.get()['Body'].read()

        df_input = pd.read_csv(BytesIO(csv_content))

        return df_input  

def preprocess(spark,configure,df_input,current_branch):
    numerical_cols = configure['features']['numerical_cols']
    
    categorical_cols = configure['features']['categorical_cols']

    df_encoded = df_input.copy()
    for col in df_encoded.select_dtypes(include=['object']):
        df_encoded[col] = df_encoded[col].astype('category').cat.codes

    ordinal_cols = configure['features']['ordinal_cols']

    # Columns for one-hot encoding
    onehot_cols = configure['features']['onehot_cols']
    
    ordinal_encoder = OrdinalEncoder()
    df_input[ordinal_cols] = ordinal_encoder.fit_transform(df_input[ordinal_cols])

    onehot_encoded_data = pd.get_dummies(df_input[onehot_cols], drop_first=True)


    df_input = pd.concat([df_input.drop(onehot_cols, axis=1), onehot_encoded_data], axis=1)

    encoders_dict = {
            'ordinal_encoder': ordinal_encoder,
            # Add more encoders as needed
        }
    
    
    df_input.rename(columns = {'index':'PATIENT_ID','Height_(cm)':'Height','Weight_(kg)':'Weight',
    'Diabetes_No, pre-diabetes or borderline diabetes':'Diabetes_No_pre-diabetes_or_borderline_diabetes',
    'Diabetes_Yes, but female told only during pregnancy':'Diabetes_Yes_but_female_told_only_during_pregnancy'}, inplace = True)


    spark.sql(f"CREATE DATABASE IF NOT EXISTS {configure['feature-store']['DB']}")
    print('pharma db created')
    # Create a unique table name for each run. This prevents errors if you run the notebook multiple times.
    table_name = configure['feature-store'][current_branch]['table_name']
    print(table_name)

    df_feature = df_input.drop(configure['features']['target'],axis=1)

    return df_feature, df_input

