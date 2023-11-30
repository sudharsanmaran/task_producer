import json
import pika
import os

rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
request_queue = os.getenv("REQUEST_QUEUE", "image_request")


def send_to_rabbitmq(obj: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=rabbitmq_host,
            heartbeat=900,
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=request_queue, durable=True)
    corr_id = obj["id"]
    channel.basic_publish(
        exchange="",
        routing_key=request_queue,
        body=json.dumps(obj),
        properties=pika.BasicProperties(
            reply_to="",
            correlation_id=corr_id,
            delivery_mode=2,
        ),
    )
    if not connection.is_closed:
        connection.close()
    return
