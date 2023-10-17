import mlflow
from databricks.sdk import WorkspaceClient
from mlflow import MlflowClient

from mlflow.utils.rest_utils import http_request
import json

def client():
  return mlflow.tracking.client.MlflowClient()
 
host_creds = client()._tracking_client.store.get_host_creds()

client = MlflowClient()

db_token = dbutils.secrets.get(scope="secrets-scope", key="databricks-token")
db_host =  dbutils.secrets.get(scope="secrets-scope", key="databricks-host")
current_branch = dbutils.secrets.get(scope="secrets-scope", key="current_branch")
w = WorkspaceClient(host=db_host,token=db_token)


endpoint_name = 'my-model'
model_name=f'pharma_{current_branch}'

mlflow.set_tracking_uri('databricks')

def mlflow_call_endpoint(endpoint, method, body='{}'):
        if method == 'GET':
            response = http_request(
                host_creds=host_creds, endpoint="{}".format(endpoint), method=method, params=json.loads(body))
        else:
            response = http_request(
                host_creds=host_creds, endpoint="{}".format(endpoint), method=method, 
                json=json.loads(body))
        return response.json()
    
def find_staging_version(model_name):
            nw_dict = dict()
            for mv in w.model_registry.search_model_versions(filter=f"name='{model_name}'"):
                    #dic = dict(mv)  
                    dic = mv.__dict__
                    
                    #print(dic['run_id'])
                    if dic['current_stage']=='Staging':
                            d = w.experiments.get_run(run_id=dic['run_id']).run
                            #print(d.data.metrics) ---------->metrics
                            #print(dic['source'])
                            version = dic['version']
                            print(version)
                            #model_uri = dic['source']
                            #my_model = load_model(model_uri)
                            return version
                    else:
                        #print("No production model is ready")
                        pass
            
            return None
    
def find_production_version(model_name):
            nw_dict = dict()
            for mv in w.model_registry.search_model_versions(filter=f"name='{model_name}'"):
                    #dic = dict(mv)  
                    dic = mv.__dict__
                    
                    #print(dic['run_id'])
                    if dic['current_stage']=='Production':
                            d = w.experiments.get_run(run_id=dic['run_id']).run
                            #print(d.data.metrics) ---------->metrics
                            #print(dic['source'])
                            version = dic['version']
                            print(version)
                            #model_uri = dic['source']
                            #my_model = load_model(model_uri)
                            return version
                    else:
                        #print("No production model is ready")
                        pass
            
            return None
        


js_err = mlflow_call_endpoint(f'/api/2.0/serving-endpoints/{endpoint_name}', 'GET')
print(js_err)           
if 'error_code' not in js_err.keys():
    
    new_version = find_production_version(model_name)
    stag_version = find_staging_version(model_name)
    
    if stag_version == None:
                    if new_version != None:
                            print("updating the model")
                            new_config = {
                                    "served_models": [
                                        {
                                        "name": endpoint_name,
                                        "model_name": model_name,
                                        "model_version": new_version,
                                        "workload_size": "Small",
                                        "scale_to_zero_enabled": True,
                                        }
                                    ],
                                    "traffic_config": {
                                        "routes": [
                                        {
                                            "served_model_name": endpoint_name,
                                            "traffic_percentage": 100
                                        }
                                        ]
                                    }
                            }

                            js_res = mlflow_call_endpoint(f'/api/2.0/serving-endpoints/{endpoint_name}/config', 'PUT',json.dumps(new_config))
                            print("Model new version updated")

                    else:
                          print("No model version is in production.")
                          
                            
    elif new_version!= None and stag_version != None:
                        print("updating with canary deployment")
                        multimodel_config = {
                                   "served_models":[
                                      {
                                         "name":"current",
                                         "model_name":model_name,
                                         "model_version":new_version,
                                         "workload_size":"Small",
                                         "scale_to_zero_enabled":True
                                      },
                                      {
                                         "name":"challenger",
                                         "model_name":model_name,
                                         "model_version":stag_version,
                                         "workload_size":"Small",
                                         "scale_to_zero_enabled":True
                                      }
                                   ],
                                   "traffic_config":{
                                      "routes":[
                                         {
                                            "served_model_name":"current",
                                            "traffic_percentage":90
                                         },
                                         {
                                            "served_model_name":"challenger",
                                            "traffic_percentage":10
                                         }
                                      ]
                                   }
                                }
                        js_res = mlflow_call_endpoint(f'/api/2.0/serving-endpoints/{endpoint_name}/config', 'PUT',json.dumps(multimodel_config))
                        print("Multimodel deployed")
                        
    else:
          print("Check the configuration something is wrong.....!")

else:
        version = find_production_version(model_name)
        stag_version = find_staging_version(model_name)
        if version != None and stag_version==None:
                print("normal deployment")
                json_transtion = {
                                    "name": endpoint_name,
                                    "config": {
                                        "served_models": [
                                        {
                                            "name": endpoint_name,
                                            "model_name": model_name,
                                            "workload_size": "Small",
                                            "model_version": version,
                                            "scale_to_zero_enabled": True,
                                            
                                        }
                                        ],
                                        "traffic_config": {
                                        "routes": [
                                            {
                                            "served_model_name": endpoint_name,
                                            "traffic_percentage": 100
                                            }
                                        ]
                                        }
                                    }
                    }
                js_res = mlflow_call_endpoint('/api/2.0/serving-endpoints', 'POST',json.dumps(json_transtion))

        elif version != None and stag_version!=None:
                print("canary deployment")
                multimodel_config = {
                                   "served_models":[
                                      {
                                         "name":"current",
                                         "model_name":model_name,
                                         "model_version":version,
                                         "workload_size":"Small",
                                         "scale_to_zero_enabled":True
                                      },
                                      {
                                         "name":"challenger",
                                         "model_name":model_name,
                                         "model_version":stag_version,
                                         "workload_size":"Small",
                                         "scale_to_zero_enabled":True
                                      }
                                   ],
                                   "traffic_config":{
                                      "routes":[
                                         {
                                            "served_model_name":"current",
                                            "traffic_percentage":90
                                         },
                                         {
                                            "served_model_name":"challenger",
                                            "traffic_percentage":10
                                         }
                                      ]
                                   }
                                }
                config ={
                   "name":endpoint_name,
                   "config": multimodel_config
                  }
                js_res = mlflow_call_endpoint('/api/2.0/serving-endpoints', 'POST',json.dumps(config))
                print(js_res)
        else:
               print("No model version is in production.")