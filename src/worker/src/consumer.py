import os
import pika
from ai_celery_app import handle_img_gen_request
from dotenv import load_dotenv

load_dotenv()

rabbitmq_host = os.getenv("RABBITMQ_HOST")
queue_name = os.getenv("REQUEST_QUEUE")

parameters = pika.URLParameters(os.getenv("RABBITMQ_BROKER_URL"))

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue=queue_name, durable=True)


def on_response(ch, method, properties, body):
    handle_img_gen_request.delay(body.decode())
    print(" [x] Received %r" % body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=2)
channel.basic_consume(queue=queue_name, on_message_callback=on_response)

print(f" [*] Waiting for messages in {queue_name} queue.")
channel.start_consuming()
