FROM python:3.8

RUN mkdir -p /app
WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
RUN python3 setup.py install

CMD awsc