FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
  python3-pip \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY nbp_exchange_rate.py nbp_exchange_rate.py
COPY resources/ resources/

ENTRYPOINT ["python3", "nbp_exchange_rate.py"]
