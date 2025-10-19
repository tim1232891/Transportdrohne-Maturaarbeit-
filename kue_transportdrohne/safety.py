import flug_kommando

async def battery(the_connection, queue_safety):
    while True:
        battery_percentage, spannung = await queue_safety.get()
        print(f"Die Batterie beträgt {battery_percentage}%")
        battery_percentage = (spannung - 12800)/(16800 -12800)* 100 # Prozent von Lipo Batterie 0% 3.2 Volt -> sehr Niedring
        print(f"Die Spannung beträgt {spannung}")
        if battery_percentage < 35:
            print("\033[91mBATTERIE WARNUNG:\033[0m Die Landung wird in kürze eingeleitet!!")

        if battery_percentage < 30:
            flug_kommando.notfall_landung(the_connection)
            break

