"""Génère zone.js : le cercle de recherche découpé aux limites du Nord (sans Belgique ni Pas-de-Calais).

À relancer seulement si CENTRE ou RAYON_KM changent dans collecte.py : python3 zone.py
"""
import json
import math
import urllib.request

from collecte import CENTRE, RAYON_KM, ICI

NORD = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements/59-nord/departement-59-nord.geojson"


def cercle(n=180):
    lat, lon = CENTRE
    dlat = RAYON_KM / 111.32
    dlon = dlat / math.cos(math.radians(lat))
    return [(lon + dlon * math.cos(2 * math.pi * i / n), lat + dlat * math.sin(2 * math.pi * i / n)) for i in range(n)]


def decoupe(poly, fenetre):
    """Sutherland-Hodgman : garde la partie de poly dans fenetre (convexe, sens anti-horaire)."""
    for (ax, ay), (bx, by) in zip(fenetre, fenetre[1:] + fenetre[:1]):
        dedans = lambda p: (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) >= 0
        entree, poly = poly, []
        for p, q in zip(entree, entree[1:] + entree[:1]):
            if dedans(q):
                if not dedans(p):
                    poly.append(inter(p, q, (ax, ay), (bx, by)))
                poly.append(q)
            elif dedans(p):
                poly.append(inter(p, q, (ax, ay), (bx, by)))
        if not poly:
            break
    return poly


def inter(p, q, a, b):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p, q, a, b
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / ((x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4))
    return x1 + t * (x2 - x1), y1 + t * (y2 - y1)


def main():
    req = urllib.request.Request(NORD, headers={"User-Agent": "zone.py"})
    geo = json.load(urllib.request.urlopen(req, timeout=30))["geometry"]
    polys = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
    zone = [decoupe([tuple(p) for p in poly[0]], cercle()) for poly in polys]
    zone = [[[round(y, 5), round(x, 5)] for x, y in z] for z in zone if len(z) > 2]  # Leaflet : [lat, lon]
    (ICI / "zone.js").write_text("window.ZONE = " + json.dumps(zone) + ";\n")
    print(f"zone.js : {len(zone)} morceau(x), {sum(map(len, zone))} points")


if __name__ == "__main__":
    main()
