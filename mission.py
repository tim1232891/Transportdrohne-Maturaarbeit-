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


async def flight_mission(the_connection, queue_flight, queue_data,queue_height, queue_find,p0, checker_queue, queue_flugmission, stop_event, output_device ):
    points_list = [
    (-353628054, 1491652735),
    (-353628448, 1491653903),
    (-353629401, 1491654387),
    (-353630354, 1491653903),
    (-353630748, 1491652735),
    (-353630354, 1491651567),
    (-353629401, 1491651083),
    (-353628448, 1491651567),
] # Hier wird eine Beispiel-Liste mit Koordinaten für die Simulation erstellt.
# Im realen Einsatz würde an dieser Stelle die Route aus dem Skript berechnung_orders oder berechnung_waypoints eingelesen,
# das die Koordinaten der Wohnadressen von der Website erhält oder eine Flugroute aus Wegpunkten

    ALT = 6

    flug_mission = 0
    i_MissionPoint = 0
    global_flug_height = 0
    return_to_home_height = 0
    while True: # damit flugmission ausgeführt wird, auch wenn von Objekterkennung unterbrochen
        checker, höhendifferenz = await queue_flugmission.get() 
        print("FLUGMISSION", checker)
        if checker == 0:
            print("WIR SIND WIEDER IN DER HAUPTMISSION")
        if flug_mission == 0 and checker ==0: # Funktionen werden jeweils ausgeführt, wenn kein Objekt erkannt wird (checker == 0)
            ergebnis = await flug_kommando.takeoff_fin(the_connection=the_connection,queue_height=queue_height, z = ALT,p0 = p0)
            if ergebnis ==True: # Wenn das Kommando erfolgreich ausgeführt wurde, wird flugmission um +1 erhöht.
# Dadurch wird verhindert, dass die Funktion takeoff_fin erneut aufgerufen wird,
# sobald sie einmal erfolgreich abgeschlossen wurde.
                flug_mission += 1
            print("FERTIG ODER ABGEBROCHEN!!!!!", flug_mission)

        if flug_mission == 1 and checker ==0:
            global_flug_height += höhendifferenz
            msg = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            rel_alt = msg.relative_alt / 1000.0 
            while i_MissionPoint < len(points_list): #geht alle Koordianten durch 
                mission = points_list[i_MissionPoint]
                ergebnis = await flug_kommando.fly_global_fin(the_connection=the_connection,  lat = mission[0] , lon = mission[1], alt = rel_alt, queue_flight=queue_flight, checker_queue = checker_queue)
                if ergebnis == False: # Wenn ergebnis == False, bedeutet das, dass ein Objekt erkannt wurde und der Flug unterbrochen wurde.
# In diesem Fall bleibt flugmission unverändert und die aktuelle Koordinate wird erneut angeflogen.
                    break
                else:
                    i_MissionPoint += 1 # Wenn eine Koordinate erfolgreich angeflogen wurde, wird sie nicht erneut aufgerufen

            if  ergebnis ==True:
                print("FERTIG MIT GLOBALEM FLUG")
                flug_mission += 1 # Wenn alle Koordinaten erfolgreich abgeflogen wurden, wird der nächste Schritt eingeleitet

            print("FERTIG ODER ABGEBROCHEN!!!!!")
        if flug_mission ==2 and checker ==0:
            print("Task wird erstellt!!!")
            print("Search Modus wird gestartet!!!")
            result = await paket_ablagerung.annaeherung(the_connection, queue_find,queue_height,checker_queue, p0, stop_event)
            # Versucht den Apriltag zu erkennen und nähert sich ihm bis auf eine relative definierte Höhe an
            if result ==True:
                flug_mission += 1
                print("Wird abglagert!!")
                paket_ablagerung.elektromagnet(output_device=output_device)
                #Hier lässt die Drohne das Päckchen fallen
                print("FERTIG ABGELAGERT!!!!!")
            else:
                print("ABRUCH!!!!!!!!!!!!!!!!")


        if flug_mission ==3 and checker ==0:
            print("RETURN TO HOME!!!!")
            return_to_home_height += höhendifferenz
            ergebnis = await flug_kommando.return_to_home(the_connection = the_connection, queue_data = queue_data,checker_queue = checker_queue)
            # Drohne fliegt nach Hause
            print(ergebnis)
            if ergebnis != False:
                print("GELANDET")
                sys.exit(0) 
                break