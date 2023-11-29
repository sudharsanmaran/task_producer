import os
import pika
from celery_app import update_database

# Establish a connection
connection = pika.BlockingConnection(
    pika.ConnectionParameters(os.getenv("RABBITMQ_HOST"))
)
channel = connection.channel()

queue_name = os.getenv("RESPOSE_QUEUE_NAME")
# Declare the same durable queue
channel.queue_declare(queue=queue_name, durable=True)


# Define a callback function to process messages
def callback(ch, method, properties, body):
    update_database.delay(body)


# Start consuming messages
channel.basic_consume(queue=queue_name, on_message_callback=callback)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
