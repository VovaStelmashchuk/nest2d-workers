The project is a worker for process the dxf files. Creates for web application [Nest2d](https://nest2d.stelmashchuk.dev/)

## Attention

The project is under development.
The project does not have a goal to be universal dxf parser or etc because the project is created for a specific task.

## How to run

### Build docker image

One docker image for both workers, we just change the commend into docker stack file

```
docker build -t nest2d-workers:local .
```

Run docker container for development, using bind to the current directory for make changes in the code

```
docker run -it -v "$(pwd):/app" -w /app nest2d-workers:local bash
```

Setup environment variables (run in the container)

```
export SECRET_FILE=.secret.json
```

Sample of the secret file

```json
{
  "mongoUri": "mongodb://<user>:<pass>@<ip>:27017/<db>"
}
```

### Run local docker stack

Create a secret for docker stack

```
cat .secret.json | docker secret create nest2d-secret-dev -
```

```
docker stack deploy -c docker-stack.dev.yml stack-test
```

## Main idea how it works

Parse dxf file and create a list of the polygons. Each polygon is a list of points.
Than the data of polygones provides to jagua-rs library for creating a nest of the polygons, implement in rust.
We use bridge between python and rust by using pyo3 library. Strongly recomend to use docker for easy setup and run the project.

- `ezdxf` library is used for parsing dxf files
- `shapely` library is used for creating polygons
- `jagua-rs` library is used for creating a nest of polygons
