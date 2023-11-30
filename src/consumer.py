import os
import pika
from celery_app import update_database
from dotenv import load_dotenv

load_dotenv()

# Establish a connection
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="rabbitmq",
        heartbeat=600,
    )
)
channel = connection.channel()

queue_name = 'image_response'
# Declare the same durable queue
print(queue_name, "queue name &&&&&&&&&&&&&&&&")
channel.queue_declare(queue=queue_name, durable=True)


# Define a callback function to process messages
def callback(ch, method, properties, body):
    update_database.delay(body)
    print(" [x] Received %r" % body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


# Start consuming messages
channel.basic_consume(queue=queue_name, on_message_callback=callback)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
