import gridfs
from pymongo import MongoClient
import os
import json

def create_mongo_client():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("Error: 'mongoUri' key not found in the secret file.")
        exit(1)

    return MongoClient(mongo_uri)


client = create_mongo_client()
db = client.get_default_database()

userDxfBucket = gridfs.GridFSBucket(db, bucket_name="userDxf")
userSvgBucket = gridfs.GridFSBucket(db, bucket_name="userSvg")

nestDxfBucket = gridfs.GridFSBucket(db, bucket_name="nestDxf")
nestSvgBucket = gridfs.GridFSBucket(db, bucket_name="nestSvg")

tmpBucket = gridfs.GridFSBucket(db, bucket_name="tmp")