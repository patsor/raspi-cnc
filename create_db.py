#!/usr/bin/env python

from sqlalchemy import Table, Column, Integer, Float, String, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from db_conn import PostgresDBConnection

def main():

    db = PostgresDBConnection("pi", "x264codec", "test")
    conn, meta = db.connect()

    profiles = Table("ramp_profiles", meta,
                     Column("name", String, primary_key=True),
                     Column("type", String),
                     Column("v_max", Float),
                     Column("a_max", Float),
                     Column("j_max", Float),
                     Column("T_a", Float),
                     Column("TPR", Float),
                     Column("step_angle", Float),
                     Column("step_timings", ARRAY(Float))
    )

    meta.create_all(conn)

    ramp_profiles = meta.tables["ramp_profiles"]

    for i in range(1000):
        for j in range(1000):
            document = ramp_profiles.insert().values(
                name="S{}V{}A{}J".format(i, j, 0),
                type="sigmoidal",
                v_max=float(i),
                a_max=float(j),
                j_max=0.0,
                T_a=0.6,
                TPR=5.0,
                step_angle=1.8,
                step_timings=[
                    0.32,
                    0.02,
                    0.015,
                    0.01,
                    0.005
                ]
            )
        
            result = conn.execute(document)
            print(result.inserted_primary_key)

if __name__ == "__main__":
    main()
