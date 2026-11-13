# Offres bijouterie-joaillerie autour d'Armentières

Page personnelle qui liste les offres d'emploi de **bijoutier·ère / joaillier·ère en atelier** (pas de vente)
dans un rayon de 30 km autour d'Armentières, côté France uniquement.

## D'où viennent les offres

| Source | Adresse interrogée | Ce qu'elle apporte |
|---|---|---|
| **France Travail** | `candidat.francetravail.fr/offres/recherche` (département 59, « offres partenaires » incluses) | Ses propres offres **et** celles de ses sites partenaires. Chaque offre affiche son vrai site d'origine, par exemple « TalentPlug via France Travail », « HelloWork via France Travail » ou « Skello via France Travail ». |
| **HelloWork** | `hellowork.com/fr-fr/emploi/recherche.html` (lieu : Nord) | Les offres publiées directement sur HelloWork. |

**Mots-clés cherchés** (sur chaque source) : bijoutier, joaillier, bijouterie, joaillerie, sertisseur,
polisseur bijouterie, orfèvre.

**Tri appliqué ensuite :**
- le titre doit parler du métier (bijou, joaill, sertiss, polisse, orfèvre, lapidaire, ciseleur, fondeur, graveur) ;
- les postes de vente, de commerce, de management et d'industrie (« mécanicien sertisseur », etc.) sont écartés ;
- la ville doit être dans le Nord (59) et à 30 km maximum d'Armentières : Hazebrouck, Bailleul, Steenvoorde,
  Cassel, toute la métropole lilloise… mais pas la Belgique, ni Béthune, Lens ou Arras (Pas-de-Calais),
  ni Douai ou Dunkerque (trop loin) ;
- une même offre publiée sur les deux sites n'apparaît qu'une fois.

**Pas couverts :**
- **Indeed** : le site bloque les robots (contrôle anti-robot Cloudflare). Pour Indeed, une alerte e-mail sur leur site reste le plus simple.
- **LinkedIn** : il faut être connecté, et la collecte automatique y est interdite.
- **Pages carrières des maisons de joaillerie, Apec, Welcome to the Jungle** : non branchés, à ajouter au besoin.

## Tous les combien ça se met à jour

La collecte tourne toute seule sur les serveurs de GitHub (GitHub Actions), **toutes les 3 heures, 6 fois par jour** :

| | Heures (heure de Paris) |
|---|---|
| Hiver | 6 h, 9 h, 12 h, 15 h, 18 h, 21 h |
| Été | 7 h, 10 h, 13 h, 16 h, 19 h, 22 h |

- GitHub lance souvent ces tâches avec **quelques minutes à une demi-heure de retard** quand ses serveurs sont chargés.
- Une collecte prend moins d'une minute : une vingtaine de pages consultées, une par seconde.
- Ton ordinateur n'a pas besoin d'être allumé.
- **Quand tu ouvres la page**, elle recharge toujours la dernière liste, jamais une version en cache. En haut, « vérifié il y a X » indique l'heure de la dernière collecte.
- Une offre reste marquée **Nouveau** pendant 3 jours après sa première apparition.
- Une offre retirée du site d'origine disparaît de la page à la collecte suivante.
- Pour forcer une collecte : onglet **Actions** du dépôt → « Collecte des offres » → **Run workflow**.
- GitHub met en pause les tâches planifiées d'un dépôt public resté 60 jours sans activité. Il prévient alors par e-mail, et un clic dans l'onglet Actions les relance.

## Annuaire des ateliers (bouton « Ateliers »)

Pour les candidatures spontanées : les ateliers et bijouteries de la même zone, chaînes comprises.

| Source | Ce qu'elle apporte |
|---|---|
| **Registre national des entreprises** (`recherche-entreprises.api.gouv.fr`, données publiques de l'État) | Les établissements actifs déclarés **32.12Z** (fabrication de bijoux, les ateliers) ou **47.77Z** (bijouteries-horlogeries), avec la tranche de salariés. Les personnes qui ont refusé la diffusion de leurs données sont exclues. |
| **OpenStreetMap** (API Overpass) | Site web, téléphone et e-mail quand ils sont renseignés, plus quelques boutiques absentes du registre. |

- **Contenu** : environ 150 lieux, dont 30 ateliers de fabrication. Une quarantaine de lieux ont un site web, une trentaine un téléphone, et seulement quelques-uns un e-mail.
- **Mise à jour** : **chaque lundi** vers 5 h (6 h en été), car un annuaire change peu.
- **Bouton « Marquer comme contacté »** : il enregistre la date sur l'appareil utilisé. Ce que tu coches sur ton téléphone n'apparaît donc pas sur ton ordinateur, et inversement. Vider les données du navigateur efface aussi ces marques.

## Fichiers

- `index.html` : la page (carte + liste).
- `collecte.py` : la collecte. La zone (`CENTRE`, `RAYON_KM`) et les mots-clés (`MOTS_CLES`) se règlent en haut du fichier.
- `offres.js` : les offres trouvées, réécrites à chaque collecte.
- `zone.py` → `zone.js` : le contour de la zone sur la carte. À relancer seulement si la zone change.
- `ateliers.py` → `ateliers.js` : l'annuaire des ateliers et bijouteries.
- `.github/workflows/collecte.yml` (offres, toutes les 3 h) et `ateliers.yml` (annuaire, le lundi) : la planification.
