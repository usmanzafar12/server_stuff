FROM python:3.7-alpine
WORKDIR /code
ENV INFLUX_TOKEN=""
ENV INFLUXDB_CONNECTION="infludb:8086"
ENV PORT=8001
RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "simple-server.py"]