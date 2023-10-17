import os
import requests
import json
import subprocess


def get_current_git_branch():
    try:
        result = subprocess.run(['git', 'branch', '--show-current'], stdout=subprocess.PIPE, text=True, check=True)
        current_branch = result.stdout.strip()
        return current_branch
    except subprocess.CalledProcessError:
       
        return None

current_branch = get_current_git_branch()

print("The current branch is: ",current_branch)

host_url = os.environ.get('DATABRICKS_HOST')
host_token = os.environ.get('DATABRICKS_TOKEN')
c5_access  = os.environ.get('AWS_ACCESS_KEY')
c5_secret  = os.environ.get('AWS_SECRET_KEY')

db_yml = {'databricks_host': host_url[:-1] }

def make_databricks_api_request(host_url, method, json_data='{}', headers=None, params=None):
   
    # Construct the full URL for the API request
    url = f"{host_url}"
    
    # Create the request headers (if provided)
    if headers is None:
        headers = {}
    
    # Create the request parameters (if provided)
    if params is None:
        params = {}
    
    # Perform the API request based on the HTTP method
    if method == 'GET':
        response = requests.get(url, headers=headers, params=json.loads(json_data))
    elif method == 'POST':
        headers['Content-Type'] = 'application/json'
        response = requests.post(url, headers=headers, params=params, json=json.loads(json_data))
    elif method == 'PUT':
        headers['Content-Type'] = 'application/json'
        response = requests.put(url, headers=headers, params=params, json=json_data)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers, params=params)
    else:
        raise ValueError("Invalid HTTP method. Supported methods are GET, POST, PUT, and DELETE.")
    
    return response

headers = {
    "Authorization": f"Bearer {host_token}"
}


def add_secrets_to_scope(scope_name,scope_key,key_value):
            secret_config = {
            "scope": scope_name,
            "key": scope_key,
            "string_value": key_value,
            }

            secret_response = make_databricks_api_request(f"{db_yml['databricks_host']}/api/2.0/secrets/put", "POST", json.dumps(secret_config),headers)
            print('The scope response is',secret_response)


session = requests.Session()

scopes_list =  session.get(f"{db_yml['databricks_host']}/api/2.0/secrets/scopes/list",headers=headers)
print(db_yml['databricks_host'])
json_text = json.loads(scopes_list.text)
print(json_text)

scope_name = []
if not json_text:
    print("The dictionary is empty.")
    
else:
    print("The dictionary is not empty.")
    
    for scope in json_text['scopes']:
            scope_name.append(scope['name'])


            

def scope_check(scope_name,scope):
        if scope not in scope_name:         
                    secret_scope_config = {
                        "scope": scope,
                        "scope_backend_type": "DATABRICKS"
                        }
                    scope_response = make_databricks_api_request(f"{db_yml['databricks_host']}/api/2.0/secrets/scopes/create", "POST", json.dumps(secret_scope_config),headers)
                    print('The scope response is',scope_response)

        else:
                print(f"{scope} is already exist!! ")


scope_check(scope_name,'secrets-scope')
scope_check(scope_name,'feature-store-example-read')
scope_check(scope_name,'feature-store-example-write')


add_secrets_to_scope('secrets-scope',"databricks-token",host_token)
add_secrets_to_scope('secrets-scope',"databricks-host",host_url)
add_secrets_to_scope('secrets-scope',"aws-access-key",c5_access)
add_secrets_to_scope('secrets-scope','aws-secret-key',c5_secret)
add_secrets_to_scope('secrets-scope','current_branch',current_branch)

add_secrets_to_scope('feature-store-example-read','dynamo-access-key-id',c5_access)
add_secrets_to_scope('feature-store-example-read','dynamo-secret-access-key',c5_secret)


add_secrets_to_scope('feature-store-example-write','dynamo-access-key-id',c5_access)
add_secrets_to_scope('feature-store-example-write','dynamo-secret-access-key',c5_secret)
