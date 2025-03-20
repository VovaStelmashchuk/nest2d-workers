import time
import datetime
import io
import ezdxf
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, nestDxfBucket
from dxf_utils import get_entity_primitives
from groupy import group_dxf_entities_into_polygons
from nest import NestPolygone, NestRequest, NestRequest, NestResult, nest
from svg_generator import create_svg_from_entities

collection = db["nesting_jobs"]


def doJob(nesting_job):
    slug = nesting_job.get("slug")
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

    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"usage": result.usage, "requested": result.requestCount,
                  "placed": result.placedCount}}
    )

    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    for entity in result.dxf_entities:
        msp.add_entity(entity)

    text_stream = io.StringIO()
    doc.write(text_stream)
    dxf_text = text_stream.getvalue()
    text_stream.close()

    dxf_bytes = dxf_text.encode('utf-8')

    file_name = f"nesting_{slug}.dxf"
    nestDxfBucket.upload_from_stream(file_name, dxf_bytes)

    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"dxf_file": file_name}}
    )

    svgContent = create_svg_from_entities(msp)
    print(svgContent)

    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"status": "done", "finishedAt": datetime.datetime.now()}}
    )


# Run the worker
print("Worker nestincg started at ", datetime.datetime.now())


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
