import io
from svg_generator import create_svg_from_doc
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, userSvgBucket
import time
import datetime
from dxf_utils import read_dxf
import traceback
from utils.logger import setup_json_logger

logger = setup_json_logger("worker_user_dxf_2_svg")

logger.info("Worker dxf to svg started", extra={"event": "start", "time": str(datetime.datetime.now())})

collection = db["projects"]


def doJobProject(project_doc):
    logger.info("Processing project", extra={"project_id": str(project_doc["_id"])})
    _id = project_doc["_id"]
    dxfArray = project_doc["dxf"]

    for dxf in dxfArray:
        fileSlug = dxf["slug"]
        processingStatus = dxf.get("processingStatus", "default")

        logger.info("Processing dxf to svg for file", extra={"fileSlug": fileSlug, "dxf": dxf})

        if processingStatus == "done":
            continue

        collection.update_one(
            {"_id": _id, "dxf.slug": fileSlug},
            {"$set": {"dxf.$.processingStatus": "in-progress"}}
        )
        try:
            dxf_doc = read_dxf(userDxfBucket.open_download_stream_by_name(
                fileSlug))

            svg_content = create_svg_from_doc(dxf_doc)

            svg_file_name = f"{fileSlug}.svg"
            userSvgBucket.upload_from_stream(
                svg_file_name,
                io.BytesIO(svg_content.encode("utf-8"))
            )
            collection.update_one(
                {"_id": _id, "dxf.slug": fileSlug},
                {"$set":
                 {
                     "dxf.$.svgExists": True,
                     "dxf.$.processingStatus": "done",
                     "dxf.$.svgFile": svg_file_name
                 }
                 }
            )
        except Exception as e:
            logger.error("Error in dxf to svg", extra={"error": str(e), "traceback": traceback.format_exc()})
            collection.update_one(
                {"_id": _id, "dxf.slug": fileSlug},
                {"$set": {"dxf.$.processingStatus": "error",
                          "dxf.$.processingError": str(e)}}
            )

    collection.update_one(
        {"_id": _id},
        {"$set": {"svgGeneratorStatus": "done"}}
    )


# Run the worker loop
while True:
    logger.info("Worker dxf to svg try to find a pending job")
    doc = collection.find_one_and_update(
        {"svgGeneratorStatus": "pending"},
        {"$set": {"svgGeneratorStatus": "processing"}},
        return_document=ReturnDocument.AFTER
    )

    if doc is None:
        time.sleep(5)
        continue

    try:
        doJobProject(doc)
    except Exception as e:
        logger.error("Error in project processing", extra={"error": str(e), "traceback": traceback.format_exc()})
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"svgGeneratorStatus": "error",
                      "svgGeneratorError": str(e)}}
        )
