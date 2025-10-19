from pymavlink import mavutil
import numpy as np
import math
import time
import asyncio
import mode
import flug_kommando
#import FLY_COMMANDS
#import DATA
#import modes
#import EXECUTION
import execution

def change_alt(the_connection, alt):
    the_connection.mav.command_long_send(
    the_connection.target_system,
    the_connection.target_component,
    mavutil.mavlink.MAV_CMD_DO_CHANGE_ALTITUDE,
    0,        
    0, 0, 0, 0,  
    0, 0, alt)
    set_speed(the_connection = the_connection, speed = 1)

def ablagerung(the_connection,x,y,z):
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,       
        0b110111111000,
        x,
        y,
        z,
        0,0,0,0,0,0,0,0
        )
        set_speed(the_connection = the_connection, speed = 0.5)
def do_change_alt(the_connection, alt):#lässt die Drohne Lokal zu momentanen Standprt fliegen
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_LOCAL_OFFSET_NED,       
        0b110111111000,
        0,
        0,
        -alt,
        0,0,0,0,0,0,0,0
        )
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

def takeoff(the_connection, z):
        the_connection.mav.command_long_send(
        the_connection.target_system,         
        the_connection.target_component,        
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 
        0,
        0,
        0, 0, 0, 0, 0, z        
        )

def land(the_connection):
    the_connection.mav.command_long_send(
    the_connection.target_system,         
    the_connection.target_component,        
    mavutil.mavlink.MAV_CMD_NAV_LAND, 
    0,
    0,
    0, 0, 0, 0, 0, 0
    )

async def takeoff_fin(the_connection, z, queue_height, p0, checker_queue):
      takeoff(the_connection = the_connection, z = z)
      ergebnis = await execution.execute_takeoff(z = z, queue_height=queue_height, p0 = p0,checker_queue = checker_queue)
      return ergebnis

def fly_ned_paket(the_connection, x, y, z):
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,       
        3520,
        10,
        10,
        3,
        0,0,0,0,0,0,0,0
        )

async def paket_abgabe(the_connection, x,y,z):
      fly_ned_paket(the_connection = the_connection, x = x, y = y, z = z)
      #await execution.execute_local(x = x, y = y, z = z, queue_flight = queue_flight)


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


def fly_ned(the_connection, x, y, z):
        the_connection.mav.set_position_target_local_ned_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,       
        0b110111111000,
        x,
        y,
        -z,
        0,0,0,0,0,0,0,0
        )

async def fly_ned_fin(the_connection, x,y,z, queue_data, checker_queue):
        fly_ned(the_connection = the_connection, x = x, y = y, z = z)
        set_speed(the_connection=the_connection, speed = 1)
        result =  await execution.execute_local(x = x, y = y, z = z, queue_data = queue_data, checker_queue = checker_queue)
        return result
async def fly_ned_fin_ablagerung(the_connection, x,y,z, queue_data, checker_queue, HOME_ALT):
        fly_ned(the_connection = the_connection, x = x, y = y, z = z)
        set_speed(the_connection=the_connection, speed = 1)
        ergebnis = await execution.execute_local_ablagerung(the_connection= the_connection,x = x, y = y, z = z, queue_data = queue_data, checker_queue = checker_queue, HOME_ALT=HOME_ALT)

        return ergebnis

async def fly_ned_fin_sensor(the_connection, x,y,z, queue_data, checker_queue):
        print("LEGOOOOOOOOOO")
        fly_ned(the_connection = the_connection, x = x, y = y, z = z)
        fly_ned(the_connection = the_connection, x = x, y = y, z = z)
        set_speed(the_connection=the_connection, speed = 2)
        await execution.execute_local_sensor(x = x, y = y, z = z, queue_data = queue_data, checker_queue = checker_queue)

async def ausweichen(the_connection, queue_distance, queue_data, checker_queue):
        while True:
                distance = await queue_distance.get() 
                print("I'VE GOT THE DISTANCE!!!!")
                if distance:
                        msg = the_connection.recv_match(type = "LOCAL_POSITION_NED", blocking = True)
                        mode.set_mode_guided(the_connection=the_connection)
                        print(msg)
                        await flug_kommando.fly_ned_fin_sensor(the_connection=the_connection,x = msg.x,y =  msg.y, z = (-msg.z + 2), queue_data=queue_data, checker_queue= checker_queue)

 

def fly_global(the_connection, lat, lon, alt):
        #msg = the_connection.recv_match(type = "GPS_RAW_INT", blocking = True)
        #alt = msg.alt
        the_connection.mav.set_position_target_global_int_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,       
        3576,
        lat,
        lon,
        alt, # alt in Meter über Boden
        0,0,0,0,0,0,0,0
        )

async def fly_global_fin(the_connection, lat, lon, alt, queue_flight, checker_queue):
        fly_global(the_connection= the_connection, lat = lat, lon = lon, alt = alt)
        set_speed(the_connection=the_connection, speed = 5)
        ergebnis = await execution.execute_global(lon=lon, lat = lat, queue_flight=queue_flight, checker_queue = checker_queue) 
        return ergebnis

async def battery_security_fm(the_connection, absolvierte_flugstrecke):
    while True:
        msg = the_connection.recv_match(type='SYS_STATUS', blocking=True)
        safety = 65 #65% Battery / 50% optimalen Battery(Ohne Batteryschaden Risiko)
        print(f"Die Batterie beträgt {msg.battery_remaining}%")
        voltage = msg.voltage_battery
        #battery_percentage = (voltage - 12800)/16800 * 100 # Prozent von Lipo Batterie 0% 3.2 Volt -> sehr Niedring
        battery_percentage = msg.battery_remaining # für Battery von SITL
        if battery_percentage < safety:
            if absolvierte_flugstrecke < 50:
                print("NOTFALLLANDUNG !!!")
                flug_kommando.notfall_landung(the_connection)
                break
 
            else: 
                safety = 0

        if battery_percentage < 35:
            msg = the_connection.recv_match(type='HEARTBEAT', blocking=True)
            flight_mode = msg.custom_mode
            print("\033[91mBATTERIE WARNUNG:\033[0m Die Landung wird in kürze eingeleitet!!")
            if str(flight_mode) == "9":
                break
 

 
        if battery_percentage < 30:
            flug_kommando.notfall_landung(the_connection)
            break
def change_alt(the_connection, alt):

        the_connection.mav.set_position_target_global_int_send(
        0,
        the_connection.target_system,         
        the_connection.target_component, 
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,       
        0b110111111000,
        0,
        0,
        alt, # alt in Meter über Boden
        0,0,0,0,0,0,0,0
        )
returner = 0
async def return_to_home(the_connection, queue_data, checker_queue, höhendifferenz):
      global returner
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

 
