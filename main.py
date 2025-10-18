from gpiozero import OutputDevice
import asyncio
import numpy as np
import math
from pymavlink import mavutil
import flug_kommando
import async_data
import paket_ablagerung
import time
import mode
import sys
import safety
import mission
import objekt_erkennung
 
output_device = OutputDevice(27) #
output_device.on()# schaltet Elektromagneten ein 
time.sleep(5)

async def main(the_connection):
    stop_event = asyncio.Event() # erstellt alle nötigen Queues
    queue_data = asyncio.Queue()
    queue_flight = asyncio.Queue()
    queue_find = asyncio.Queue()
    queue = asyncio.Queue()
    queue_distance = asyncio.Queue()
    queue_height = asyncio.Queue()
    safety_queue = asyncio.Queue()
    queue_flugmission = asyncio.Queue()
    checker_queue = asyncio.Queue()
    msg = the_connection.recv_match(type='SCALED_PRESSURE', blocking=True) # Liest den aktuellen Luftdruck aus zur barometrischen 
    #Berechnung der aktuellen Höhe
    p0 = msg.press_abs
    mode = 'GUIDED'
    the_connection.set_mode(mode) # Setzt den Flugmodus auf GUIDED – nur in diesem Modus lässt sich die Drohne
# mit den selbst definierten Kommandos vollständig autonom steuern
    print("GUIDED")
    flug_kommando.arm_motors(the_connection=the_connection)
    print("Armed")
    # hier werden alle asynchronen Tasks erstellt
    producer = asyncio.create_task(async_data.data(the_connection,queue_data, queue_flight, queue,queue_height,queue_find,safety_queue,queue_distance))
    consumer = asyncio.create_task(async_data.consumer(queue))
    consumer_data = asyncio.create_task(async_data.consumer_data(queue_data))
    
    #Hier werden alle asynchronen Funktionen ausgerufen und laufen parallel
    await asyncio.gather(mission.flight_mission(the_connection = the_connection, queue_flight = queue_flight, queue_data = queue_data,  queue_height= queue_height, queue_find = queue_find,p0 = p0, checker_queue = checker_queue, queue_flugmission=queue_flugmission,stop_event = stop_event, output_device = output_device),producer, consumer, consumer_data, objekt_erkennung.distance_sensor(the_connection = the_connection,checker_queue= checker_queue, queue_flugmission= queue_flugmission,  queue_distance = queue_distance), safety.battery(the_connection, safety_queue))


if __name__ == "__main__":
    the_connection = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    the_connection.wait_heartbeat()
    asyncio.run(main(the_connection))
