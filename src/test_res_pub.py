import json
import pika
import os

rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
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
        body=json.dumps(obj),
        properties=pika.BasicProperties(
            reply_to="",
            correlation_id=corr_id,
        ),
    )
    if not connection.is_closed:
        connection.close()
    return


send_image_response_to_rabbitmq({
    "id": "26b7e94d-de42-4c23-9ba4-c65a7429e00f",
    "response": ['jhcbdbc', 'jcxvjdcbdjb'],
})
