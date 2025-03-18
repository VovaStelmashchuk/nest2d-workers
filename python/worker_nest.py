import time
import datetime
import io
from pymongo import ReturnDocument
from mongo import db, userDxfBucket
from dxf_utils import get_entity_primitives
from groupy import group_dxf_entities_into_polygons
from nest import NestPolygone, NestRequest, NestRequest, NestResult, nest


def doJob(nesting_job):
    files = nesting_job.get("files")
    params = nesting_job.get("params")
    width = params.get("width")
    height = params.get("height")
    tolerance = params.get("tolerance")
    space = params.get("space")

    nest_polygones = []
    for file in files:
        fileSlug: str = file.get("slug")
        fileCount: int = file.get("count")

        binary_stream = userDxfBucket.open_download_stream_by_name(fileSlug)
        dxf_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")
        dxf_entities = get_entity_primitives(dxf_stream)
        polygon_groups = group_dxf_entities_into_polygons(
            dxf_entities, tolerance)

        for group in polygon_groups:
            nest_polygones.append(NestPolygone(group, fileCount))

    result: NestResult = nest(NestRequest(
        nest_polygones, width, height, space
    ))


# Run the worker
print("Worker nestincg started at ", datetime.datetime.now())

collection = db["nesting_jobs"]

while True:
    print("Worker nesitng try to find a pending job")

    nesting_job = collection.find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "pending"}},
        return_document=ReturnDocument.AFTER
    )

    if nesting_job is None:
        time.sleep(5)
        continue
    try:
        print("Worker nesting job found", nesting_job.get(
            "slug"), "at", datetime.datetime.now())
        doJob(nesting_job)
    except Exception as e:
        print("Error: ", e)
        collection.update_one(
            {"_id": nesting_job["_id"]},
            {"$set": {"status": "error", "error": str(e)}}
        )
