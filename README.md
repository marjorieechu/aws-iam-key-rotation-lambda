DETAILED INSTRUCTION TO GUIDE YOU TOWARDS COMPLETING THIS DEMO

# AWS IAM Key Rotation with Lambda Functions

This project contains two Lambda functions to automate the key rotation process for IAM users:

1. **Key Rotation Creation**: Inactivates existing active keys and creates new keys.
2. **Key Rotation Deletion**: Deletes inactive keys.

## Project Structure

## Prerequisites

- AWS CLI configured with sufficient permissions (IAM and Secrets Manager).
- AWS Lambda with the appropriate execution roles.
- AWS Secrets Manager set up to store IAM credentials for users.

## Setup Instructions

### Step 1: Upload Lambda Functions

1. Go to the AWS Management Console.
2. Navigate to **Lambda**.
3. Create two Lambda functions:
   - One for key creation and inactivation (`key_rotation_create/lambda_function.zip`).
   - One for deleting inactive keys (`key_rotation_del/lambda_function.zip`).
4. Upload the ZIP files for both functions in their respective Lambda functions.

### Step 2: Set Up Secrets in AWS Secrets Manager

1. Go to **Secrets Manager** in AWS Management Console.
2. Create a new secret for each IAM user with the following structure in the **Secret Value**:

   ```json
   {
     "UserName": "IAM_User_Name",
     "AccessKeyId": "AKIA...",
     "SecretAccessKey": "YourSecretKey..."
   }
   ```

Replace IAM_User_Name with the actual IAM username.
Replace AccessKeyId and SecretAccessKey with the current key pair for that IAM user.
Save the secret and note the Secret ARN.

### Step 3: Set Up Lambda Environment Variables

For each Lambda function, you need to set up environment variables:

Go to the Configuration section of each Lambda function.
Add a new environment variable:

- Key: secrets
- Value: A semicolon-separated list of Secret ARNs (e.g., arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret1;arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret2).

### Step 4: Set Up IAM Roles for Lambda Functions

The Lambda functions require permissions to access IAM and Secrets Manager. Ensure the following permissions are attached to the Lambda execution role:

- secretsmanager:GetSecretValue
- secretsmanager:UpdateSecret
- iam:ListAccessKeys
- iam:UpdateAccessKey
- iam:CreateAccessKey
- iam:DeleteAccessKey

### Step 5: Testing and Invocation

You can invoke the Lambda functions directly using the AWS Management Console or AWS CLI.

## Using AWS CLI:

For the creation/inactivation Lambda function:

`aws lambda invoke --function-name <Your_Lambda_Function_Name_Create> response.json`

Sample Output: The response.json will contain logs such as:

{
"For user - username, Access & Secret keys will be inactivated."
"key has been inactivated."
"A new set of keys has been created for user - username."
}

CloudWatch Logs: You can also check the logs of your Lambda functions in CloudWatch for detailed output.

### Step 6: Verify Key Rotation

Check in Secrets Manager: After invoking the create Lambda, check in AWS Secrets Manager to see if the secret has been updated with new key details.

Check in IAM: Go to the IAM Console and ensure the old keys are inactivated, new keys are created, and inactive keys are deleted.

## Clean Up

Once the project is complete or no longer needed, make sure to clean up the resources by:

1. \*\*Deleting the Lambda functions.
2. \*\*Deleting the secrets in AWS Secrets Manager.
3. \*\*Removing any related IAM policies and roles.

## Step 7: Setup Automatic trigger; when lambda one runs to completion to trigger lambda two

1. AWS Step Functions (Recommended)
   AWS Step Functions allow you to orchestrate multiple Lambda functions and other AWS services in a sequence. You can configure it so that after Lambda One completes successfully, Lambda Two is automatically triggered.

### Steps to Use Step Functions:

1. \*\*Create a State Machine in AWS Step Functions.
2. \*\*Define the workflow as follows:
   - First, invoke Lambda One.
   - On successful completion of Lambda One, invoke Lambda Two.
3. \*\*If Lambda One fails, you can handle the error by either retrying or notifying you.
   Example of a Step Function Definition:

   ```json
   {
     "StartAt": "RunLambdaOne",
     "States": {
       "RunLambdaOne": {
         "Type": "Task",
         "Resource": "arn:aws:lambda:region:account-id:function:lambda-one-name",
         "Next": "RunLambdaTwo",
         "Catch": [
           {
             "ErrorEquals": ["States.ALL"],
             "Next": "FailState"
           }
         ]
       },
       "RunLambdaTwo": {
         "Type": "Task",
         "Resource": "arn:aws:lambda:region:account-id:function:lambda-two-name",
         "End": true
       },
       "FailState": {
         "Type": "Fail",
         "Cause": "Lambda One failed"
       }
     }
   }
   ```

This will ensure that Lambda Two runs only after Lambda One completes successfully.

2. Amazon EventBridge
   EventBridge can be used to create a rule that triggers Lambda Two based on the completion of Lambda One.

Steps to Use EventBridge:

1. \*\*Add a Success Event: You can configure Lambda One to send an event to EventBridge upon successful execution.
2. \*\*Create an EventBridge Rule: Create a rule that listens for this event and triggers Lambda Two when the event occurs.

#### Example Lambda One Modification to Trigger Event:

#### Modify Lambda One to publish an event to EventBridge after it successfully completes:

      import json
      import boto3
      import os

      iam = boto3.client('iam')
      secretsmanager = boto3.client('secretsmanager')
      eventbridge = boto3.client('events')

      def lambda_handler(event, context):

         # Your existing key rotation logic here...

         # If Lambda One completes successfully, publish an event to EventBridge
         response = eventbridge.put_events(
            Entries=[
                  {
                     'Source': 'my.custom.lambda.one',
                     'DetailType': 'LambdaOneCompleted',
                     'Detail': json.dumps({'status': 'success'}),
                     'EventBusName': 'default'
                  }
            ]
         )
         print("Event triggered after Lambda One completion.")

         return "Process key creation & secret update has completed successfully."

### Set Up EventBridge Rule:

1. \*\*Create a new EventBridge rule that listens for this custom event:
   - Event Source: my.custom.lambda.one
   - Detail Type: LambdaOneCompleted
2. \*\*Set Lambda Two as the target for this rule.
   This way, when Lambda One finishes, it will send an event to EventBridge, which in turn triggers Lambda Two.

### Note:

- Step Functions: The best approach if you want more control over the orchestration, retries, and monitoring of the workflow.
- EventBridge: A simpler solution that works well if you just want to trigger Lambda Two based on a successful event from Lambda One.

## Conclusion

This project provides a demonstration for automating IAM key rotation using Lambda functions and AWS Secrets Manager. You can extend it by scheduling these Lambda functions using Amazon CloudWatch Events to periodically rotate IAM keys for your users.

### Notes for Students

1. **Objective**: This exercise aims to familiarize you with Lambda, IAM, and Secrets Manager services in AWS. You will:

   - Set up Lambda functions.
   - Automate IAM key management.
   - Use Secrets Manager for storing and retrieving IAM user credentials.

2. **Expected Outcome**: After following the steps, you should be able to invoke the Lambda functions to rotate IAM keys and delete inactive ones. You can also monitor logs in CloudWatch to verify that the key rotation was successful.

Let me know if you need further clarification or adjustments to the README file!
