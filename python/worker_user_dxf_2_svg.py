import io
from svg_generator import create_svg
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, userSvgBucket
import time
import datetime

print("Worker dxf to svg started at ", datetime.datetime.now())

collection = db["projects"]

while True:
    print("Worker dxf to svg try to find a pending job")
    doc = collection.find_one_and_update(
        {"svgGeneratorStatus": "pending"},
        {"$set": {"svgGeneratorStatus": "processing"}},
        return_document=ReturnDocument.AFTER
    )

    if doc is None:
        time.sleep(5)
        continue

    try:
        dxfArray = doc["dxf"]

        for dxf in dxfArray:
            fileSlug = dxf["slug"]
            processingStatus = dxf.get("processingStatus", "default")

            print("Processing dxf to svg for file: ", fileSlug, dxf)

            if processingStatus == "done":
                continue

            collection.update_one(
                {"_id": doc["_id"], "dxf.slug": fileSlug},
                {"$set": {"dxf.$.processingStatus": "in-progress"}}
            )
            try:
                binary_stream = userDxfBucket.open_download_stream_by_name(
                    fileSlug)

                text_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")

                svg_content = create_svg(text_stream)

                userSvgBucket.upload_from_stream(
                    fileSlug, io.BytesIO(svg_content.encode("utf-8"))
                )
                collection.update_one(
                    {"_id": doc["_id"], "dxf.slug": fileSlug},
                    {"$set": {"dxf.$.svgExists": True, "dxf.$.processingStatus": "done"}}
                )
            except Exception as e:
                print("Error: ", e)
                collection.update_one(
                    {"_id": doc["_id"], "dxf.slug": fileSlug},
                    {"$set": {"dxf.$.processingStatus": "error",
                              "dxf.$.processingError": str(e)}}
                )

        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"svgGeneratorStatus": "done"}}
        )
    except Exception as e:
        print("Error: ", e)
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"svgGeneratorStatus": "error",
                      "svgGeneratorError": str(e)}}
        )
