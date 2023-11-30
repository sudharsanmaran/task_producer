import os
import asyncio
import aio_pika
from celery_app import update_database
from dotenv import load_dotenv

load_dotenv()

rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
queue_name = "image_response"


async def on_response(message: aio_pika.IncomingMessage):
    async with message.process():
        update_database.delay(message.body.decode())
        print(" [x] Received %r" % message.body)


async def main(loop):
    connection = await aio_pika.connect_robust(f"amqp://{rabbitmq_host}", loop=loop)

    async with connection:
        # Creating channel
        channel = await connection.channel()

        # Declaring queue
        queue = await channel.declare_queue(queue_name, durable=True)

        # Start consuming messages
        await queue.consume(on_response)


loop = asyncio.get_event_loop()
loop.create_task(main(loop))

# we enter a never-ending loop that waits for data and
# runs callbacks whenever necessary.
print(" [*] Waiting for messages. To exit press CTRL+C")
loop.run_forever()
