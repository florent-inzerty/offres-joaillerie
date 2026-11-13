"""Collecte les offres bijoutier/joaillier (atelier) autour d'Armentières.

Sources : France Travail (inclut ses offres partenaires) et HelloWork.
Indeed est absent : il bloque les robots (challenge Cloudflare).
Usage : python3 collecte.py  -> écrit offres.js, lu par index.html.
Lancé automatiquement par GitHub Actions (.github/workflows/collecte.yml).
"""
import html
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ICI = Path(__file__).parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MOTS_CLES = ["bijoutier", "joaillier", "bijouterie", "joaillerie", "sertisseur", "polisseur bijouterie", "orfèvre"]
DEPARTEMENTS = {"59": "Nord"}  # Béthune/Lens sont à 25 km mais dans le 62 : exclus
CENTRE = (50.6886, 2.8807)  # Armentières
RAYON_KM = 30  # Hazebrouck 25, Steenvoorde 26, Cassel 29 ; Douai 38, Dunkerque 53

# Le titre doit parler du métier d'atelier : pas de vente, pas d'industrie (sertisseuses de conserverie...).
METIER = re.compile(r"bijou|joaill|sertiss|polisse|orf[èe]vr|lapidaire|ciseleu|fondeur|graveu", re.I)
EXCLURE = re.compile(r"vend|vente|commercial|conseill|boutique|magasin|caiss|manager|directeur|responsable"
                     r"|m[ée]cani|maintenance|sertisseuse|retail|marketing", re.I)


def get(url):
    time.sleep(1)  # politesse envers les sites
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def texte(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def ville(s):
    """'PARIS 2E ARRONDISSEMENT' / 'Lille (59)' -> 'Paris' / 'Lille'."""
    return re.sub(r"\s*\(.*|\s+\d.*", "", s).strip().title()


def contrat(s):
    s = s.lower()
    if re.search(r"apprenti|alternance|professionnalisation", s):
        return "Alternance"
    for c in ("CDI", "CDD", "Intérim", "Stage"):
        if c.lower() in s or (c == "Intérim" and "mis" in s):
            return c
    return "Autre"


def france_travail(mot, dep):
    offres = []
    for debut in range(0, 200, 20):  # ponytail: 10 pages max, largement assez pour ce métier
        q = urllib.parse.urlencode({"motsCles": mot, "lieux": f"{dep}D", "offresPartenaires": "true",
                                    "range": f"{debut}-{debut + 19}", "tri": "0"})
        page = get(f"https://candidat.francetravail.fr/offres/recherche?{q}")
        blocs = re.findall(r'<li data-id-offre="([^"]+)" class="result">(.*?)</li>', page, re.S)
        for id_, b in blocs:
            # "ATELIER LUCAS - <span>80 - AMIENS</span>"
            sub = re.search(r'class="subtext">(.*?)<span>(.*?)</span>', b, re.S)
            entreprise, lieu = (texte(sub.group(1)), texte(sub.group(2))) if sub else ("", "")
            m = re.match(r"(\d\w)\s*-\s*(.+)", lieu)
            offres.append({
                "id": "ft-" + id_,
                "source": "France Travail",
                "titre": texte(re.search(r'media-heading-title">(.*?)</span>', b, re.S).group(1)),
                "entreprise": entreprise.strip(" -"),
                "ville": ville(m.group(2) if m else lieu),
                "dep": m.group(1) if m else dep,
                "contrat": contrat(texte(re.search(r'class="contrat[^"]*">(.*?)</p>', b, re.S).group(1))),
                "description": texte(re.search(r'class="description">(.*?)</p>', b, re.S).group(1)),
                "date": texte(re.search(r'class="date">(.*?)</p>', b, re.S).group(1)),
                "url": f"https://candidat.francetravail.fr/offres/recherche/detail/{id_}",
            })
        if len(blocs) < 20:
            break
    return offres


def hellowork(mot, dep):
    q = urllib.parse.urlencode({"k": mot, "l": DEPARTEMENTS[dep]})
    page = get(f"https://www.hellowork.com/fr-fr/emploi/recherche.html?{q}")
    offres = []
    # aria-label : "Voir offre de TITRE à VILLE - 59, chez ENTREPRISE, pour un CDI, en temps plein"
    for id_, label in re.findall(r'href="/fr-fr/emplois/(\d+)\.html"[^>]*?aria-label="([^"]*)"', page, re.S):
        m = re.match(r"Voir offre de (.*) à (.*?) - (\d\w), chez (.*?), pour un (.*?)(?:, |$)", html.unescape(label))
        if not m:
            continue
        titre, lieu, d, entreprise, typ = m.groups()
        offres.append({
            "id": "hw-" + id_, "source": "HelloWork", "titre": titre, "entreprise": entreprise,
            "ville": ville(lieu), "dep": d, "contrat": contrat(typ), "description": "", "date": "",
            "url": f"https://www.hellowork.com/fr-fr/emplois/{id_}.html",
        })
    return offres


def geocode(offres):
    """Ajoute lat/lon via l'API publique geo.api.gouv.fr, avec un cache local."""
    f = ICI / "geocache.json"
    cache = json.loads(f.read_text()) if f.exists() else {}
    for o in offres:
        cle = f"{o['ville']}|{o['dep']}"
        if cle not in cache:
            q = urllib.parse.urlencode({"nom": o["ville"], "codeDepartement": o["dep"], "fields": "centre", "limit": 1})
            try:
                r = json.loads(get(f"https://geo.api.gouv.fr/communes?{q}"))
                cache[cle] = r[0]["centre"]["coordinates"][::-1] if r else None
            except Exception as e:
                print("géocodage raté", cle, e)
                continue
        o["coords"] = cache[cle]
    f.write_text(json.dumps(cache, ensure_ascii=False, indent=1))


def distance_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def precedentes():
    f = ICI / "offres.js"
    if not f.exists():
        return {}
    data = json.loads(re.sub(r"^window\.DATA = |;\s*$", "", f.read_text()))
    return {o["id"]: o for o in data["offres"]}


def main():
    offres = {}
    ok = 0
    for dep in DEPARTEMENTS:
        for mot in MOTS_CLES:
            for source in (france_travail, hellowork):
                try:
                    trouvees = source(mot, dep)
                except Exception as e:  # un site en panne ne doit pas tout bloquer
                    print(f"{source.__name__} {mot} {dep} : erreur {e}")
                    continue
                ok += 1
                for o in trouvees:
                    if METIER.search(o["titre"]) and not EXCLURE.search(o["titre"]):
                        # même offre publiée sur les deux sites -> une seule entrée
                        offres.setdefault((o["titre"].lower(), o["ville"].lower()), o)
                print(f"{source.__name__:15} {dep} {mot:22} {len(trouvees):3} résultats")
    if not ok:  # pas de réseau (ex. juste après le démarrage) : on garde l'ancienne liste
        raise SystemExit("aucune source joignable, offres.js inchangé")
    offres = list(offres.values())
    geocode(offres)
    # ponytail: une offre sans ville précise ("Nord") est écartée, on ne peut pas vérifier la distance
    offres = [o for o in offres if o.get("coords") and distance_km(CENTRE, o["coords"]) <= RAYON_KM]
    avant = precedentes()
    for o in offres:  # date de première apparition, pour le badge "Nouveau"
        o["vu_le"] = avant.get(o["id"], {}).get("vu_le", time.strftime("%Y-%m-%d"))
    data = {"maj": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "offres": offres}
    (ICI / "offres.js").write_text("window.DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"\n{len(offres)} offres atelier retenues -> offres.js")


if __name__ == "__main__":
    main()
