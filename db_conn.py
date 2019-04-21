#!/usr/bin/env python

from argparse import ArgumentParser

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class DBConnection(object):
    def __init__(self, host, port, db_name):
        self.host = host
        self.port = port
        self.db_name = db_name
        self.db = self.open_connection()

    def open_connection(self):
        """Opens connection to the DB."""
        client = MongoClient(self.host, self.port)
        try:
            client.admin.command('ismaster')
        except ConnectionFailure:
            print("Server not available")
            return None
        db = client[self.db_name]
        return db

    def insert_document(self, coll, document):
        """Inserts one single document into collection."""
#        print("Inserting document {} inside {}".format(coll))
        collection = self.db[coll]
        doc_id = document["_id"]
        if self.find_document(coll, doc_id):
            print("Document '{}' already in '{}'.".format(doc_id, coll))
            return False
        else:
            collection.insert_one(document)
            print("Inserted '{}' into '{}'.".format(doc_id, coll))
            return True

    def find_document(self, coll, doc_id):
        """Finds one document in a given collection by documents _id."""
#        print("Searching for {} inside {}".format(doc_id, coll))
        collection = self.db[coll]
        document = collection.find_one({"_id": doc_id})
        if document:
#            print("Document '{}' retrieved from '{}'.".format(doc_id, coll))
            return document
        else:
#            print("Document '{}' not in '{}'.".format(doc_id, coll))
            return {}

def main():
    parser = ArgumentParser(description="Manages database connection")
    parser.add_argument("-s", "--host", dest="host", help="Specify host name", default="localhost")
    parser.add_argument("-p", "--port", dest="port", type=int, help="Specify port on which the DB runs on", default=27017)
    parser.add_argument("-d", "--db", dest="db", help="Specify db name")

    args = parser.parse_args()
    db_conn = DBConnection(args.host, args.port, args.db)
#    for a_max in range(1, 100):
#        for v_max in range(1, 1200):
        
#            rp = {"_id": "T{}V{}A0J".format(v_max, a_max),
#                   "v_max": float(v_max),
#                   "a_max": float(a_max),
#                   "j_max": 0.0,
#                   "T_accel": float(v_max / 60.0 / a_max),
#                   "step_timings": [0.125,
#                                    0.0875,
#                                    0.0625,
#                                    0.006327],
#                   "type": "trapezoidal"}
    
#            db_conn.insert_document("ramp_profiles", rp)
#    db_conn.insert_document("ramp_profiles", rp2)

    print(db_conn.find_document("ramp_profiles", "T1200V50A0J"))

if __name__ == "__main__":
    main()
