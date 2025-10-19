import itertools
from math import sin, cos, atan2, sqrt, radians
import ast
import os


optionen = []
distanzen = []
# Koordinaten von Firma, bei der die Drohne das zu liefernde Paket auflädt -> Startpunkt der Drohne (Beispielsweise)
start_lat = 52.5200 
start_lon = 13.4050
start_cor = (start_lat, start_lon)

#Besipiel Koordinaten für Test (erstellt von ChatGPT)
coordinates = [
    (48.8566, 2.3522),   
    (40.7128, -74.0060),  
    (35.6895, 139.6917),  
    (-33.8688, 151.2093), 
    (55.7558, 37.6173),  
    (51.5074, -0.1278),  
    (34.0522, -118.2437),
    (19.4326, -99.1332),  
    (-23.5505, -46.6333), 
    (31.2304, 121.4737),  
    (28.6139, 77.2090),   
    (43.6532, -79.3832), 
    (1.3521, 103.8198),   
    (37.7749, -122.4194), 
    (41.9028, 12.4964)   
]

#mit Hilfe von ChatGPT gemacht von hier bis (liest die Wegstrecke (Missionspunkte) aus waypoints.txt)
input_file = os.path.expanduser("~/maturaarbeit/final_test/waypoints.txt")

coordinates = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue  # überspringt leere oder ungültige Zeilen

        try:
            row = ast.literal_eval(line)  # sicherer als eval
            if "lat" in row and "lon" in row:
                coordinates.append((row["lat"], row["lon"]))  # (lon, lat)
        except Exception as e:
            print(f"⚠️ Fehler in Zeile: {line[:60]}... -> {e}")
#hier
print("Koordinatenliste:", coordinates)

mission_points = len(coordinates)
if mission_points < 6: # Bei so einer kleinen Menge können wir Brutforceing anwenden! Das wird immer den kürzesten Weg zurückgeben            
    for p in itertools.permutations(coordinates):
        flug = [start_cor] + list(p) + [start_cor]
        optionen.append(flug)
        total_distance = 0
        for i in range(len(flug)-1):
            lat1 = flug[i][0]
            lon1 = flug[i][1]
            lat2 = flug[i+1][0]
            lon2 = flug[i+1][1]
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dLat = lat2-lat1
            dLon = lon2-lon1
            a = pow(sin(dLat/2.0), 2) + pow(sin(dLon/2.0), 2) * cos(lat1) * cos(lat2)
            dist = 6378.388 * 2.0 * atan2(sqrt(a), sqrt(1.0-a))
            total_distance += dist 
        distanzen.append(total_distance)

    min_dis = min(distanzen)
    min_pos = distanzen.index(min_dis)
    max_dis = max(distanzen)
    max_pos = distanzen.index(max_dis)
    print(f"Die kleinste Distanz beträgt {min_dis}")
    print(optionen[min_pos])
    print(f"Die kleinste Distanz beträgt {max_dis}")
    print(optionen[max_pos])

else: # ansonsten wird die Strecke so berechnet, dass die Drohne immer zur nächstliegensten 
    #Koordinate fliegt -> das führt meistens auch zum kürzesten Weg und benötigt bei grossen 
    # Mengen deutlich weniger Rechenleistung. 
    position = {
        "lat": start_lat,
        "lon": start_lon
    }
    flug_missions_coordinaten = []
    for i in range(mission_points):
        distanzen_liste = []
        for coordinate in coordinates:
            lat1 = position["lat"]
            lon1 = position["lon"]
            lat2 = coordinate[0]
            lon2 = coordinate[1]
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dLat = lat2-lat1
            dLon = lon2-lon1
            a = pow(sin(dLat/2.0), 2) + pow(sin(dLon/2.0), 2) * cos(lat1) * cos(lat2)
            dist = 6378.388 * 2.0 * atan2(sqrt(a), sqrt(1.0-a))
            distanzen_liste.append(dist)
        min_distance = min(distanzen_liste)
        min_pos = distanzen_liste.index(min_distance)
        next_cor = coordinates[min_pos]
        flug_missions_coordinaten.append(next_cor)
        position["lat"] = next_cor[0]
        position["lon"] = next_cor[1]
        coordinates.remove(next_cor)

    print("Die Koordinaten von der kürzesten Flugstrecke lauten: ", flug_missions_coordinaten)
        


    


    