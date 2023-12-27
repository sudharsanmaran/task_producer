import os
import pika
from celery_app import update_database
from dotenv import load_dotenv

load_dotenv()

rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
queue_name = "image_response"

parameters = pika.URLParameters("amqp://guest:guest@rabbitmq:5672/")

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

channel.queue_declare(queue=queue_name, durable=True)


def on_response(ch, method, properties, body):
    update_database.delay(body.decode())
    print(" [x, y] Received %r" % body, "asdvdvdv", body.decode())
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=queue_name, on_message_callback=on_response)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
