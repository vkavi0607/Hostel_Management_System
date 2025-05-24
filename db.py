import pymongo
import os
import string
import random
from dotenv import load_dotenv

load_dotenv()  # For local development with a .env file

class MongoDBConnection:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            try:
                mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
                cls._instance.client = pymongo.MongoClient(mongo_uri)
                cls._instance.db = cls._instance.client["hostel_management_streamlit"]  # Or your preferred DB name
                # Test connection
                cls._instance.client.admin.command('ping')
                print("Successfully connected to MongoDB!")
            except pymongo.errors.ConnectionFailure as e:
                print(f"Could not connect to MongoDB: {e}")
                cls._instance = None  # Reset instance if connection fails
                raise
        return cls._instance

    def get_collection(self, collection_name):
        if self.client is None or self.db is None:
            raise Exception("MongoDB connection not established.")
        return self.db[collection_name]

# Helper to generate 6-digit alphanumeric userId
def generate_unique_id(length=6, max_attempts=10):
    chars = string.ascii_letters + string.digits
    users_collection = get_users_collection()
    for _ in range(max_attempts):
        new_id = ''.join(random.choice(chars) for _ in range(length))
        if not users_collection.find_one({"userId": new_id}):
            return new_id
    raise Exception("Failed to generate unique ID after maximum attempts.")

# --- Collection Getters (Convenience) ---
def get_users_collection():
    return MongoDBConnection().get_collection("users")

def get_rooms_collection():
    return MongoDBConnection().get_collection("rooms")

def get_room_requests_collection():
    return MongoDBConnection().get_collection("room_requests")

def get_maintenance_collection():
    return MongoDBConnection().get_collection("maintenance")

def get_events_collection():
    return MongoDBConnection().get_collection("events")

def get_fees_collection():
    return MongoDBConnection().get_collection("fees")

def get_visitors_collection():
    return MongoDBConnection().get_collection("visitors")

def get_feedback_collection():
    return MongoDBConnection().get_collection("feedback")

if __name__ == '__main__':
    # Test the singleton
    db_conn1 = MongoDBConnection()
    db_conn2 = MongoDBConnection()
    print(f"db_conn1 is db_conn2: {db_conn1 is db_conn2}")

    users_col = get_users_collection()
    print(f"Users collection: {users_col.name}")
    # You can create indexes here if needed, e.g., for unique fields
    users_col.create_index("email", unique=True)
    users_col.create_index("userId", unique=True)
    get_rooms_collection().create_index("number", unique=True)
    print("Indexes ensured.")