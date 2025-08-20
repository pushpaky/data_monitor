
from fastapi import FastAPI
from pymongo import MongoClient
from bson import Binary, UuidRepresentation
from datetime import datetime
import uuid
from .config import MONGO_URI, DB_NAME, COLLECTION_NAME

app = FastAPI()


def serialize_mongo_doc(doc):
    # Convert Binary UUID and datetime to string
    if "deviceid" in doc:
        try:
            doc["deviceid"] = str(doc["deviceid"].as_uuid())
        except Exception:
            doc["deviceid"] = str(doc["deviceid"])

    if "devicetime" in doc:
        doc["devicetime"] = doc["devicetime"].isoformat()

    return doc


def get_data_from_mongodb(device_id: str, start_date: str, end_date: str):
    try:
        client = MongoClient(MONGO_URI, uuidRepresentation="standard")
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        device_id_uuid = uuid.UUID(device_id)
        device_id_binary = Binary.from_uuid(device_id_uuid, UuidRepresentation.STANDARD) # noqa

        start = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        query = {
            "deviceid": device_id_binary,
            "devicetime": {"$gte": start, "$lte": end}
        }

        projection = {
            "_id": 0,
            "deviceid": 1,
            "devicetime": 1,
            "data.evt.etm": 1,
            "data.evt.csm": 1,
            "data.binfo.bvt": 1,
            "data.binfo.bpon": 1
        }

        results = list(collection.find(query, projection))
        serialized_results = [serialize_mongo_doc(doc) for doc in results]

        return {
            "count": len(serialized_results),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "records": serialized_results
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}
