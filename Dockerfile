FROM python:3.7

RUN mkdir -p /app
WORKDIR /app
COPY . .
RUN pip3 install -r requirements.txt
RUN python3 setup.py install

CMD awsc