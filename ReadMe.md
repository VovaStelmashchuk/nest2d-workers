## I finally managed to merge all source code of [nest2d.stelmashchuk.dev](https://nest2d.stelmashchuk.dev) into one repository, so all future development will be [here](https://github.com/VovaStelmashchuk/nest2d)

The project is a worker for processing the DXF files. Creates for web application [Nest2d](https://nest2d.stelmashchuk.dev/)

## How to run

### Build Docker image

One Docker image for both workers, we just change the command in the Docker stack file

```
docker build -t nest2d-workers:local .
```

Run Docker container for development, using bind to the current directory for make changes in the code

```
docker run -it -v "$(pwd):/app" -w /app nest2d-workers:local bash
```

Set up environment variables (run in the container)

```
export MONGO_URI=mongodb://user:password@host:port/db_name?...
```

### Run local Docker stack

```
docker stack deploy -c docker-stack.dev.yml stack-test
```

## The main idea How it works

Parse dxf file and create a list of the polygons. Each polygon is a list of points.
Than the data of polygones provides to jagua-rs library for creating a nest of the polygons, implement in rust.
We use bridge between python and rust by using pyo3 library. Strongly recomend to use docker for easy setup and run the project.

- `ezdxf` library is used for parsing dxf files
- `shapely` library is used for creating polygons
- `jagua-rs` library is used for creating a nest of polygons
