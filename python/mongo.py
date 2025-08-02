import gridfs
from pymongo import MongoClient
import os

from utils.logger import setup_json_logger

logger = setup_json_logger("mongo")

def create_mongo_client():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        logger.error("Error: 'mongoUri' key not found in environment variables.")
        exit(1)

    return MongoClient(mongo_uri)


client = create_mongo_client()
db = client.get_default_database()

userDxfBucket = gridfs.GridFSBucket(db, bucket_name="validDxf")

nestDxfBucket = gridfs.GridFSBucket(db, bucket_name="nestDxf")
nestSvgBucket = gridfs.GridFSBucket(db, bucket_name="nestSvg")
