from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

df = pd.read_csv("C:/Users/loick/OneDrive/Desktop/grand_projet/backend/fichier.csv")

df["ville_successeurs"] = df["ville_successeurs"].apply(lambda x: x.split(','))
df["temps_trajet_normal"] = df["temps_trajet_normal"].apply(lambda x: list(map(float, x.split(','))))

# Calcul de la distance à vol d'oiseau (distance Euclidienne) entre deux points géographiques
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c  # Résultat en kilomètres
    return distance

# Récupère des données en temps réel venant de l'API HERE
def realTime(lat_dep, long_dep, lat_arr, long_arr):
    api_key = 'JvfJVgKEZXF8mhwMiSuugER1uaWGM7nvstLhPAzd0IY'
    url = 'https://router.hereapi.com/v8/routes'
    params = {
        'origin': f'{lat_dep},{long_dep}',
        'destination': f'{lat_arr},{long_arr}',
        'transportMode': 'car',
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        departure_time = data['routes'][0]['sections'][0]['departure']['time']
        arrival_time = data['routes'][0]['sections'][0]['arrival']['time']

        # Convertir les temps en objets datetime
        departure_dt = datetime.fromisoformat(departure_time)
        arrival_dt = datetime.fromisoformat(arrival_time)

        # Calculer la durée du trajet
        duration = arrival_dt - departure_dt
        duration_minutes = duration.total_seconds() / 60

        return duration_minutes

    except Exception as e:
        print(f"Erreur lors de la requête API HERE: {e}")
        return None

def find_Suc(df, ville_depart):        
    successeurs = df[df['ville_depart']==ville_depart]['ville_successeurs']

    if not successeurs.empty:
        villes_successeurs = successeurs.iloc[0]
        return villes_successeurs
    else:
        print(f"{ville_depart} n'existe pas ")

def find_normal_traject(df, ville_depart):
    normal_traject = df[df['ville_depart']==ville_depart]['temps_trajet_normal']
    if not normal_traject.empty:
        return normal_traject.iloc[0]  
    else:
        print(f"{ville_depart} n'existe pas ")

def insert_value(df, ville_depart, ville_arrive, closedSet):
    dictionnaire = dict()
    successeurs = find_Suc(df, ville_depart)
    temps_normaux = find_normal_traject(df, ville_depart)

    if len(successeurs) == len(temps_normaux):
        for ville_suc, temps_normal in zip(successeurs, temps_normaux):
            if ville_suc in closedSet or ville_suc == ville_depart:
                continue

            lat_dep = df[df['ville_depart'] == ville_depart]["latitude"].values[0]
            long_dep = df[df['ville_depart'] == ville_depart]["longitude"].values[0]
            lat_arr = df[df['ville_depart'] == ville_arrive]["latitude"].values[0]
            long_arr = df[df['ville_depart'] == ville_arrive]["longitude"].values[0]

            real_time_duration = realTime(lat_dep, long_dep, lat_arr, long_arr)
            if real_time_duration is not None:
                g_n = temps_normal + real_time_duration

                lat_ville_suc = df[df['ville_depart'] == ville_suc]["latitude"].values[0]
                long_ville_suc = df[df['ville_depart'] == ville_suc]["longitude"].values[0]
                h_n = haversine(lat_ville_suc, long_ville_suc, lat_arr, long_arr)

                dictionnaire[ville_suc] = [g_n + h_n]
            else:
                print(f"Durée non disponible pour {ville_depart} -> {ville_suc}, API renvoie None.")
    else:
        print(f"Problème avec les données pour {ville_depart}. Successeurs et trajets ne correspondent pas.")

    return dictionnaire

def main_2(df, ville_depart, ville_arrive):
    openSet = {ville_depart: 0}
    closedSet = []

    while openSet:
        current_ville = min(openSet, key=openSet.get)
        print(f"Ville actuelle : {current_ville}")

        if current_ville == ville_arrive:
            print("Arrivée atteinte.")
            closedSet.append(current_ville)
            print("État final de closedSet :")
            print(closedSet)
            return closedSet

        del openSet[current_ville]
        closedSet.append(current_ville)

        temp_value = insert_value(df, current_ville, ville_arrive, closedSet)
        
        for ville_suc, f_n in temp_value.items():
            if ville_suc in closedSet:
                continue

            if ville_suc not in openSet or f_n[0] < openSet[ville_suc]:
                openSet[ville_suc] = f_n[0]

    print("Boucle terminée. État final de closedSet :")
    print(closedSet)
    return closedSet

def lat_dep(df,result):
    values = dict()
    for v in result:
        values[v] = df['ville_depart'==v]['latitude']
    return values

def lat_dep(df,result):
    dictionnaire = []
    for v in result:
        ligne = df[df['ville_depart'] == v]
        dictionnaire.append([ligne['latitude'].values[0],ligne['longitude'].values[0]])
    return dictionnaire

# Exécution du code
@app.route('/route', methods=['GET'])
def get_route():
    start_city = request.args.get('start_city')
    end_city = request.args.get('end_city')

    if not start_city or not end_city:
        return jsonify({"error": "Missing parameters"}), 400

    result = main_2(df, start_city, end_city)
    coordinates = lat_dep(df, result)
    return jsonify(coordinates)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)