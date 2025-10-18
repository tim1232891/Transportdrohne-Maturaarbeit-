from pymavlink import mavutil
import asyncio
import numpy as np
import mode
import time

# In diesem Codeabschnitt werden die benötigten Daten vom Pixhawk (Flight Controller) abgefragt. Beim Empfang der 
# Daten werden sie in die entsprechende asynchrone Queue eingefügt.


# In dieser Definition wird ein Interval gesetzt in welcher der Pixhawk die Daten senden soll
def set_message_interval(the_connection, msg_id, period_s):
    period_us = int(period_s * 1_000_000)
    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        msg_id,
        period_us,
        0, 0, 0, 0, 0
    )

# In dieser asynchronen Definition werden die Intervale mit Hilfe der set_message_interval Defintion gesetzt und anschliessend
# in die passende asynchrone Queue gelegt
async def data(the_connection, queue_data, queue_flight, queue, queue_height,queue_find, safety_queue, queue_distance):
    start = None
    distance = None
    set_message_interval(the_connection, msg_id=32, period_s=1)   
    set_message_interval(the_connection, msg_id=33, period_s=1)   
    set_message_interval(the_connection, msg_id=24, period_s=1)   
    set_message_interval(the_connection, msg_id=132, period_s=0.05)    
    set_message_interval(the_connection, msg_id=1, period_s=1) 
    while True:
        global_position = the_connection.recv_match(type="GLOBAL_POSITION_INT", blocking=True)
        local_position = the_connection.recv_match(type="LOCAL_POSITION_NED", blocking=True)
        battery = the_connection.recv_match(type="SYS_STATUS", blocking=True)
        pressure = the_connection.recv_match(type="SCALED_PRESSURE", blocking =True)
        if start:
            distance = the_connection.recv_match(type="DISTANCE_SENSOR", blocking = True, timeout = 0.3)
        if global_position:
            await queue_flight.put((global_position.lat, global_position.lon))
            await queue.put(("global_position", global_position))
            if global_position.relative_alt > 1000:
                start = True
        if pressure:
            await queue_height.put(pressure.press_abs)
            print(pressure.press_abs)

        if local_position:
            await queue_data.put(local_position)
            await queue.put(("local_position", local_position))
        if distance:
            await queue_distance.put(distance)
        if battery:
            await queue.put(("battery", battery.battery_remaining))
            await safety_queue.put((battery.battery_remaining, battery.voltage_battery))
        await asyncio.sleep(1)

# Die consumer Definition kriegt die von data gesendeten Daten und plottet sie, damit eine Pilot:In die 
# Daten besser nachvollziehen kann
async def consumer(queue):
    while True:
        name, value = await queue.get()

        if name == "global_position":
            print(f"Global Position -> Lat: {value.lat / 1e7:.7f}, Lon: {value.lon / 1e7:.7f}")
            print(f"GPS Altitude -> {np.round(value.alt / 1000, 1)} m")
        elif name == "local_position":
            print(f"Local Position -> X: {value.x:.2f} m (North), Y: {value.y:.2f} m (East)")
        elif name == "battery":
            print(f"Battery Remaining -> {value}%")


async def consumer_data(queue_data):
    while True:
        data = await queue_data.get()
        print(f"Local X: {np.round(data.x, 1)} m")
