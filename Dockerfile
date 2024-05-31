# Use the official Ubuntu 16.04 as the base image
FROM ubuntu:16.04

# Maintainer information
MAINTAINER Adam Djellouli <addjellouli1@gmail.com>

# Install dependencies
RUN apt-get update -y && \
    apt-get install -y python-pip python-dev

# Copy requirements.txt into the image
COPY ./requirements.txt /src/requirements.txt

# Set the working directory
WORKDIR /src

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the entire current directory into the image
COPY . /src

# Set the entry point to Python
ENTRYPOINT ["python"]

# Default command to run the application
CMD ["app.py"]
