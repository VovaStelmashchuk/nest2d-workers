The project is a worker for process the dxf files. Create for web application [Nest2d](https://nest2d.stelamashchuk.dev)

The project is under development. The project does not have a goal to be universal dxf parser or etc. The project is created for a specific task.

The project read the task from the MongoDB and process the DXF parsing, creating the polygons call other service for nesting and save the result to the MongoDB.

## How to run

Build docker image

```
docker build -t nest_app .
```

Run docker container for development, using bind to the current directory for make changes in the code

```
docker run -it -v "$(pwd):/app" -w /app nest_app bash
```
