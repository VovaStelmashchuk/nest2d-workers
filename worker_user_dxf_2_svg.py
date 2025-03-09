import io
from svg_generator import create_svg
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, userSvgBucket
import time
import datetime

print("Worker dxf to svg started at ", datetime.datetime.now())

collection = db["projects"]

while True:
    print("Worker dxf to svg is waiting for a task")

    doc = collection.find_one_and_update(
        {"svgGeneratorStatus": "pending"},
        {"$set": {"svgGeneratorStatus": "processing"}},
        return_document=ReturnDocument.AFTER
    )

    if doc is None:
        time.sleep(5)
        continue

    dxfArray = doc["dxf"]

    for dxf in dxfArray:
        fileSlug = dxf["slug"]
        binary_stream = userDxfBucket.open_download_stream_by_name(fileSlug)

        text_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")

        svg_content = create_svg(text_stream)

        userSvgBucket.upload_from_stream(
            fileSlug, io.BytesIO(svg_content.encode("utf-8"))
        )
        collection.update_one(
            {"_id": doc["_id"], "dxf.slug": fileSlug},
            {"$set": {"dxf.$.svgExists": True}}
        )
        print("Done")

    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"svgGeneratorStatus": "done"}}
    )
