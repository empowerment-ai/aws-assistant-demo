import json
from openai import OpenAI
from time import sleep
import os
import uuid
import boto3
from decimal import Decimal  # Import the Decimal class

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Init client
client = OpenAI(api_key=OPENAI_API_KEY) 
dynamodb = boto3.resource('dynamodb')

def book_reservation(name, phone_number, house_id, check_in_date, nights):

    total_cost = int(nights) * 100

    table = dynamodb.Table('reservations')

    # Generate a unique GUID
    reservation_id = str(uuid.uuid4())
    
    # Convert total_cost to Decimal
    total_cost_decimal = Decimal(str(total_cost))

    response = table.put_item(
       Item={
            'reservation_id': reservation_id,  # Use the GUID as the partition key
            'name': name,
            'phone_number': phone_number,
            'house_id': house_id,
            'check_in_date': check_in_date,
            'nights': nights,
            'total_cost': total_cost_decimal
        }
    )
    return f"Booked: ID {reservation_id} and total cost: {total_cost}"


def handle_action(run, thread_id):
    tools_to_call = run.required_action.submit_tool_outputs.tool_calls
    print(len(tools_to_call))
    print(tools_to_call)
    
    tools_output_array = []
    for each_tool in tools_to_call:
      tool_call_id = each_tool.id
      function_name = each_tool.function.name
      function_arg = each_tool.function.arguments
      print("Tool ID:" + tool_call_id)
      print("Function to Call:" + function_name )
      print("Parameters to use:" + function_arg)
    
      if (function_name == 'get_cost'):
        cost_data=json.loads(function_arg)
        house_id = cost_data.get('house_id')
        no_nights = cost_data.get('no_nights')
        output=int(no_nights) * 100
        tools_output_array.append({"tool_call_id": tool_call_id, "output": output})
      elif (function_name == 'book_reservation'):
        reservation_data=json.loads(function_arg)
        full_name = reservation_data.get('full_name')
        phone_number = reservation_data.get('phone')
        house_id = reservation_data.get('house_id')
        check_in_date = reservation_data.get('check_in_date')
        no_nights = reservation_data.get('no_nights')
        #total_cost = reservation_data.get('cost')
        #total_cost = 1000.00
        response = book_reservation(full_name, phone_number, house_id, check_in_date, no_nights)
        #print(full_name)
        output=f"Reservation Booked:{response}"
        tools_output_array.append({"tool_call_id": tool_call_id, "output": output})
        
    run = client.beta.threads.runs.submit_tool_outputs(
      thread_id = thread_id,
      run_id = run.id,
      tool_outputs=tools_output_array
    )

    print(tools_output_array)        


def lambda_handler(event, context):
    print('test lambda function called')
    print('event:', event)
    print('context:', context)
    thread_id = event.get('thread_id')
    run_id = event.get('run_id')

    print(f"Thread ID: {thread_id}, Run ID: {run_id}")
    
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                      run_id=run_id)
        print(f"Run status: {run_status.status}")
        if run_status.status == 'completed' or run_status.status == 'failed':
          break
      
        if run_status.status == 'requires_action':
          handle_action(run_status, thread_id)

        sleep(1)  # Wait for a second before checking again    
    
   
