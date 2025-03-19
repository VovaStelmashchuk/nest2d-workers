import gridfs
from pymongo import MongoClient
import os
import json


def load_secret_file():
    secret_file_path = os.environ.get("SECRET_FILE")
    if not secret_file_path:
        print("Error: SECRET_FILE environment variable is not set.")
        exit(1)

    try:
        with open(secret_file_path, "r") as file:
            secret_data = json.load(file)
        return secret_data
    except Exception as e:
        print(f"Error reading secret file: {e}")
        exit(1)


def create_mongo_client():
    secret_data = load_secret_file()
    mongo_uri = secret_data.get('mongoUri')
    if not mongo_uri:
        print("Error: 'mongoUri' key not found in the secret file.")
        exit(1)

    return MongoClient(mongo_uri)


client = create_mongo_client()
db = client.get_default_database()

userDxfBucket = gridfs.GridFSBucket(db, bucket_name="userDxf")
userSvgBucket = gridfs.GridFSBucket(db, bucket_name="userSvg")

nestDxfBucket = gridfs.GridFSBucket(db, bucket_name="nestDxf")
