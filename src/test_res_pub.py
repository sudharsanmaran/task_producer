import json
import pika
import os

rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
response_queue = os.getenv("RESPONSE_QUEUE", "image_response")


def send_image_response_to_rabbitmq(obj: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbitmq_host)
    )
    channel = connection.channel()
    channel.queue_declare(queue=response_queue, durable=True)
    corr_id = obj["id"]
    channel.basic_publish(
        exchange="",
        routing_key=response_queue,
        body=json.dumps(obj).encode(),
        properties=pika.BasicProperties(
            reply_to="",
            correlation_id=corr_id,
        ),
    )
    if not connection.is_closed:
        connection.close()
    return


send_image_response_to_rabbitmq({
    "id": "0ec674af-2366-4c86-9f91-147bc633d443",
    "response": ['jhcbdbc', 'jcxvjdcbdjb'],
})
