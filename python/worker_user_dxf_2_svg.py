import io
from svg_generator import create_svg_from_entities
from pymongo import ReturnDocument
from mongo import db, userDxfBucket, userSvgBucket
import time
import datetime
import ezdxf

print("Worker dxf to svg started at ", datetime.datetime.now())

collection = db["projects"]


def doJobProject(project_doc):
    _id = project_doc["_id"]
    dxfArray = project_doc["dxf"]

    for dxf in dxfArray:
        fileSlug = dxf["slug"]
        processingStatus = dxf.get("processingStatus", "default")

        print("Processing dxf to svg for file: ", fileSlug, dxf)

        if processingStatus == "done":
            continue

        collection.update_one(
            {"_id": _id, "dxf.slug": fileSlug},
            {"$set": {"dxf.$.processingStatus": "in-progress"}}
        )
        try:
            binary_stream = userDxfBucket.open_download_stream_by_name(
                fileSlug)

            dxf_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")
            project_doc = ezdxf.read(dxf_stream)
            msp = project_doc.modelspace()

            svg_content = create_svg_from_entities(msp)

            svg_file_name = f"{fileSlug}.svg"
            userSvgBucket.upload_from_stream(
                svg_file_name,
                io.BytesIO(svg_content.encode("utf-8"))
            )
            collection.update_one(
                {"_id": _id, "dxf.slug": fileSlug},
                {"$set": {"dxf.$.svgExists": True, "dxf.$.processingStatus": "done"}}
            )
        except Exception as e:
            print("Error: ", e)
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
        doJobProject(doc)
    except Exception as e:
        print("Error: ", e)
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"svgGeneratorStatus": "error",
                      "svgGeneratorError": str(e)}}
        )
