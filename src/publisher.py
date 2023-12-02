import json
import os
import pika

rabbitmq_host = "rabbitmq"
request_queue = os.getenv("REQUEST_QUEUE", "image_request")


def send_to_rabbitmq(obj: dict):
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
