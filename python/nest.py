from groupy import DXFPolygonGroup
from ezdxf import transform
from ezdxf.entities import DXFGraphic
import json
import nest_rust


class NestPolygone:
    def __init__(self, polygone_group, count):
        self.polygone_group: DXFPolygonGroup = polygone_group
        self.count: int = count

    def __str__(self) -> str:
        return f"NestPolygone -> Count: {self.count}, PolygoneGroup: {self.polygone_group}"


class NestRequest:
    def __init__(self, files: list[NestPolygone], width: float, height: float, spacing: float):
        self.items: list[NestPolygone] = files
        self.width = width
        self.height = height
        self.spacing = spacing


class NestResult:
    def __init__(self, usage: float, requestCount: int, placedCount: int, dxf_entities: list[DXFGraphic] = []):
        self.usage = usage
        self.requestCount = requestCount
        self.placedCount = placedCount
        self.dxf_entities = dxf_entities

    def __str__(self) -> str:
        return f"NestResult -> Usage: {self.usage}, RequestCount: {self.requestCount}, PlacedCount: {self.placedCount}"


class Transform:
    def __init__(self, fileIndex, x, y, angle):
        self.fileIndex = fileIndex
        self.x = x
        self.y = y
        self.angle = angle

    def __str__(self) -> str:
        return f"Transform -> FileIndex: {self.fileIndex}, X: {self.x}, Y: {self.y}, Angle: {self.angle}"


def nest(nest_request: NestRequest) -> NestResult:
    items: list = nest_request.items
    totalRequest = 0
    for i in range(len(items)):
        totalRequest += items[i].count

    nest_request_object = buildNestRequestObject(nest_request)
    nest_request_json = json.dumps(nest_request_object)

    try:
        result_json = nest_rust.run_nest(nest_request_json)
    except Exception as e:
        print("Error executing Rust code:", e)
        raise e

    try:
        result = json.loads(result_json)
        solution = result.get("Solution")
    except json.JSONDecodeError as e:
        print("Error decoding JSON result:", e)
        raise e

    firstLayout = solution.get("Layouts")[0]
    usage = firstLayout.get("Statistics").get("Usage")
    placedItems = firstLayout.get("PlacedItems")
    totalPlacedItems = len(placedItems)

    transforms = []
    for item in placedItems:
        index = item.get("Index")
        transformation = item.get("Transformation")
        rotation = transformation.get("Rotation")
        translation = transformation.get("Translation")
        x = translation[0]
        y = translation[1]
        transforms.append(Transform(index, x, y, rotation))

    if totalPlacedItems == totalRequest:
        dxf_entities = buildResultDxf(nest_request, transforms)

    return NestResult(usage, totalRequest, totalPlacedItems, dxf_entities)


def buildResultDxf(nestRequest: NestRequest, transforms) -> list[DXFGraphic]:
    dxf_entities = []
    # Process each transformation
    for innerTransform in transforms:
        # Get the corresponding NestPolygone (or DXF entity group)
        nest_poly = nestRequest.items[innerTransform.fileIndex]
        entities = []
        for i in range(len(nest_poly.polygone_group.dxf_entities)):
            # Add all entities to the List
            entities.append(
                nest_poly.polygone_group.dxf_entities[i].entity.copy())

        rotationMatrix = transform.Matrix44.z_rotate(innerTransform.angle)
        translationMatrix = transform.Matrix44.translate(
            innerTransform.x, innerTransform.y, 0)

        transform.inplace(entities, m=rotationMatrix * translationMatrix)
        for entity in entities:
            dxf_entities.append(entity)

    return dxf_entities


def buildNestRequestObject(nestRequest: NestRequest):
    items = buildRequestItems(nestRequest)

    return {
        "uuid": "1234",
        "input": {
            "Name": "Test",
            "Items": items,
            "Objects": [
                {
                    "Cost": 1,
                    "Stock": 1,
                    "Zones": [],
                    "Shape": {
                        "Type": "Polygon",
                        "Data":  {
                            "Outer": [
                                [0, 0],
                                [nestRequest.width, 0],
                                [nestRequest.width, nestRequest.height],
                                [0, nestRequest.height]
                            ],
                            "Inner": []
                        }
                    }

                }
            ]
        },
        "config": {
            "cde_config": {
                "quadtree_depth": 5,
                "hpg_n_cells": 2000,
                "item_surrogate_config": {
                    "pole_coverage_goal": 0.9,
                    "max_poles": 10,
                    "n_ff_poles": 2,
                    "n_ff_piers": 0
                }
            },
            "poly_simpl_tolerance": 0.001,
            "prng_seed": 0,
            "n_samples": 500000,
            "ls_frac": 0.2
        }
    }


def buildRequestItems(nestRequest: NestRequest):
    data = []
    for file in nestRequest.items:
        fileItems = convertPolygoneGroupToJaguarRequest(
            file.polygone_group, file.count, nestRequest.spacing)
        data.extend(fileItems)
    return data


def convertPolygoneGroupToJaguarRequest(grop: DXFPolygonGroup, count: int, spacing: float) -> list[dict]:
    items = []
    poly = grop.polygon
    if poly.is_empty:
        return []

    poly = poly.buffer(spacing)

    xs, ys = poly.exterior.xy
    points: list[list[float]] = []
    for i in range(len(xs)):
        points.append([xs[i], ys[i]])

    items.append({
        "Demand": count,
        "AllowedOrientations": [0, 90, 180, 270],
        "Shape": {
            "Type": "SimplePolygon",
            "Data": points
        }
    })

    return items
