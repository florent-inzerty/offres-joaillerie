"""Annuaire des ateliers et bijouteries de la zone, pour les candidatures spontanées.

Sources :
- registre national des entreprises (recherche-entreprises.api.gouv.fr) : codes NAF 32.12Z (fabrication
  de bijoux, les ateliers) et 47.77Z (bijouteries-horlogeries), établissements actifs du Nord ;
- OpenStreetMap (API Overpass) : site web, téléphone, e-mail, et quelques boutiques absentes du registre.
Usage : python3 ateliers.py  -> écrit ateliers.js. Lancé chaque semaine par GitHub Actions.
"""
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request

from collecte import CENTRE, ICI, RAYON_KM, distance_km, get

NAF = {"32.12Z": "Atelier", "47.77Z": "Bijouterie"}
SALARIES = {"00": "0 salarié", "01": "1 ou 2 salariés", "02": "3 à 5 salariés", "03": "6 à 9 salariés",
            "11": "10 à 19 salariés", "12": "20 à 49 salariés", "21": "50 à 99 salariés", "22": "100 à 199 salariés"}
ZONE = json.loads(re.sub(r"^window\.ZONE = |;\s*$", "", (ICI / "zone.js").read_text()))


def dans_zone(lat, lon):
    """Point dans le contour (cercle de 30 km découpé aux limites du Nord) ?"""
    dedans = False
    for poly in ZONE:
        for (a, b), (c, d) in zip(poly, poly[1:] + poly[:1]):
            if (a > lat) != (c > lat) and lon < (d - b) * (lat - a) / (c - a) + b:
                dedans = not dedans
    return dedans


VIDES = {"bijouterie", "bijoux", "bijou", "horlogerie", "joaillerie", "joaillier", "sarl", "maison", "atelier", "france",
         "lille", "roubaix", "tourcoing"}


def mots(nom):
    nom = unicodedata.normalize("NFD", (nom or "").lower()).encode("ascii", "ignore").decode()
    return {m for m in re.findall(r"[a-z]{4,}", nom) if m not in VIDES}


def joli(nom):
    nom = re.sub(r"\s+", " ", nom or "").strip()
    return nom.title() if nom.isupper() else nom


def reessayer(url, fois=5):
    """Les API publiques renvoient parfois 502/503/504 quelques minutes : on patiente et on recommence."""
    for essai in range(fois):
        try:
            return get(url)
        except OSError as e:
            if essai == fois - 1:
                raise
            print("indisponible, nouvel essai dans 30 s :", e)
            time.sleep(30)


COMMUNES = {}


def nom_commune(code):
    """Le registre écrit ARMENTIERES : on prend le nom officiel avec accents (Armentières)."""
    if code and code not in COMMUNES:
        try:
            COMMUNES[code] = json.loads(reessayer(f"https://geo.api.gouv.fr/communes/{code}?fields=nom"))["nom"]
        except (OSError, KeyError, ValueError):
            COMMUNES[code] = None
    return COMMUNES.get(code)


def registre():
    lieux = {}
    for naf, type_ in NAF.items():
        page = 1
        while True:
            q = urllib.parse.urlencode({"activite_principale": naf, "departement": "59", "etat_administratif": "A",
                                        "per_page": 25, "page": page})
            d = json.loads(reessayer(f"https://recherche-entreprises.api.gouv.fr/search?{q}"))
            for ent in d["results"]:
                if "NON-DIFFUSIBLE" in (ent.get("nom_complet") or ""):
                    continue  # la personne a refusé la diffusion de ses données
                for e in ent.get("matching_etablissements", []):
                    try:
                        lat, lon = float(e["latitude"]), float(e["longitude"])
                    except (TypeError, ValueError, KeyError):
                        continue
                    if e.get("etat_administratif") != "A" or not dans_zone(lat, lon):
                        continue
                    enseigne = (e.get("liste_enseignes") or [None])[0] or e.get("nom_commercial")
                    nom = enseigne or re.sub(r"\s*\(.*\)$", "", ent["nom_complet"])
                    lieux[e["siret"]] = {
                        "id": e["siret"], "nom": joli(nom), "type": type_,
                        "chaine": (ent.get("nombre_etablissements_ouverts") or 1) > 3,
                        "ville": nom_commune(e.get("commune")) or joli(e.get("libelle_commune")), "adresse": e.get("adresse"),
                        "coords": [round(lat, 5), round(lon, 5)],
                        "salaries": SALARIES.get(e.get("tranche_effectif_salarie")),
                        "site": None, "tel": None, "mail": None,
                    }
            if page >= d["total_pages"]:
                break
            page += 1
    return lieux


def osm():
    lat, lon = CENTRE
    q = (f'[out:json][timeout:60];(nwr["shop"="jewelry"](around:{RAYON_KM * 1000},{lat},{lon});'
         f'nwr["craft"~"jeweller|goldsmith"](around:{RAYON_KM * 1000},{lat},{lon}););out center tags;')
    for essai in range(6):  # serveurs publics souvent surchargés : on alterne deux miroirs
        url = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")[essai % 2]
        req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(),
                                     headers={"User-Agent": "offres-joaillerie (annuaire personnel)"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)["elements"]
        except OSError as e:
            print("OpenStreetMap indisponible", url, e)
            time.sleep(20)
    raise SystemExit("OpenStreetMap injoignable, ateliers.js inchangé")


def main():
    lieux = registre()
    print(f"registre : {len(lieux)} établissements dans la zone")
    ajoutes = completes = 0
    for el in osm():
        t = el["tags"]
        lat, lon = (el["lat"], el["lon"]) if "lat" in el else (el["center"]["lat"], el["center"]["lon"])
        if not dans_zone(lat, lon):
            continue
        infos = {"site": t.get("website") or t.get("contact:website"),
                 "tel": t.get("phone") or t.get("contact:phone"),
                 "mail": t.get("email") or t.get("contact:email")}
        # même établissement : même SIRET ; sinon un nom en commun à moins de 300 m ;
        # sinon le plus proche à moins de 30 m (dans un centre commercial, les boutiques sont collées)
        lieu = lieux.get(t.get("ref:FR:SIRET", "").replace(" ", ""))
        if not lieu:
            d = lambda l: distance_km(l["coords"], (lat, lon))
            noms = mots(t.get("name")) | mots(t.get("brand"))
            proches = sorted((l for l in lieux.values() if d(l) < 0.3), key=d)
            lieu = next((l for l in proches if noms & mots(l["nom"])), None) or \
                next((l for l in proches if d(l) < 0.03), None)
        if lieu:
            lieu.update({k: v for k, v in infos.items() if v})
            completes += 1
        else:
            lieux[f"osm-{el['id']}"] = {
                "id": f"osm-{el['id']}", "nom": t.get("name") or t.get("brand") or "Bijouterie",
                "type": "Atelier" if "craft" in t else "Bijouterie", "chaine": "brand" in t,
                "ville": t.get("addr:city") or t.get("contact:city") or "", "adresse": None,
                "coords": [round(lat, 5), round(lon, 5)], "salaries": None, **infos,
            }
            ajoutes += 1
    print(f"OpenStreetMap : {completes} complétés, {ajoutes} ajoutés")
    for l in lieux.values():
        if not l["ville"]:  # boutiques venues d'OpenStreetMap sans adresse : commune d'après la position
            q = urllib.parse.urlencode({"lat": l["coords"][0], "lon": l["coords"][1], "fields": "nom"})
            r = json.loads(reessayer(f"https://geo.api.gouv.fr/communes?{q}"))
            l["ville"] = r[0]["nom"] if r else ""
    # Doublons : même nom à moins de 150 m (ex. plusieurs sociétés Lepage déclarées à la même adresse)
    gardes = []
    for l in sorted(lieux.values(), key=lambda l: -sum(bool(l[k]) for k in ("site", "tel", "mail", "salaries"))):
        double = next((g for g in gardes if mots(g["nom"]) & mots(l["nom"])
                       and distance_km(g["coords"], l["coords"]) < 0.15), None)
        if double:
            double.update({k: v for k, v in l.items() if v and not double.get(k)})
        else:
            gardes.append(l)
    lieux = {l["id"]: l for l in gardes}
    for l in lieux.values():
        l["km"] = round(distance_km(CENTRE, l["coords"]))
    data = {"maj": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
            "liste": sorted(lieux.values(), key=lambda l: (l["km"], l["nom"]))}
    (ICI / "ateliers.js").write_text("window.ATELIERS = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"{len(lieux)} lieux -> ateliers.js")


if __name__ == "__main__":
    main()
