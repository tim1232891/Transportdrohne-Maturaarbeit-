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

#hier ist die Objektüberfliegung definiert
async def distance_sensor(the_connection,checker_queue,queue_distance, queue_flugmission):###
        print("LOS GEHT DER DISTANCE SENSOR!!!!")
        await queue_flugmission.put((0, 0)) # Tupel-Aufbau: (Distanz, zusätzliche Höhe)
# In diesem Fall: keine Distanz -> signalisiert das "Go" für die Flugmission.

        while True:
            checker = 0
            distance = await queue_distance.get() # warten asynchron, bis eine Distanz erkannt wird
            current_mode = the_connection.flightmode
            if current_mode == "LAND" or current_mode == "LOITER": # whileschlaufe/distanzensensor stoppen, damit Drohne beim
                #übersteuern (mode == LOITER) und beim landen (mode == Land) nicht gestört wird
                break
            if distance:  
                höhen_differenz = 0
                while distance:
                    if checker == 0: # Wenn die Distanz zum ersten Mal erkannt wird (da sie beim Überflug weiterhin erfasst wird)
                        await checker_queue.put((1, 0)) # wird das laufende execution-Programm beendet
                        mode.set_mode_brake(the_connection = the_connection)# Drohne stoppt sofort (Brake-Modus-> Drohne stoppt sofort)
                        await asyncio.sleep(0.2)
                        mode.set_mode_guided(the_connection = the_connection) # Drohne wieder in Guided modus-> 
                        #Damit sie wieder Flugkommandos ausführen kann
                    flug_kommando.do_change_alt(the_connection=the_connection, alt = 2)# Die Drohne steigt so lange, 
                    #bis kein Objekt mehr erkannt wird, und erhöht danach die Höhe um zwei zusätzliche Sicherheitsmeter.
                    try: 
                        distance = await asyncio.wait_for(queue_distance.get(), timeout=2)
                    except asyncio.TimeoutError:
                        distance = None
                    checker = 1
                print("OBJEKT UEBERFLOGEN!!!!!")
                print(höhen_differenz)
                await asyncio.sleep(1) 
                await queue_flugmission.put((0, höhen_differenz))# Die Flightmission wird erneut durchgeführt.
# Die Höhendifferenz spielt in der neuesten Codeversion keine Rolle mehr,
# da die Flughöhe stets der aktuellen relativen Höhe der Drohne entspricht.