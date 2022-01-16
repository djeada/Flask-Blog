FROM ubuntu:16.04

MAINTANER Adam Djellouli "addjellouli1@gmail.com"

RUN apt-get update -y && \
    apt-get install -y python-pip python-dev

COPY ./requirements.txt src/requirements.txt

WORKDIR /src

RUN pip install -r requirements.txt

COPY . /src

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]
