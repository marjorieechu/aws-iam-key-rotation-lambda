import boto3
import json
import logging
from botocore.exceptions import ClientError
from datetime import datetime

# Configuration Section: Update these variables
SECRET_ARN = "arn:aws:secretsmanager:us-east-1:533267247980:secret:Usercred-KuxnN4"  # Replace with your secret's ARN or name
IAM_USER_NAME = "del-admin1"  # Replace with your IAM username
DYNAMODB_TABLE_NAME = "SecretsRotationLog"  # Replace with your desired DynamoDB table name

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager_client = boto3.client('secretsmanager')
iam_client = boto3.client('iam')
dynamodb_client = boto3.client('dynamodb')
dynamodb_resource = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Extract information from the event triggered by AWS Secrets Manager
    secret_arn = event['SecretId']  # This is automatically passed by AWS Secrets Manager
    token = event['ClientRequestToken']
    step = event['Step']

    # Ensure DynamoDB table is created
    create_dynamodb_table_if_not_exists(DYNAMODB_TABLE_NAME)

    # Retrieve metadata about the secret
    metadata = secretsmanager_client.describe_secret(SecretId=secret_arn)
    current_version = [version for version, staged in metadata['VersionIdsToStages'].items() if 'AWSCURRENT' in staged][0]

    # Handle the different steps of the rotation process
    try:
        if step == "createSecret":
            create_secret(secret_arn, token)
        elif step == "setSecret":
            set_secret(secret_arn, token)
        elif step == "testSecret":
            test_secret(secret_arn, token)
        elif step == "finishSecret":
            finish_secret(secret_arn, token)
        else:
            raise ValueError("Invalid step parameter")

        # Log success to DynamoDB
        log_to_dynamodb(secret_arn, step, "SUCCESS")

    except Exception as e:
        logger.error(f"Error in step {step}: {e}")
        # Log failure to DynamoDB
        log_to_dynamodb(secret_arn, step, "FAILURE", str(e))
        raise e

def create_secret(secret_arn, token):
    try:
        # Retrieve the current secret value
        secret_value = secretsmanager_client.get_secret_value(SecretId=secret_arn, VersionStage="AWSCURRENT")
        current_secret = json.loads(secret_value['SecretString'])

        # Use the IAM user specified in the configuration section
        username = IAM_USER_NAME
        
        # Create a new access key for the specified IAM user
        response = iam_client.create_access_key(UserName=username)
        new_access_key = response['AccessKey']
        
        # Store the new key in Secrets Manager under the 'AWSPENDING' stage
        secretsmanager_client.put_secret_value(
            SecretId=secret_arn,
            ClientRequestToken=token,
            SecretString=json.dumps({
                "accessKeyId": new_access_key['AccessKeyId'],
                "secretAccessKey": new_access_key['SecretAccessKey'],
                "username": username
            }),
            VersionStages=['AWSPENDING']
        )
    except ClientError as e:
        logger.error(f"Error in create_secret: {e}")
        raise e

def set_secret(secret_arn, token):
    # No action needed in this example
    pass

def test_secret(secret_arn, token):
    try:
        # Retrieve the secret version that is pending to be set as current
        pending_secret_value = secretsmanager_client.get_secret_value(SecretId=secret_arn, VersionId=token)
        pending_secret = json.loads(pending_secret_value['SecretString'])

        # Test the new credentials by making a simple AWS service call
        test_client = boto3.client(
            's3',
            aws_access_key_id=pending_secret['accessKeyId'],
            aws_secret_access_key=pending_secret['secretAccessKey']
        )
        test_client.list_buckets()  # Simple call to validate new credentials
    except ClientError as e:
        logger.error(f"Error in test_secret: {e}")
        raise e

def finish_secret(secret_arn, token):
    try:
        # Promote the 'AWSPENDING' version to 'AWSCURRENT'
        secretsmanager_client.update_secret_version_stage(
            SecretId=secret_arn,
            VersionStage='AWSCURRENT',
            MoveToVersionId=token
        )

        # Retrieve the old secret value
        secret_value = secretsmanager_client.get_secret_value(SecretId=secret_arn, VersionStage="AWSPREVIOUS")
        previous_secret = json.loads(secret_value['SecretString'])

        # Use the IAM user specified in the configuration section
        username = IAM_USER_NAME
        
        # Deactivate and delete the old access key
        iam_client.update_access_key(
            AccessKeyId=previous_secret['accessKeyId'],
            Status='Inactive',
            UserName=username
        )

        iam_client.delete_access_key(
            AccessKeyId=previous_secret['accessKeyId'],
            UserName=username
        )
    except ClientError as e:
        logger.error(f"Error in finish_secret: {e}")
        raise e

def create_dynamodb_table_if_not_exists(table_name):
    try:
        # Check if the DynamoDB table already exists
        dynamodb_client.describe_table(TableName=table_name)
    except dynamodb_client.exceptions.ResourceNotFoundException:
        # If the table does not exist, create it
        logger.info(f"Creating DynamoDB table: {table_name}")
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'SecretArn',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'Timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'SecretArn',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'Timestamp',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        # Wait until the table exists.
        dynamodb_resource.Table(table_name).wait_until_exists()
        logger.info(f"DynamoDB table {table_name} created successfully.")

def log_to_dynamodb(secret_arn, step, status, error_message=None):
    try:
        # Insert log entry into DynamoDB table
        table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)
        table.put_item(
            Item={
                'SecretArn': secret_arn,
                'Step': step,
                'Status': status,
                'Timestamp': datetime.utcnow().isoformat(),
                'ErrorMessage': error_message if error_message else "None"
            }
        )
        logger.info(f"Logged to DynamoDB: SecretArn={secret_arn}, Step={step}, Status={status}")
    except ClientError as e:
        logger.error(f"Failed to log to DynamoDB: {e}")
