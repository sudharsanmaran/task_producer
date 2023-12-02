FROM python:3.11.6

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copy the worker script into the container
COPY . /app

# Set environment variables for Azure and RabbitMQ
ENV OMP_NUM_THREADS=1

# Create a directory for the transformers cache
RUN mkdir -p /app/transformers_cache
ENV TRANSFORMERS_CACHE=/app/transformers_cache

# Set the command to run the worker script
CMD ["python", "/app/consumer.py"]
