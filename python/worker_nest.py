import time
import datetime
import io
import ezdxf
from typing import List
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, nestDxfBucket, nestSvgBucket
from nest import NestPolygone, NestRequest, NestRequest, NestResult, nest
from svg_generator import create_svg_from_doc
from polygone import DxfPolygon, process 
import traceback

collection = db["nesting_jobs"]
users_collection = db["users"]

def doJob(nesting_job):
    slug = nesting_job.get("slug")
    files = nesting_job.get("files")
    params = nesting_job.get("params")
    width = params.get("width")
    height = params.get("height")
    tolerance = params.get("tolerance")
    space = params.get("space")

    start_at = datetime.datetime.now()
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"startAt": start_at}}
    )

    nest_polygones = []
    for file in files:
        fileSlug: str = file.get("slug")
        fileCount: int = file.get("count")

        binary_stream = userDxfBucket.open_download_stream_by_name(fileSlug)
        dxf_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")
        dxf_polygones :List[DxfPolygon] = process(dxf_stream, tolerance)

        for group in dxf_polygones:
            nest_polygones.append(NestPolygone(group, fileCount))

    result: NestResult = nest(NestRequest(
        nest_polygones, width, height, space, tolerance
    ))

    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"usage": result.usage, "requested": result.requestCount,
                  "placed": result.placedCount}}
    )

    if (result.placedCount != result.requestCount):
        raise Exception("Not all items could be placed in the nesting job")

    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    for entity in result.dxf_entities:
        msp.add_entity(entity)

    text_stream = io.StringIO()
    doc.write(text_stream)
    dxf_text = text_stream.getvalue()
    text_stream.close()

    dxf_bytes = dxf_text.encode('utf-8')

    dxf_file_name = f"{slug}.dxf"
    nestDxfBucket.upload_from_stream(dxf_file_name, dxf_bytes)

    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"dxf_file": dxf_file_name}}
    )

    svg_content = create_svg_from_doc(doc)

    svg_file_name = f"{slug}.svg"
    nestSvgBucket.upload_from_stream(
        svg_file_name,
        io.BytesIO(svg_content.encode("utf-8"))
    )
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"svg_file": svg_file_name}}
    )

    finishAt = datetime.datetime.now()
    time_taken = finishAt - start_at

    minutes_taken = int(time_taken.total_seconds() / 60)
    
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {
            "$set": {
                "status": "done", 
                "finishedAt": finishAt, 
                "timeTaken": minutes_taken
            }
        }
    )
    user_id = nesting_job.get("ownerId")
    users_collection.update_one(
        {"id": user_id},
        {
            "$inc": {
                "nestingJobs": 1,
                "nestingTimeInMinute": minutes_taken
            }
        }
    )


# Run the worker
print("Worker nestincg started at ", datetime.datetime.now())


while True:
    print("Worker nesitng try to find a pending job")

    nesting_job = collection.find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing"}},
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
        print(traceback.format_exc())
        collection.update_one(
            {"_id": nesting_job["_id"]},
            {"$set": {"status": "error", "error": str(e)}}
        )
