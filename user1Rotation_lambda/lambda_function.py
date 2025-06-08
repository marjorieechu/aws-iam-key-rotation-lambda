import json
import boto3
import os

iam = boto3.client('iam')
secretsmanager = boto3.client('secretsmanager')

def lambda_handler(event, context):
    
    # Getting the single secret value from environment variable
    vsecret = os.getenv('secrets')

    # Fetching the secret details from Secrets Manager
    get_secret = secretsmanager.get_secret_value(SecretId=vsecret)
    secret_details = json.loads(get_secret['SecretString'])

    print(f"For user - {secret_details['UserName']}, Access & Secret keys will be inactivated.")
    
    # Extracting the key details from IAM
    key_response = iam.list_access_keys(UserName=secret_details['UserName'])
    
    # Inactivating existing keys
    for key in key_response['AccessKeyMetadata']:
        if key['Status'] == 'Active':
            iam.update_access_key(AccessKeyId=key['AccessKeyId'], Status='Inactive', UserName=secret_details['UserName'])
            print(f"{key['AccessKeyId']} key of {secret_details['UserName']} has been inactivated.")
    
    # Creating a new set of keys
    create_response = iam.create_access_key(UserName=secret_details['UserName'])
    print(f"A new set of keys has been created for user - {secret_details['UserName']}")
    
    # Updating the secret with new key details
    NewSecret = json.dumps({
        "UserName": create_response['AccessKey']['UserName'],
        "AccessKeyId": create_response['AccessKey']['AccessKeyId'],
        "SecretAccessKey": create_response['AccessKey']['SecretAccessKey']
    })
    secretsmanager.update_secret(SecretId=vsecret, SecretString=NewSecret)
    print(f"{vsecret} secret has been updated with the latest key details for {secret_details['UserName']}.")

    return "Key creation & secret update process completed successfully."
