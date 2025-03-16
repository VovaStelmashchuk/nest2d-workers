from groupy import DXFPolygonGroup
import requests
import math

import ezdxf
from ezdxf import transform


class NestPolygone:
    def __init__(self, polygone_group, count):
        self.polygone_group: DXFPolygonGroup = polygone_group
        self.count: int = count

    def __str__(self) -> str:
        return f"NestPolygone -> Count: {self.count}, PolygoneGroup: {self.polygone_group}"


class NestRequest:
    def __init__(self, files):
        self.items: list[NestPolygone] = files


class NestResult:
    def __init__(self, usage, requestCount, placedCount):
        self.usage = usage
        self.requestCount = requestCount
        self.placedCount = placedCount

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


def nest(nestRequest: NestRequest) -> NestResult:
    nestRequestObject = buildNestRequestObject(nestRequest)
    response = requests.post(
        "https://jaguar.stelmashchuk.dev/nest", json=nestRequestObject)
    body = response.json()
    items = body.get("Items")
    totalRequest = 0
    for i in range(len(items)):
        totalRequest += items[i].get("Demand")

    solution = body.get("Solution")
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
        buildResultDxf(nestRequest, transforms)

    return NestResult(usage, totalRequest, totalPlacedItems)


def buildResultDxf(nestRequest: NestRequest, transforms):
    # Create a new DXF document
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

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
            msp.add_entity(entity)

    doc.saveas("transformed_output.dxf")
    print("New DXF file created: transformed_output.dxf")


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
                                [1000, 0],
                                [1000, 1000],
                                [0, 1000]
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
            file.polygone_group, file.count)
        data.extend(fileItems)
    return data


def convertPolygoneGroupToJaguarRequest(grop: DXFPolygonGroup, count: int):
    items = []
    poly = grop.polygon
    if poly.is_empty:
        return []

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
