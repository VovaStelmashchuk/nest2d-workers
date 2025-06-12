import time
import datetime
import io
import ezdxf
from typing import List
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, nestDxfBucket, nestSvgBucket
from nest import NestPolygone, NestRequest, NestRequest, NestResult, nest, NestResultLayout
from svg_generator import create_svg_from_doc
from polygone import DxfPolygon 
import traceback
from polygone import find_closed_polygons
from utils.logger import setup_json_logger

collection = db["nesting_jobs"]
users_collection = db["users"]
logger = setup_json_logger("worker_nest")

def buildLayout(nest_layout: NestResultLayout, dxf_file_name: str, svg_file_name: str, ownerId: str):
    doc = ezdxf.new(dxfversion='R2010', units=4)
    msp = doc.modelspace()
    
    # Get all unique colors from entities
    colors = set()
    for entity in nest_layout.dxf_entities:
        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'color'):
            colors.add(entity.dxf.color)
    
    # Create layers for each color and add them to the document
    for color in colors:
        layer_name = f"Color_{color}"
        if layer_name not in doc.layers:
            layer = doc.layers.add(name=layer_name)
            layer.color = color
    
    # Attach entities to their corresponding color layers
    for entity in nest_layout.dxf_entities:
        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'color'):
            color = entity.dxf.color
            layer_name = f"Color_{color}"
            entity.dxf.layer = layer_name

    for entity in nest_layout.dxf_entities:
        msp.add_entity(entity)

    text_stream = io.StringIO()
    doc.write(text_stream)
    dxf_text = text_stream.getvalue()
    text_stream.close()

    dxf_bytes = dxf_text.encode('utf-8')

    nestDxfBucket.upload_from_stream(filename=dxf_file_name, source=dxf_bytes, metadata={"ownerId": ownerId})

    svg_content = create_svg_from_doc(doc)

    nestSvgBucket.upload_from_stream(
        filename=svg_file_name,
        source=io.BytesIO(svg_content.encode("utf-8")),
        metadata={"ownerId": ownerId}
    )

from typing import Tuple

def doJob(nesting_job):
    slug = nesting_job.get("slug")
    files = nesting_job.get("files")
    params = nesting_job.get("params")
    width = params.get("width")
    height = params.get("height")
    tolerance = params.get("tolerance")
    space = params.get("space")
    sheet_count = params.get("sheetCount")

    start_at = datetime.datetime.now()
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"startAt": start_at}}
    )

    nest_polygones = []
    for file in files:
        fileSlug: str = file.get("slug")
        fileCount: int = file.get("count")

        grid_out = userDxfBucket.open_download_stream_by_name(fileSlug)
        dxf_polygones: List[DxfPolygon]
        dxf_polygones = find_closed_polygons(grid_out, tolerance)

        for group in dxf_polygones:
            nest_polygones.append(NestPolygone(group, fileCount))

    result: NestResult = nest(NestRequest(
        nest_polygones, width, height, space, tolerance, sheet_count
    ))
   
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": { "requested": result.requestCount, "placed": result.placedCount }}
    )

    if (result.placedCount != result.requestCount):
        raise Exception("Not all items could be placed in the nesting job")
    
    dxf_files = []
    svg_files = []
    for index, layout in enumerate(result.layouts):
        dxf_file_name = f"{slug}_part_{index + 1}.dxf"
        svg_file_name = f"{slug}_part_{index + 1}.svg"
        buildLayout(layout, dxf_file_name, svg_file_name, nesting_job.get("ownerId"))
        dxf_files.append(dxf_file_name)
        svg_files.append(svg_file_name)
        
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {"$set": {"dxf_files": dxf_files, "svg_files": svg_files, "layoutCount": len(result.layouts), "status": "done" }}
    )

    finishAt = datetime.datetime.now()
    time_taken = finishAt - start_at

    minutes_taken = int(time_taken.total_seconds() / 60)
    
    collection.update_one(
        {"_id": nesting_job["_id"]},
        {
            "$set": {
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
                "nestingTimeInMinute": minutes_taken,
                "balance": -(minutes_taken + 1)
            }
        }
    )


# Run the worker
logger.info("Worker nestincg started", extra={"event": "start", "time": str(datetime.datetime.now())})


while True:
    logger.info("Worker nesting try to find a pending job")

    nesting_job = collection.find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing"}},
        return_document=ReturnDocument.AFTER
    )

    if nesting_job is None:
        time.sleep(5)
        continue
    try:
        logger.info("Worker nesting job found", extra={"slug": nesting_job.get("slug"), "time": str(datetime.datetime.now())})
        doJob(nesting_job)
    except Exception as e:
        logger.error("Error in nesting job", extra={"error": str(e), "traceback": traceback.format_exc()})
        collection.update_one(
            {"_id": nesting_job["_id"]},
            {"$set": {"status": "error", "error": str(e)}}
        )
