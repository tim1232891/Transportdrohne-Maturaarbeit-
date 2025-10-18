from pymavlink import mavutil
import execution

#Hierbei definiere ich Funktionen, die es ermöglichen, gezielte Bewegungen der Drohne auszuführen


# Definition für die Ablagerung vom Päckchen. Hierbei habe ich das Frame mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED
# genommen. So fliegt die Drohne vom der aktuellen Position x Meter nach Vorne, y Meter nach rechts und z Meter nach untern.
def ablagerung(the_connection,x,y,z):
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED, # Frame     
        0b110111111000, # ist die Typemask und bestimmt welcher Parameter relevant sind. In diesm Fall nur die Position.
        #Die Beschleunigung in die jeweilige Richtung wird mit dieser Typemask zu beispiel vernachlässigt 
        x,
        y,
        z,
        0,0,0,0,0,0,0,0
        )
        set_speed(the_connection = the_connection, speed = 0.5)

# Der Befehl do_change_alt ist für die den Fall, dass der Distanzensensor ein Objekt erkennt. Dabei fliegt die Drohne um gegebene
# variabel alt hoch. 
def do_change_alt(the_connection, alt):#lässt die Drohne Lokal zu momentanen Standort fliegen
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_LOCAL_OFFSET_NED, #Frame ist ebenfalls von Position der Drohne aus, statt vorne und rechts, 
        #stehe x und y für die Distanz in Richtung Norden und Osten. Das spielt keine Rolle, da nur z Achse verwendet wird.
        # NED steht für North East Down -> deshalb wird bei Down -alt gesetzt. 
        0b110111111000,
        0,
        0,
        -alt,
        0,0,0,0,0,0,0,0
        )

# set_speed ist eine Definition, welche die Geschindgkeit der Drohne regelt
def set_speed(the_connection, speed):
        the_connection.mav.command_long_send(
                the_connection.target_system,         
                the_connection.target_component,        
                mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, 
                0,
                0,
                speed, 
                0, 0, 0, 0, 0
        )
# die arm_motors-Defintion startet die Motoren ohne sofort abzuheben 
def arm_motors(the_connection):
        the_connection.mav.command_long_send(
        the_connection.target_system,         
        the_connection.target_component,        
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 
        0,
        1,
        0, 0, 0, 0, 0, 0
        )
        the_connection.motors_armed_wait()


# Das ist die takeoff-Definiton. Sie lässt die Drohne auf z Meter steigen. 
def takeoff(the_connection, z):
        the_connection.mav.command_long_send(
        the_connection.target_system,         
        the_connection.target_component,        
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 
        0,
        0,
        0, 0, 0, 0, 0, z        
        )
# die Land-Defintion lässt die Drohne landen 
def land(the_connection):
    the_connection.mav.command_long_send(
    the_connection.target_system,         
    the_connection.target_component,        
    mavutil.mavlink.MAV_CMD_NAV_LAND, 
    0,
    0,
    0, 0, 0, 0, 0, 0
    )


# Die asynchrone takeoff_fin-Definition ist die finale Funktion zum Startvorgang. Sie ruft intern execute_takeoff 
# (execution Skript) auf. Dadurch muss im endgültigen Code nur diese Definition aufgerufen werden, das 
# Flugkommando wird vollständig ausgeführt und abgeschlossen, bevor der restliche Code fortgesetzt wird.
async def takeoff_fin(the_connection, z, queue_height, p0, checker_queue):
      takeoff(the_connection = the_connection, z = z)
      ergebnis = await execution.execute_takeoff(z = z, queue_height=queue_height, p0 = p0,checker_queue = checker_queue)
      return ergebnis

# Das ist die notfall_landung defintion. Sie wird aufgerufen, wenn der Batterie zustand zu tief ist. Sie läuft unabhängig von 
# der Flugmission. Dadruch überschreibt sie jedes Flugkommando und wird sicher ausgeführt
def notfall_landung(the_connection):
        the_connection.mav.command_long_send(
        the_connection.target_system,         
        the_connection.target_component,        
        mavutil.mavlink.MAV_CMD_NAV_LAND, 
        0,
        0,
        0, 0, 0, 0, 0, 0
        ) 
        print("Die Notfalllandung wurde eingeleitet!!!!")


# Die fly_ned-Definition steuert die Flugrichtung lokal relativ zum Startpunkt der Drohne und eignet sich 
# daher ideal für die Return-to-Home-Funktion.
def fly_ned(the_connection, x, y, z):
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,   # Die fly_ned-Definition fliegt lokal von der Startposition aus:
# x Meter nach Norden, y Meter nach Osten und z Meter nach unten (negative z-Werte führen nach oben)    
        0b110111111000,
        x,
        y,
        -z,
        0,0,0,0,0,0,0,0
        )


# fly_ned_fin-Defintion sendet fly_ned Nachricht und führt sie mit Hilfe vom Executionskript aus
async def fly_ned_fin(the_connection, x,y,z, queue_data, checker_queue):
        fly_ned(the_connection = the_connection, x = x, y = y, z = z)
        set_speed(the_connection=the_connection, speed = 1)
        result =  await execution.execute_local(x = x, y = y, z = z, queue_data = queue_data, checker_queue = checker_queue)
        return result


# Die fly_global-Definition lässt die Drohne global per GPS fliegen.
# WICHTIG: 'lat' steht für Längengrad und 'lon' für Breitengrad.
# Im gesamten Code wurden diese Variablen vertauscht. Ich lasse es jetzt aus Zeitgründen so stehen, um Fehlfunktionen zu vermeiden.
def fly_global(the_connection, lat, lon, alt):
        #msg = the_connection.recv_match(type = "GPS_RAW_INT", blocking = True)
        #alt = msg.alt
        the_connection.mav.set_position_target_global_int_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, # Steht für das FRAME global Fliegen und die 
        #Höhe ist relativ zur Startpunkthöhe   
        3576, # Typemask (in Dezimal statt Binär angegeben) –> verwendet nur die Positionsdaten
# und ignoriert alle anderen Parameter wie Beschleunigung und Yaw-Rate
        lat,
        lon,
        alt, # alt in Meter über Boden
        0,0,0,0,0,0,0,0
        )

# die fly_global_fin-Defintion sendet fly_global Nachricht und führt sie mit Hilfe vom Executionskript aus
async def fly_global_fin(the_connection, lat, lon, alt, queue_flight, checker_queue):
        fly_global(the_connection= the_connection, lat = lat, lon = lon, alt = alt)
        set_speed(the_connection=the_connection, speed = 5)
        ergebnis = await execution.execute_global(lon=lon, lat = lat, queue_flight=queue_flight, checker_queue = checker_queue) 
        return ergebnis



# Das return_to_home-Skript arbeitet mit Hilfe von fly_ned im NED-Frame (North, East, Down),
# also relativ zum Startpunkt der Drohne.
# Ablauf:
# 1. Drohne steigt auf -10 Meter (entspricht 10 m Höhe).
# 2. Anschliessend fliegt sie auf dieser Höhe (abhängig von der Objekterkennung)
#    mit Norden = 0 und Osten = 0 zur Home-Position zurück.
# 3. Dort angekommen, landet sie automatisch.

returner = 0
async def return_to_home(the_connection, queue_data, checker_queue):
      returner = 0
      if returner == 0:
            msg = the_connection.recv_match(type =  "LOCAL_POSITION_NED", blocking = True)
            resultat = await fly_ned_fin(the_connection = the_connection, x = msg.x , y = msg.y ,z = 10, queue_data = queue_data,  checker_queue = checker_queue)
            if resultat == True:
                  returner +=1
      if returner == 1:
            msg = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            rel_alt = msg.relative_alt / 1000.0 
            resultat = await fly_ned_fin(the_connection = the_connection, x = 0 , y = 0 ,z = rel_alt, queue_data = queue_data,  checker_queue = checker_queue)
            if resultat == True:
                  returner +=1
      if returner == 2:
            land(the_connection=the_connection)
            return True
      else:
            return False

 
