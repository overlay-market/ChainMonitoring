# Chain Monitoring
Chain Monitoring using Python, Prometheus & Grafana

## Architecture
There are three services in this repository:
1. Chain Moniroting Python app - main application that handles querying the chain
2. Prometheus - open-source systems monitoring and alerting tool
3. Grafana - open-source data visualization tool

## Project Structure
to-do

## Prometheus Metrics
This is a running list of all the metrics being monitored in this project.
1. `ovl_token_minted` - Number of OVL tokens minted
   
### How to add new metrics
- to-do


## Local Development
You can choose from two options for local development: (1) Docker Setup or (2) Bare Python app. The docker setup is more recommended to understand how the whole architecture works.

### Docker Setup
We're leveraging docker and docker compose for this project. This makes it easy to run multiple services that are integral to the Chain Monitoring system. Follow the steps below on how to setup for local development.
1. Install docker on your local machine: https://docs.docker.com/engine/install/
2. Run docker compose. This command runs all services specified in docker-compose.yml
    ```
    docker-compose up
    ```
3. Check if the containers are running
   ```
   docker ps
   ```
   This command should return a list of running containers like so:
   ```
   CONTAINER ID   IMAGE              COMMAND                   CREATED         STATUS         PORTS                    NAMES
    c0271363ffd6   alpine:3.10        "/bin/sh -c '\n  apk …"   9 seconds ago   Up 8 seconds                            chainmonitoring-grafana-dashboards-1
    44598b06ec1c   prom/prometheus    "/bin/prometheus --c…"    9 seconds ago   Up 8 seconds   0.0.0.0:9091->9090/tcp   prometheus-svc-2
    13bfaded8fac   grafana/grafana    "/run.sh"                 9 seconds ago   Up 8 seconds   0.0.0.0:3000->3000/tcp   chainmonitoring-grafana-1
    2c45966746cf   chain-monitoring   "/bin/sh -c 'python …"    9 seconds ago   Up 8 seconds   0.0.0.0:81->8000/tcp     chain-monitoring
   ```
4. Once all containers are running, you should be able to access the following services in your browser:
   - Grafana - http://localhost:3000/
   - Prometheus - http://localhost:9091/
   - Chain Monitoring Python application - http://localhost:81/

#### When there are new python packages in your changes, make sure to add them to the requirements.txt file:
```
pip install <package_name>
pip freeze > requirements.txt
```

#### If there are code changes to the python application, re-build the docker container for the python application before running `docker-compose up`.
```
docker-compose build chain-monitoring
```


### Bare Python setup
This only runs the Python application. To emulate the complete monitoring functionality in your local machine, opt for the Docker setup instead.
1. Install requirements
   ```
   pip install -r requirements.txt
   ```
2. Run python app
   ```
   python query_mint_events.py
   ```

## Deployment
### Ubuntu Instance
- to-do