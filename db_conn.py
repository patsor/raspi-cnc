#!/usr/bin/env python

from argparse import ArgumentParser

import sqlalchemy

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


class PostgresDBConnection(object):
    def __init__(self, user, password, db, host="localhost", port=5432):
        self.url = "postgresql://{}:{}@{}:{}/{}".format(
            user,
            password,
            host,
            port,
            db
        )

    def connect(self):
        engine = sqlalchemy.create_engine(self.url, echo=False)

        return engine
        

class MongoDBConnection(object):
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
    db_conn = MongoDBConnection(args.host, args.port, args.db)

    print(db_conn.find_document("ramp_profiles", "T1200V50A0J"))

if __name__ == "__main__":
    main()
