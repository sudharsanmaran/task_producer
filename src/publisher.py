import json
import os
import pika
import requests

rabbitmq_host = "rabbitmq"
request_queue = os.getenv("REQUEST_QUEUE", "image_request")


def send_to_rabbitmq(obj: dict):

    # before pushing into the queue, please check whether the prompt doesn't
    # violate Rules of Microsoft Azure Open AI content Filter API
    # verdict = analyze_content(obj['content'])

    # if verdict != 'accept':
    #     return "The content violates the rules, so the message will not be sent to RabbitMQ."
    
    connection = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host)
        )

        channel = connection.channel()

        message_body = json.dumps(obj)
        properties = pika.BasicProperties(
            delivery_mode=2,
            correlation_id=obj["id"],
        )  # Set reply_to to response queue name

        channel.basic_publish(
            exchange="",
            routing_key=request_queue,
            body=message_body,
            properties=properties,
        )
    finally:
        if connection and connection.is_open:
            connection.close()



def analyze_content(content):
    """
    Analyzes content using the ContentFilter API.

    Args:
    content: The string content to be analyzed.

    Returns:
    A dictionary containing the API response data or None if the request fails.
    """

    # Define the URL base
    url_base = "https://contentfilter.azurewebsites.net/analyze-content"

    # Build the final URL with the provided content
    url = f"{url_base}?content={content}"

    # Set optional headers if needed (adjust based on the API documentation)
    headers = {
        "Content-Type": "application/json",
    }

    # Send the POST request
    try:
        response = requests.post(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

    # Check for successful response code (200)
    if response.status_code == 200:
    # Process the response data
        data = response.json()
        verdict = data['vedict']
        return verdict
    else:
        print(f"Error: {response.status_code} - {response.reason}")
        return None