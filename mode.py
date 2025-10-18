from pymavlink import mavutil


# Hier werden lediglich die verschiedenen Flugmodi definiert, um sie später einfach und übersichtlich aufrufen zu können

def set_mode_stabalized(the_connection):
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = 0

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        base_mode,
        custom_mode,
        0, 0, 0, 0, 0
    )

def set_mode_guided(the_connection):
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = 4

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        base_mode,
        custom_mode,
        0, 0, 0, 0, 0
    )

def set_mode_loiter(the_connection):
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = 5

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        base_mode,
        custom_mode,
        0, 0, 0, 0, 0
    )

def set_mode_brake(the_connection):
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = 17

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        base_mode,
        custom_mode,
        0, 0, 0, 0, 0
    )

def set_mode_auto(the_connection):
    base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    custom_mode = 3

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        base_mode,
        custom_mode,
        0, 0, 0, 0, 0
    )


