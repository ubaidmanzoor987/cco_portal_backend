# Use an official Python runtime as a parent image
FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget gnupg2 nano

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# fixing windows line endings problems.
COPY ./docker/entrypoint.sh entrypoint.sh.raw
RUN sed 's/\r$//' entrypoint.sh.raw > entrypoint.sh \
    && rm entrypoint.sh.raw

# Update pip
RUN python -m pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]

# Run the Django server
CMD ["serve", "--bind", "0.0.0.0:8000"]
