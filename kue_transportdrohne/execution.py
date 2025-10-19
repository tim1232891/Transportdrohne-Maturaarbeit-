import numpy as np
import asyncio
from pymavlink import mavutil


async def execute_takeoff(z, queue_height, p0, checker_queue):
    pressure = await queue_height.get()

    height = 44330 * (1 - (pressure/p0)**0.1903)
    print(height)
    while height + 0.5 < z:
        pressure = await queue_height.get()
        height = 44330 * (1 - (pressure/p0)**0.1903)
        print(f"Die Drohne befindet sich auf {np.round((height/z)*100,1)}% der Zielhöhe")
    return True


async def execute_local(x,y,z, queue_data, checker_queue):
    print("EXECUTE LOCAL")
    checker = 0
    v_goal = np.array([x,y,z])
    msg = await queue_data.get()
    v_now = np.array([msg.x,msg.y,-msg.z])
    toleranz = np.linalg.norm(v_goal-v_now)
    while toleranz > 0.5 and checker ==0: #brauchen noch checker oder àhnliches
        msg = await queue_data.get()

        x = msg.x
        y = msg.y
        z = msg.z

        v_now = np.array([x,y,-z])  

        toleranz = np.linalg.norm(v_goal-v_now)
        print(f"Die Distanz zum Ziel beträgt {np.round(toleranz,1)} Meter!!!")


       try :
            checker, höhe = checker_queue.get_nowait() #nowait, damit Programm schnell weiterfährt, solange nichts in der QUE>
            print("EX LOCAL", checker)# -> normal nichts ausser Distanz entdeckt 
        except asyncio.QueueEmpty:
            checker = 0 #->QUEUE wird nur mit 1 gefüllt im Fall von Distanz, wenn keine Distanz, dann 0 -> whileschlaufe läuf>
            print("NICHTS CHECKER = 0")
        #while not checker_queue.empty():
        #            try:
        #                x = checker_queue.get_nowait()
        #                print("LEEREN", x)
#                    except asyncio.QueueEmpty:
#                        break
    print("Zwischenziel ERREICHT ODER ABGEBRUCHEN!!!!")
    while not checker_queue.empty():
                    try:
                        x = checker_queue.get_nowait()
                        print("LEEREN", x)
                    except asyncio.QueueEmpty:
                         break
    if checker != 0:
        print("ABBRUCH!!!!")
        return False #Damit Programm weiss, das while Schlaufe unterbrochen wurde
    else:
        return True #Damit Programm weiss, das while Schlaufe abgeschlossen wurde


async def execute_local_sensor(x,y,z, queue_data, checker_queue): # while-schlaufe ohne chekcer definiert: wird immer ausgefü>
    v_goal = np.array([x,y,z])
    msg = await queue_data.get()
    v_now = np.array([msg.x,msg.y,-msg.z])
    toleranz = np.linalg.norm(v_goal-v_now)

    while toleranz > 0.5: #brauchen noch checker oder àhnliches
        msg = await queue_data.get() 
        x = msg.x
        y = msg.y
        z = msg.z

        v_now = np.array([x,y,-z])  

        toleranz = np.linalg.norm(v_goal-v_now)
        print(f"SENSOR_DATEN sind {np.round(toleranz,1)} Meter vom ZIEL ENTFERNT!!!")
    print("WIR HABEN OBJEKT UEBERFLOGEN!!!!")
async def execute_local_ablagerung(x,y,z, queue_data, the_connection, HOME_ALT, checker_queue):
    print("EXECUTE PAKETABLAGERUNG")
    v_goal = np.array([x,y,z])
    msg = await queue_data.get()
    v_now = np.array([msg.x,msg.y,-msg.z])
    toleranz = np.linalg.norm(v_goal-v_now)
    höhe = 5
    checker = 0
    while toleranz > 0.5 and höhe > 4.5 and checker ==0: #brauchen noch checker oder àhnliches
        print("CHECKER ==", checker)
        msg = await queue_data.get() 
        x = msg.x
        y = msg.y
        z = msg.z

        v_now = np.array([x,y,-z])  

        toleranz = np.linalg.norm(v_goal-v_now)
        gps = the_connection.recv_match(type = "GPS_RAW_INT", blocking=True)
        gps_höhe = gps.alt/1000
        höhe = gps_höhe-HOME_ALT
        print(höhe)
        try :
            checker, x = checker_queue.get_nowait() # selbe Idee wie von oben
            print("EX LOCAL ABLAGERUNG", checker)
        except asyncio.QueueEmpty:
            checker = 0
        print(f"Die Distanz zum Ziel beträgt {np.round(toleranz,1)} Meter!!!")
    print(toleranz)
    while not checker_queue.empty():
            try:
                x = checker_queue.get_nowait()
                print("LEEREN", x)
            except asyncio.QueueEmpty:
                break
    if checker !=0:
        print("FALSE -> ABBRUCH")
        return False

    else:
        print("TRUE -> DURCHSCHGEFüHRT")
        return True


async def execute_global(lat, lon, queue_flight, checker_queue):
    v_goal = np.array([lat,lon])
    checker = 0
    #msg = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking = True)
    v_now = np.array(v_goal[0]-100,v_goal[1]-100)
    while not np.allclose(v_now, v_goal, atol=40, rtol=0) and checker == 0: # wenn beide vektoren werte sich um max 10 unters>
        print("EXECUTE_GLOBAL_CHECKER", checker)
        lat,lon = await queue_flight.get()
        #print("QUEUE GIBT DATEN!!!!!!!!!!!!!!!!!!!")
        v_now = np.array([lat,lon])  
        try :
            checker, x = checker_queue.get_nowait() #selbe Idee wie oben
            print("EX GLOBAL", checker)
        except asyncio.QueueEmpty:
            checker = 0
    while not checker_queue.empty():
                try:
                    x = checker_queue.get_nowait()
                    print("LEEREN", x)
                except asyncio.QueueEmpty:
                     break
    if checker != 0:
        print("ABRRUCH")
        return False
    else:
        print("FINISHED")
        return True
        #print(v_goal)
        #print(v_now)


