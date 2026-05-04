from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.cluster import KMeans
import requests
import time

app = Flask(__name__)
CORS(app)

def geocode(postcode):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={postcode}"
    response = requests.get(url).json()
    if response:
        return float(response[0]["lat"]), float(response[0]["lon"])
    return None

def get_osrm_route(coords):
    coord_str = ";".join([f"{lng},{lat}" for lat, lng in coords])
    url = f"http://router.project-osrm.org/trip/v1/driving/{coord_str}?roundtrip=false&source=first"
    res = requests.get(url).json()
    if res.get("trips"):
        return res["trips"][0]
    return None

@app.route("/optimize", methods=["POST"])
def optimize():
    data = request.json
    postcodes = data["postcodes"]
    drivers = int(data["drivers"])

    coords = []
    valid = []

    for pc in postcodes:
        loc = geocode(pc)
        time.sleep(1)
        if loc:
            coords.append(loc)
            valid.append(pc)

    if len(coords) < drivers:
        return jsonify({"error": "Not enough valid locations"})

    kmeans = KMeans(n_clusters=drivers, random_state=0).fit(coords)
    labels = kmeans.labels_

    clusters = {}

    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append({
            "postcode": valid[i],
            "lat": coords[i][0],
            "lng": coords[i][1]
        })

    final_routes = []

    for driver, points in clusters.items():
        coords_list = [(p["lat"], p["lng"]) for p in points]
        route = get_osrm_route(coords_list)

        if route:
            final_routes.append({
                "driver": int(driver),
                "geometry": route["geometry"],
                "points": points
            })

    return jsonify(final_routes)

if __name__ == "__main__":
    app.run()
