docker network create gps_app_net

docker run  --hostname teltonika --name teltonika --network gps_app_net --env-file envs.txt -p 8001:8001 teltonika-server

docker run --hostname influx --name influxdb --network gps_app_net -p 8086:8086 -v  C:\influxdb:/root/.influxdbv2 quay.io/influxdb/influxdb:v2.0.3