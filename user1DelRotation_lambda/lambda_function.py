import json
import boto3
import os

iam = boto3.client('iam')
secretsmanager = boto3.client('secretsmanager')

def lambda_handler(event, context):
    
    # Getting the single secret value from the environment variable
    vsecret = os.getenv('secrets')

    # Fetching the secret details from Secrets Manager
    get_secret = secretsmanager.get_secret_value(SecretId=vsecret)
    secret_details = json.loads(get_secret['SecretString'])

    print(f"For user - {secret_details['UserName']}, inactive Access & Secret keys will be deleted.")
    
    # Extracting the key details from IAM
    key_response = iam.list_access_keys(UserName=secret_details['UserName'])
    
    # Inactive Key Deletion
    for key in key_response['AccessKeyMetadata']:
        if key['Status'] == 'Inactive':
            iam.delete_access_key(AccessKeyId=key['AccessKeyId'], UserName=secret_details['UserName'])
            print(f"An inactive key - {key['AccessKeyId']} of {secret_details['UserName']} has been deleted.")
    
    return "Process of inactive key deletion completed successfully."
