FROM ubuntu:latest

RUN apt-get update; DEBIAN_FRONTEND=noninteractive apt-get install -qq -y python3 python3-pip python python-pip python-dev git libssl-dev libffi-dev build-essential vim curl dnsutils php iputils-ping wget

# add missing packages :-)
RUN pip3 install flask flask_sqlalchemy pwntools requests
RUN pip install pwntools requests

COPY files /app

WORKDIR /app

#for pwntools-terminal fix
RUN PWNLIB_NOTERM=1 pwn update
ENV PWNLIB_NOTERM=true

RUN cd /app;
RUN chmod +x /app/start.sh
ENTRYPOINT /app/start.sh
