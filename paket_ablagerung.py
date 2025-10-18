import numpy as np
import flug_kommando
import asyncio
import camera
stop_event = asyncio.Event()

#Das ganze Skript ist für die Ablagerung des Paketets am gewünschten Ort zuständig
def elektromagnet(output_device):
    output_device.off() #Elektromagnet aus -> Päckchen fallengelassen
    print("Package has been dropped!")

async def annaeherung(the_connection, queue_find,checker_queue, pressure_0, stop_event):
    cam_task = asyncio.create_task(camera.camera_loop(queue_find, stop_event)) # camera wird gestartet und versucht Apriltag zu erkennen
    alt = 5
    print("IN ANNäHRUNG!!!!!!!!!!!!")
    while alt > 4.5 and not stop_event.is_set():
        array, size = await queue_find.get() #hier kommen die Eckpunkte von den Apriltagpixel und die Auflösung von der Kamera
        print(array)
        apriltag_length = 0.75 # in Meter 
        array =  np.array(array)
        # berechntet die Länge in Pixel vom Apriltag stabil und sicher. Auch bei eher seitlicher Aufnahme sehr akkurate Werte
        p0, p1, p2, p3 = [array[i].astype(float) for i in range(4)]
        a = np.linalg.norm(p1 - p0)
        b = np.linalg.norm(p2 - p1)
        c = np.linalg.norm(p2 - p3)
        d = np.linalg.norm(p3 - p0)
        x = 0.5 * (a + c)
        y = 0.5 * (b + d)
        pixel_length = np.sqrt(x * y) # Geometrisches Mittel
        print(pixel_length)
        mittelpunkt_x = (array[0][0]+ array[1][0] + array[2][0] + array[3][0])/4 #bestimmt die X-Koordinate vom Mittelpunkt x
        mittelpunkt_y = (array[0][1] + array[1][1] + array[2][1]+ array[3][1])/4 #bestimmt die Y-Koordinate vom Mittelpunkt y
        tag = np.array([mittelpunkt_x, mittelpunkt_y]) #bestimmung des Mittelpunkts von Apriltag auf Sichtfeld der Kamera
        drohne = np.array(size)/2 # Mittelpunkt vom Sichtfeld der Kamera (auf Kameraeinstellung gesetzt)

        richtungs_vektor = tag - drohne #Berechnung vom Richtungsvektor in Pixel 
        print("RICHTUNGSVEKTOR PIXEL",richtungs_vektor)
        richtungs_vektor_m = richtungs_vektor/pixel_length*apriltag_length #Richtungsvektor Pixel multipliziert 
        #mit k Faktor (Echte Länge/Pixellänge) -> gibt realen Richtungsvektor, welcher als FLugkommando an die Drohne geht
        print("RICHTUNGSVEKTOR",richtungs_vektor_m)

        distanz_rechts = richtungs_vektor_m[0] # lokale Distanz nach rechts
        distanz_vorne = -richtungs_vektor_m[1] # distanz nach vorne (das Minus kommt davon, das Pixelkoordiantensystem (x|-y) ist)
        try :
            checker, höhe = checker_queue.get_nowait() #nowait, damit Programm schnell weiterfährt, solange nichts in Queue
            print("EX LOCAL", checker) # -> Wird Null sein, solage keine Distanz entdeckt wird
        except asyncio.QueueEmpty:
            checker = 0 #->QUEUE wird nur mit 1 gefüllt im Fall das eine Distanz entdeckt wird, wenn keine Distanz, dann 0 
            print("NICHTS CHECKER = 0")
        if checker ==0:
            flug_kommando.ablagerung(the_connection = the_connection, x = distanz_vorne, y = distanz_rechts, z = 1) 
            #Flugkommando wird gesendet(max. einen Meter nach unten) -> wenn während der Flugzeit der Apriltag wieder erkannt wird
            #so wird Flugkommando direkt wieder überschieben (kein execution)-> Ziel: es Korrigiert sich immer wieder aus -> je 
            #näher am Apriltag desto genauer wird die Annäherung
            print("YUHUUUUUUUUU")
        else: 
            return False
        try :
            pressure = the_connection.recv_match(type= "SCALED_PRESSURE", blocking = True) #blocking True: damit es sicher
            # den Luftdruck für Berechnung hat. (blocking True ist nicht schlau bei einem asynchronen Code, da es blockierend ist, 
            # der Luftdruck wird jedoch in einer sehr hohen Frequenz geschickt)
            pressure = pressure.press_abs
            alt = 44330 * (1 - (pressure/pressure_0)**0.1903)
            print("AAAALLLLTTT", alt)
        except asyncio.QueueEmpty:
            alt = alt
        await asyncio.sleep(0.3)
    stop_event.set() # Sobald sich Drohne unter 4.5 Metern relative höhe befindet, ist annaeherung beendet und 
    #stop_evet wird gesetzt, damit Kamera auch beendet wird -> benötigt nämlich relativ viel CPU
    try:
        await cam_task
    except asyncio.CancelledError:
        pass
    return True
