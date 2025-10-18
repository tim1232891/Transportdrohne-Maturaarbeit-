import numpy as np
import asyncio
from pymavlink import mavutil

# Dieses Skript sorgt dafür, dass die Flugkommandos korrekt ausgeführt werden. Wenn der Code zwei Flugkommandos 
# direkt nacheinander aufruft, würde das erste sofort überschrieben werden. Ein Flugkommando, wie es von pymavlink 
# definiert ist, sendet lediglich den Befehl. Dieser Vorgang erfolgt in sehr kurzer Zeit, und der Code läuft weiter, 
# ohne darauf zu warten, dass die Drohne den Zielort tatsächlich erreicht hat.


# Ausführung vom Start der Drohne (Takeoff)
async def execute_takeoff(z, queue_height, p0):
    pressure = await queue_height.get()

    height = 44330 * (1 - (pressure/p0)**0.1903) # Berechnet höhe barometrisch -> vereinfachte Formel, aber sehr akurat
# deutlich genauer als GPS
    while height + 0.5 < z: # toleranz 0.5
        pressure = await queue_height.get()
        height = 44330 * (1 - (pressure/p0)**0.1903)
        print(f"Die Drohne befindet sich auf {np.round((height/z)*100,1)}% der Zielhöhe")
    return True

# Ausführung für das lokale Fliegen (Angabe der Fluginstruktionen in Metern nicht in GPS Koordinaten)
# funktioniert mit Vektorannäherung! Wenn Vektoren sich genügend angenähert haben, dann wird while-Schlaufe beendet
async def execute_local(x,y,z, queue_data, checker_queue):
    print("EXECUTE LOCAL")
    checker = 0
    v_goal = np.array([x,y,z]) 
    msg = await queue_data.get()
    v_now = np.array([msg.x,msg.y,-msg.z])
    toleranz = np.linalg.norm(v_goal-v_now)
    while toleranz > 0.5 and checker ==0: #checker ist dafür da, wenn der LIDAR-Sensor ein Objekt erkennt, wird der checker 1
    # daraufhin wird whileschlaufe abgebrochen und Objekt kann überflogen werden. 
        msg = await queue_data.get()

        x = msg.x
        y = msg.y
        z = msg.z

        v_now = np.array([x,y,-z])  

        toleranz = np.linalg.norm(v_goal-v_now)
        print(f"Die Distanz zum Ziel beträgt {np.round(toleranz,1)} Meter!!!")


        try :
            checker, höhe = checker_queue.get_nowait() #nowait, damit Programm schnell weiterfährt, solange nichts in der QUEUE
            # nicht gefüllt ist
            # wenn checker -> dann checker 1 -> while-Schlaufe wird abgebrochen
        except asyncio.QueueEmpty:
            checker = 0 #->QUEUE wird nur mit 1 gefüllt im Fall von Distanz, wenn keine Distanz, dann 0 -> whileschlaufe läuft
            # weiter
    while not checker_queue.empty():
                    try:
                        x = checker_queue.get_nowait() #-> Queue wird zur Sicherheit geleert, damit dann wieder alles läuft
                    except asyncio.QueueEmpty:
                         break
    if checker != 0:
        print("ABBRUCH!!!!")
        return False #Damit Programm weiss, das while Schlaufe unterbrochen wurde
    else:
        return True #Damit Programm weiss, das while Schlaufe abgeschlossen wurde

# Aufführung für globales Fliegen (input sind Koordinaten)
async def execute_global(lat, lon, queue_flight, checker_queue):
    v_goal = np.array([lat,lon]) # Zielvektor
    checker = 0
    v_now = np.array(v_goal[0]-100,v_goal[1]-100) #erfundener Startvektor, damit While-Schlaufe anfängt
    while not np.allclose(v_now, v_goal, atol=40, rtol=0) and checker == 0: # solange sich beide Werte um 40 unterscheiden
        # meine Koordinate wird hierbei als Zahl angesehen bsp. 8.72830402 -> 872830402
        lat,lon = await queue_flight.get() # Längen und Breitengrad empfangen 
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


