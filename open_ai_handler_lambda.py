import json
from openai import OpenAI
import os
import boto3

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
ASSISTANT_ID = os.environ['ASSISTANT_ID']
LAMBDA_HANDLER_ARN = os.environ["LAMBDA_HANDLER_ARN"]


# Init client
client = OpenAI(api_key=OPENAI_API_KEY) 


def start_conversation():
  print("Starting a new conversation...")  # Debugging line
  thread = client.beta.threads.create()
  print(f"New thread created with ID: {thread.id}")  # Debugging line
  return thread.id


def get_message(assistant_id, thread_id, run_id):
  run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run_id)
  print(f"Run status: {run_status.status}")
  
  if run_status.status == 'completed':
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = messages.data[0].content[0].text.value
    return {
      'statusCode': 200,
          'body': json.dumps({'run_status': run_status.status, 'iaMessage': response})
    }
  else:
    return {
      'statusCode': 200,
          'body': json.dumps({'run_status': run_status.status, 'iaMessage': ""})
    }

def startChat(assistant_id, thread_id, user_input):

  if not thread_id:
    print("Error: Missing thread_id")  # Debugging line
    return "error: Missing thread_id"

  print(f"Received message: '{user_input}' for thread ID: '{thread_id}'")  # Debugging line

  # Add the user's message to the thread
  client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=user_input)
  # Run the Assistant
  run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id)
  print(f"run ID: {run.id}")
  invoke_handler(thread_id, run.id)
  return run.id
    


def invoke_handler(thread_id, run_id):
  # Create a Lambda client using Boto3
    client = boto3.client('lambda')

    # Data to send, convert your data to JSON
    payload = {
        'thread_id': thread_id,
        'run_id': run_id
    }

    # Invoke another Lambda function asynchronously
    response = client.invoke(
        FunctionName=LAMBDA_HANDLER_ARN,
        InvocationType='Event',  # Asynchronous invocation
        Payload=json.dumps(payload)
    )


def lambda_handler(event, context):
    
    
    # # Check the HTTP method
    http_method = event.get('httpMethod')

    if http_method == 'GET':
        # Handling GET method for 'start'
        if event.get('resource') == '/start':
            # Generate or retrieve a threadID here
            thread_id = start_conversation()
            return {
                'statusCode': 200,
                'body': json.dumps({'thread_id': thread_id})
            }
        

    elif http_method == 'POST':
        # Handling POST method for 'chat'
        if event.get('resource') == '/chat':
            # Extracting data from the request body
            body = json.loads(event.get('body', '{}'))
            thread_id = body.get('thread_id')
            user_input = body.get('user_input')

            # Implement your logic here to process the message and generate iaMessage
            run_id = startChat(ASSISTANT_ID, thread_id, user_input)

            return {
                'statusCode': 200,
                'body': json.dumps({'thread_id': thread_id, 'run_id': run_id})
            }
        elif event.get('resource') == '/message':
            body = json.loads(event.get('body', '{}'))
            thread_id = body.get('thread_id')
            run_id = body.get('run_id')
            return get_message(ASSISTANT_ID, thread_id, run_id)  

    # Default response for unsupported methods or routes
    return {
        'statusCode': 400,
        'body': json.dumps('Unsupported method or route')
    }
