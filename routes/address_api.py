from flask import Blueprint, jsonify
import json
import os

address_api = Blueprint("address_api", __name__)

BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "data")

with open(os.path.join(BASE_PATH, "ilceler.json"), encoding="utf-8") as f:
    ilceler = json.load(f)

with open(os.path.join(BASE_PATH, "mahalleler.json"), encoding="utf-8") as f:
    mahalleler = json.load(f)

# İlçeleri döndür
@address_api.route("/api/districts/<int:sehir_id>")
def get_districts(sehir_id):
    results = [i for i in ilceler if i["sehir_id"] == sehir_id]
    return jsonify(results)

# Mahalleleri döndür
@address_api.route("/api/neighborhoods/<int:ilce_id>")
def get_neighborhoods(ilce_id):
    results = [m for m in mahalleler if m["ilce_id"] == str(ilce_id)]
    return jsonify(results)

address_api = Blueprint("address_api", __name__)

BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "data")

with open(os.path.join(BASE_PATH, "ilceler.json"), encoding="utf-8") as f:
    ilceler = json.load(f)

with open(os.path.join(BASE_PATH, "mahalleler.json"), encoding="utf-8") as f:
    mahalleler = json.load(f)

@address_api.route("/api/districts/<int:sehir_id>")
def get_districts(sehir_id):
    results = [i for i in ilceler if i["sehir_id"] == str(sehir_id)]
    return jsonify(results)

@address_api.route("/api/neighborhoods/<int:ilce_id>")
def get_neighborhoods(ilce_id):
    results = [m for m in mahalleler if m["ilce_id"] == str(ilce_id)]
    return jsonify(results)