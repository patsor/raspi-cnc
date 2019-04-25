#!/usr/bin/env python

import math

from sqlalchemy import Table, Column, Integer, Float, String, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY

from db_conn import PostgresDBConnection

def _configure_ramp_sigmoidal(vm, accel, mode):
    #self.logger.info("{} - Generating sigmoidal ramp profile [v_max={}]".format(self.name, vm))
    #outf = open("ramp_profile_s" + str(int(vm)) + ".csv", "w")
    # steps per revolution: microstepping mode as factor
    spr = 360.0 / 1.8 * mode
    # Number of steps it takes to move axis 1mm
    steps_per_mm = spr / 5.0
    # linear movement along the axes per step
    # angle of rotation (phi) per step in rad: 2 * PI = 360 degrees
    # [rotation_angle = 2 * PI / SPR]
    angle = 2 * math.pi / spr
    # Convert target velocity from mm/min to rad/s
    w = vm / 60 * steps_per_mm * angle
    # Convert acceleration from mm/s^2 to rad/s^2
    a = accel * steps_per_mm * angle
    ti = 0.4
    # pre-calculated values
    w_4_a = w / (4*a)
    a_4_w = (4*a) / w
    e_ti = math.e**(a_4_w*ti)
    e_n = math.e**(a_4_w*angle/w)
    t_mod = ti - w_4_a * math.log(0.005)
    
    num_steps = int(round(w**2 * (math.log(math.e**(a_4_w*t_mod) + e_ti) - math.log(e_ti + 1)) / (4*a*angle)))
#        t = 0.0
    c = []
    for i in range(1, num_steps):
        cn = w_4_a * math.log(((e_ti + 1) * e_n**(i+1) - e_ti)/((e_ti + 1) * e_n**i - e_ti))
        #print(1/cn/steps_per_mm*60)
#            t += cn
#            outf.write("{};{}\n".format(t, 1.0/cn/40*60))
        c.append(cn)
        # Get the total duration of all acceleration steps
        # should be [t_a = cf/a]
    c_total = sum(c)
#        outf.close()
    return (c, c_total)

def main():

    db = PostgresDBConnection("pi", "x264codec", "test")
    conn, meta = db.connect()

    profiles = Table("ramp_profiles", meta,
                     Column("name", String, primary_key=True),
                     Column("type", String),
                     Column("v_max", Float),
                     Column("a_max", Float),
                     Column("j_max", Float),
                     Column("mode", Integer),
                     Column("T_a", Float),
                     Column("TPR", Float),
                     Column("step_angle", Float),
                     Column("step_timings", ARRAY(Float))
    )

    meta.create_all(conn)

    ramp_profiles = meta.tables["ramp_profiles"]
    
    for i in range(200, 1201):
        for j in range(10, 201):
            ins = ramp_profiles.insert()
            doc_list = []
            for k in [1, 2, 4, 8, 16, 32]:
                (step_delays, total_time) = _configure_ramp_sigmoidal(float(i), float(j), k)
                #print(step_delays, total_time)
                name = "S{}V{}A{}J{}M".format(i, j, 0, k)
                values = {"name": name,
                          "type": "sigmoidal",
                          "v_max": float(i),
                          "a_max": float(j),
                          "j_max": 0.0,
                          "T_a": total_time,
                          "mode": k,
                          "TPR": 5.0,
                          "step_angle": 1.8/k,
                          "step_timings": step_delays}
                #----------- document = ramp_profiles.insert().values(name=name,
                                                         #---- type="sigmoidal",
                                                         #------ v_max=float(i),
                                                         #------ a_max=float(j),
                                                         #----------- j_max=0.0,
                                                         #------ T_a=total_time,
                                                         #-------------- mode=k,
                                                         #------------- TPR=5.0,
                                                         #---- step_angle=1.8/k,
                                                         # step_timings=step_delays)
                #print(document)
                doc_list.append(values)
            conn.execute(ins, doc_list)
        print(i)
        
            #print(result.inserted_primary_key)
            #print(name)

if __name__ == "__main__":
    main()
