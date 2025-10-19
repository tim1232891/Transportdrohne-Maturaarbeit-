rom gpiozero import OutputDevice
import asyncio
import numpy as np
import math
from pymavlink import mavutil
import flug_kommando
import async_data
import paket_ablagerung
from concurrent.futures import ThreadPoolExecutor
import time
import mode
import sys
import safety

 
output_device = OutputDevice(27)
output_device.on()
time.sleep(5)
points_list = [
 (472633024, 86991679),
 (472631822, 86994328),


]
t0 = time.time()

ALT = 6

flug_mission = 0

async def distance_sensor(the_connection,checker_queue,queue_distance, queue_flugmission):###
        print("LOS GEHT DER DISTANCE SENSOR!!!!")
        await queue_flugmission.put((0, 0)) # Tupel-Aufbau: (Distanz, zusätzliche Höhe) -> In diesem Fall: keine Distanz, kei>
        while True:
            checker = 0
            distance = await queue_distance.get()
            current_mode = the_connection.flightmode
            if current_mode == "LAND" or current_mode == "LOITER": # whileschlaufe/distanzensensor stoppen, damit Drohne wirk>
                break
            if distance:  
                höhen_differenz = 0
                while distance:
                    if checker == 0:
                        await checker_queue.put((1, 0))
                        mode.set_mode_brake(the_connection = the_connection)
                        await asyncio.sleep(0.2)
                        mode.set_mode_guided(the_connection = the_connection)
                    flug_kommando.do_change_alt(the_connection=the_connection, alt = 2)
                    try: 
                        distance = await asyncio.wait_for(queue_distance.get(), timeout=2)
                    except asyncio.TimeoutError:
                        distance = None
                    höhen_differenz +=2
                    checker = 1
                print("OBJEKT UEBERFLOGEN!!!!!")
                print(höhen_differenz)
                await asyncio.sleep(1) 
                await queue_flugmission.put((0, höhen_differenz))# Die Flightmission, wird wieder Durchgeführt und zwar mit e>

i_MissionPoint = 0
global_flug_height = 0
return_to_home_height = 0
async def flight_mission(the_connection, queue_flight, queue_data,queue_height, queue_find, loop, pool,p0, HOME_ALT, checker_queue, queue_flugmission, queue_distance, stop_event ):
    global global_flug_height
    global return_to_home_height
    global flug_mission
    global i_MissionPoint
    print(flug_mission)
    while True:
        checker, höhendifferenz = await queue_flugmission.get()
        print("FLUGMISSION", checker)
        if checker == 0:
            print("WIR SIND WIEDER IN DER HAUPTMISSION")
        if flug_mission == 0 and checker ==0:
            ergebnis = await flug_kommando.takeoff_fin(the_connection=the_connection,queue_height=queue_height, z = ALT,p0 = p0, checker_queue = checker_queue)
            if ergebnis ==True:
                flug_mission += 1
            print("FERTIG ODER ABGEBROCHEN!!!!!", flug_mission)

        if flug_mission == 1 and checker ==0:
            global_flug_height += höhendifferenz
            msg = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            rel_alt = msg.relative_alt / 1000.0 
            while i_MissionPoint < len(points_list):
                mission = points_list[i_MissionPoint]
                ergebnis = await flug_kommando.fly_global_fin(the_connection=the_connection,  lat = mission[0] , lon = mission[1], alt = rel_alt, queue_flight=queue_flight, checker_queue = checker_queue)
                if ergebnis == False:
                    break
                else:
                    i_MissionPoint += 1
            if  ergebnis ==True:
                print("FERTIG MIT GLOBALEM FLUG")
                flug_mission += 1

            print("FERTIG ODER ABGEBROCHEN!!!!!")
        #
        if flug_mission ==2 and checker ==0:
            print("Task wird erstellt!!!")
            #asyncio.create_task(paket_ablagerung.thread_task(loop, pool, queue_find))
            print("Search Modus wird gestartet!!!")
#            ergebnis = await paket_ablagerung.search(the_connection = the_connection, queue_find = queue_find, queue_data=qu>
            result = await paket_ablagerung.annaeherung(the_connection, queue_find,queue_height,checker_queue, p0, stop_event)
            if result ==True:
                flug_mission += 1
                print("Wird abglagert!!")
                paket_ablagerung.elektromagnet(output_device=output_device)
                print("FERTIG ABGELAGERT!!!!!")
            else:
                print("ABRUCH!!!!!!!!!!!!!!!!")
        #try:
        #    checker, höhendifferenz = await asyncio.wait_for(checker_queue.get(),timeout=0.5)
        #    print("FLUG_MISSION", checker)
        #except asyncio.TimeoutError:
        #    checker, höhendifferenz = 0, 0
        if flug_mission ==3 and checker ==0:
            print("RETURN TO HOME!!!!")
            return_to_home_height += höhendifferenz
            ergebnis = await flug_kommando.return_to_home(the_connection = the_connection, queue_data = queue_data,checker_qu>
            print(ergebnis)
            if ergebnis != False:
                print("GELANDET")
                sys.exit(0) 
                break

async def main(the_connection):
    #loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    queue_data = asyncio.Queue()
    queue_flight = asyncio.Queue()
    queue_find = asyncio.Queue()
    queue = asyncio.Queue()
    queue_distance = asyncio.Queue()
    queue_height = asyncio.Queue()
    safety_queue = asyncio.Queue()
    queue_flugmission = asyncio.Queue()
    checker_queue = asyncio.Queue()
    msg = the_connection.recv_match(type='SCALED_PRESSURE', blocking=True)
    p0 = msg.press_abs
    msg = the_connection.recv_match(type = "GPS_RAW_INT", blocking = True)
    HOME_ALT= msg.alt/1000
    mode = 'GUIDED'
    the_connection.set_mode(mode)
    print("GUIDED")
    flug_kommando.arm_motors(the_connection=the_connection)
    print("Armed")
    #with ThreadPoolExecutor(max_workers=1) as pool:#einstufen
    producer = asyncio.create_task(async_data.data(the_connection,queue_data, queue_flight, queue,queue_height,queue_find,safety_queue,queue_distance))
        #distance = asyncio.create_task(async_data.distance(the_connection=the_connection,queue_distance=queue_distance, queu>
    consumer = asyncio.create_task(async_data.consumer(queue))
    consumer_data = asyncio.create_task(async_data.consumer_data(queue_data))
        #detector = asyncio.create_task(paket_ablagerung(loop, pool, queue_find))
    pool = 0
    loop = 0
    await asyncio.gather(flight_mission(the_connection = the_connection, queue_flight = queue_flight, queue_data = queue_data,  queue_height= queue_height, queue_find = queue_find,loop = loop, pool=pool,p0 = p0, HOME_ALT = HOME_ALT, checker_queue = checker_queue, queue_flugmission=queue_flugmission, queue_distance = queue_distance,, stop_event = stop_event),producer, consumer, consumer_data,, distance_sensor(the_connection = the_connection,checker_queue= checker_queue, queue_flugmission= flight_mission,  queue_distance = queue_distance), safety.battery(the_connection, safety_queue))


if __name__ == "__main__":
    the_connection = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    the_connection.wait_heartbeat()
    asyncio.run(main(the_connection))
