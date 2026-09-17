"""Personnalités de nationalité française décédées, année par année, via Wikidata.

    uv run python -m scripts.collecte_personnalites                     # 1990 → 2025
    uv run python -m scripts.collecte_personnalites --debut 2020 --fin 2025
    uv run python -m scripts.collecte_personnalites --force             # ignore le cache

Collecte longue (plus d'une demi-heure) : elle n'est pas lancée par
`refresh_data`, qui importe son résultat.

Deux étapes :

1. Collecte : une requête SPARQL par année, mise en cache dans
   `data/personnalites/brut/`.
   Une année déjà collectée n'est pas redemandée, ce qui permet de reprendre
   après une interruption.
2. Consolidation : toutes les années sont fusionnées en un seul fichier, avec
   une ligne par personne et une date retenue par personne.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import unquote

import requests

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = (
    "deces-personnalites-fr/0.1 "
    "(projet personnel d'analyse ; une requête par période, espacées)"
)
TIMEOUT_S = 90
PAUSE_S = 2.0
TENTATIVES = 3

DOSSIER = Path(__file__).resolve().parent.parent / "data" / "personnalites"
DOSSIER_BRUT = DOSSIER / "brut"

# Précision Wikidata : 11 = jour, 10 = mois, 9 = année, 8 = décennie, 7 = siècle.
PRECISIONS = {11: "jour", 10: "mois", 9: "année", 8: "décennie", 7: "siècle"}

# Rang Wikidata : une déclaration « préférée » l'emporte sur une « normale ».
RANGS = {"PreferredRank": 2, "NormalRank": 1}

COLONNES_BRUT = [
    "wikidata_id", "nom", "deces", "deces_precision", "deces_rang",
    "naissance", "naissance_precision", "naissance_rang",
    "nb_editions_wikipedia", "article_wikipedia_fr",
]


class RequeteTropLongue(RuntimeError):
    """Le service a coupé la requête : la période doit être découpée."""


# ---------------------------------------------------------------------------
# Collecte
# ---------------------------------------------------------------------------

def requete_sparql(debut: date, fin: date) -> str:
    """Décès survenus dans [debut, fin[ de personnes de nationalité française.

    Seules comptent les personnes ayant au moins un article Wikipédia, dans
    n'importe quelle langue : sans ce filtre, environ un tiers des lignes sont
    de simples fiches Wikidata, pas des personnalités publiques.

    La nationalité (P27 = France) inclut les doubles nationaux. Les
    déclarations dépréciées sont écartées, les autres sont toutes remontées
    avec leur rang et leur précision : le choix de la date se fait ensuite.
    """
    return f"""
SELECT ?p ?pLabel ?deces ?precD ?rangD ?naissance ?precN ?rangN ?liens ?article WHERE {{
  ?p wdt:P27 wd:Q142 ; wikibase:sitelinks ?liens .
  FILTER(?liens >= 1)
  ?p p:P570 ?sd .
  ?sd psv:P570 [ wikibase:timeValue ?deces ; wikibase:timePrecision ?precD ] ;
      wikibase:rank ?rangD .
  FILTER(?deces >= "{debut.isoformat()}T00:00:00Z"^^xsd:dateTime
      && ?deces <  "{fin.isoformat()}T00:00:00Z"^^xsd:dateTime)
  FILTER(?rangD != wikibase:DeprecatedRank)
  ?p wdt:P31 wd:Q5 .
  OPTIONAL {{
    ?p p:P569 ?sn .
    ?sn psv:P569 [ wikibase:timeValue ?naissance ; wikibase:timePrecision ?precN ] ;
        wikibase:rank ?rangN .
    FILTER(?rangN != wikibase:DeprecatedRank)
  }}
  OPTIONAL {{ ?article schema:about ?p ; schema:isPartOf <https://fr.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}}"""


def interroger(debut: date, fin: date) -> list[dict]:
    """Exécute la requête, avec reprises sur les erreurs transitoires."""
    for tentative in range(1, TENTATIVES + 1):
        try:
            r = requests.get(
                ENDPOINT,
                params={"query": requete_sparql(debut, fin)},
                headers={"User-Agent": USER_AGENT,
                         "Accept": "application/sparql-results+json"},
                timeout=TIMEOUT_S,
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            # Le service ferme la connexion sans réponse quand la requête
            # dépasse sa limite : inutile de réessayer à l'identique.
            raise RequeteTropLongue(str(e)) from e

        if r.status_code == 200:
            try:
                return r.json()["results"]["bindings"]
            except ValueError as e:
                # Le service peut répondre 200 puis couper le flux quand il
                # atteint sa limite de temps : le JSON arrive tronqué. C'est le
                # même dépassement qu'un 504, sous une autre forme.
                raise RequeteTropLongue(f"réponse tronquée ({e})") from e
        if r.status_code in (500, 504) or "timeout" in r.text[:500].lower():
            raise RequeteTropLongue(f"HTTP {r.status_code}")
        if r.status_code == 429 and tentative < TENTATIVES:
            attente = int(r.headers.get("Retry-After", 30))
            print(f"      limite de débit atteinte, pause {attente} s", flush=True)
            time.sleep(attente)
            continue
        if r.status_code >= 500 and tentative < TENTATIVES:
            time.sleep(10 * tentative)
            continue
        raise RuntimeError(f"Wikidata : HTTP {r.status_code} — {r.text[:300]}")
    raise RuntimeError("Wikidata : tentatives épuisées")


def milieu(debut: date, fin: date) -> date:
    return date.fromordinal((debut.toordinal() + fin.toordinal()) // 2)


def collecter_periode(debut: date, fin: date, profondeur: int = 0) -> list[dict]:
    """Collecte une période, en la coupant en deux tant qu'elle est trop lourde."""
    marge = "   " + "  " * profondeur
    try:
        lignes = interroger(debut, fin)
        print(f"{marge}{debut} → {fin} : {len(lignes)} lignes", flush=True)
        time.sleep(PAUSE_S)
        return lignes
    except RequeteTropLongue:
        if (fin - debut).days <= 7:
            raise RuntimeError(f"période {debut} → {fin} toujours trop lourde") from None
        m = milieu(debut, fin)
        print(f"{marge}{debut} → {fin} : trop lourd, découpage en deux", flush=True)
        time.sleep(PAUSE_S * 2)
        return (collecter_periode(debut, m, profondeur + 1)
                + collecter_periode(m, fin, profondeur + 1))


def valeur(b: dict, cle: str) -> str:
    return b.get(cle, {}).get("value", "")


def rang(uri: str) -> str:
    return uri.rsplit("#", 1)[-1] if uri else ""


def collecter_annee(annee: int, force: bool) -> Path:
    chemin = DOSSIER_BRUT / f"deces_{annee}.csv"
    if chemin.exists() and not force:
        print(f"{annee} : déjà collectée (cache)", flush=True)
        return chemin

    print(f"{annee} :", flush=True)
    lignes = collecter_periode(date(annee, 1, 1), date(annee + 1, 1, 1))

    DOSSIER_BRUT.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".tmp")
    with temporaire.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLONNES_BRUT)
        for b in lignes:
            w.writerow([
                valeur(b, "p").rsplit("/", 1)[-1],
                valeur(b, "pLabel"),
                valeur(b, "deces"), valeur(b, "precD"), rang(valeur(b, "rangD")),
                valeur(b, "naissance"), valeur(b, "precN"), rang(valeur(b, "rangN")),
                valeur(b, "liens"),
                valeur(b, "article"),
            ])
    # Écriture atomique : un cache n'existe que s'il est complet.
    temporaire.replace(chemin)
    return chemin


# ---------------------------------------------------------------------------
# Sexe
# ---------------------------------------------------------------------------

FICHIER_SEXE = DOSSIER_BRUT / "sexe.csv"
SEXES = {"Q6581097": "homme", "Q6581072": "femme"}
LOT_SEXE = 200


def collecter_sexes(identifiants: set[str]) -> dict[str, str]:
    """Sexe (P21) de chaque personne, par lots, avec cache incrémental.

    Récupéré à part plutôt que dans la requête annuelle : l'y ajouter
    alourdirait des requêtes déjà à la limite du temps autorisé, et obligerait
    à recollecter toutes les années.
    """
    connus: dict[str, str] = {}
    if FICHIER_SEXE.exists():
        with FICHIER_SEXE.open(encoding="utf-8") as f:
            connus = {l["wikidata_id"]: l["sexe"] for l in csv.DictReader(f)}

    manquants = sorted(identifiants - connus.keys())
    if manquants:
        print(f"Sexe : {len(manquants)} personnes à compléter", flush=True)
    for i in range(0, len(manquants), LOT_SEXE):
        lot = manquants[i:i + LOT_SEXE]
        connus.update(_sexes_du_lot(lot))
        # Sauvegarde après chaque lot : une erreur au 100e lot ne doit pas
        # faire perdre les 99 précédents.
        _ecrire_sexes(connus)
        if (i // LOT_SEXE) % 20 == 0:
            print(f"   {min(i + LOT_SEXE, len(manquants))}/{len(manquants)}", flush=True)
        time.sleep(PAUSE_S)
    return connus


def _sexes_du_lot(lot: list[str]) -> dict[str, str]:
    valeurs = " ".join(f"wd:{q}" for q in lot)
    requete = f"SELECT ?p ?s WHERE {{ VALUES ?p {{ {valeurs} }} OPTIONAL {{ ?p wdt:P21 ?s }} }}"
    motif = ""
    for tentative in range(1, TENTATIVES + 2):
        try:
            r = requests.get(ENDPOINT, params={"query": requete},
                             headers={"User-Agent": USER_AGENT,
                                      "Accept": "application/sparql-results+json"},
                             timeout=TIMEOUT_S)
            if r.status_code == 200:
                trouves: dict[str, str] = dict.fromkeys(lot, "")
                for b in r.json()["results"]["bindings"]:
                    q = valeur(b, "p").rsplit("/", 1)[-1]
                    s = valeur(b, "s").rsplit("/", 1)[-1]
                    # Plusieurs valeurs possibles : une valeur connue l'emporte sur le vide.
                    trouves[q] = trouves[q] or SEXES.get(s, "autre" if s else "")
                return trouves
            motif = f"HTTP {r.status_code}"
            attente = int(r.headers.get("Retry-After", 15 * tentative))
        except (requests.RequestException, ValueError) as e:
            motif = type(e).__name__
            attente = 15 * tentative
        if tentative <= TENTATIVES:
            print(f"      lot sexe : {motif}, nouvelle tentative dans {attente} s", flush=True)
            time.sleep(attente)
    raise RuntimeError(f"Wikidata (sexe) : {motif} après {TENTATIVES + 1} tentatives")


def _ecrire_sexes(connus: dict[str, str]) -> None:
    DOSSIER_BRUT.mkdir(parents=True, exist_ok=True)
    temporaire = FICHIER_SEXE.with_suffix(".tmp")
    with temporaire.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["wikidata_id", "sexe"])
        w.writerows(sorted(connus.items()))
    temporaire.replace(FICHIER_SEXE)


# ---------------------------------------------------------------------------
# Noms manquants
# ---------------------------------------------------------------------------

# Le service de libellés ne cherche qu'en français puis en anglais ; sans l'un
# des deux, il renvoie l'identifiant brut (« Q2105 » pour Jacques Chirac).
LANGUES_SECOURS = "fr,mul,en,es,it,de,pt,nl"


def est_identifiant(nom: str) -> bool:
    return nom.startswith("Q") and nom[1:].isdigit()


def nom_depuis_article(url: str) -> str:
    """« …/wiki/Jean_Dupont_(homme_politique) » → « Jean Dupont »."""
    titre = unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")
    return titre.split(" (", 1)[0].strip()


def libelles_de_secours(identifiants: list[str]) -> dict[str, str]:
    if not identifiants:
        return {}
    valeurs = " ".join(f"wd:{q}" for q in identifiants)
    requete = (f"SELECT ?p ?pLabel WHERE {{ VALUES ?p {{ {valeurs} }} "
               f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{LANGUES_SECOURS}". }} }}')
    r = requests.get(ENDPOINT, params={"query": requete},
                     headers={"User-Agent": USER_AGENT,
                              "Accept": "application/sparql-results+json"},
                     timeout=TIMEOUT_S)
    if r.status_code != 200:
        print(f"   noms de secours indisponibles (HTTP {r.status_code})", file=sys.stderr)
        return {}
    return {valeur(b, "p").rsplit("/", 1)[-1]: valeur(b, "pLabel")
            for b in r.json()["results"]["bindings"]}


def completer_noms(lignes: list[dict]) -> int:
    """Remplace les identifiants bruts par un nom lisible. Renvoie le nombre corrigé."""
    sans_nom = [r for r in lignes if est_identifiant(r["nom"])]
    for r in sans_nom:
        if r["article_wikipedia_fr"]:
            r["nom"] = nom_depuis_article(r["article_wikipedia_fr"])
    restants = [r for r in sans_nom if est_identifiant(r["nom"])]
    secours: dict[str, str] = {}
    for i in range(0, len(restants), LOT_SEXE):
        secours.update(libelles_de_secours([r["wikidata_id"] for r in restants[i:i + LOT_SEXE]]))
    for r in restants:
        r["nom"] = secours.get(r["wikidata_id"], r["nom"])
    return sum(1 for r in sans_nom if not est_identifiant(r["nom"]))


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

def formater(valeur_iso: str, precision: int) -> str:
    """Date affichée à la précision réellement connue.

    Wikidata stocke une date connue à l'année près comme un 1er janvier : la
    recopier telle quelle ferait croire à une date exacte.
    """
    if not valeur_iso:
        return ""
    signe = "-" if valeur_iso.startswith("-") else ""
    corps = valeur_iso.lstrip("-+")[:10]
    if precision >= 11:
        return signe + corps
    if precision == 10:
        return signe + corps[:7]
    return signe + corps[:4]


def meilleure(declarations: list[tuple[str, int, str]]) -> tuple[str, int, bool]:
    """Choisit une date parmi plusieurs déclarations.

    Ordre : rang préféré d'abord, puis précision la plus fine. Signale une
    ambiguïté quand plusieurs dates différentes restent à égalité.
    """
    if not declarations:
        return "", 0, False

    def cle(d: tuple[str, int, str]) -> tuple[int, int]:
        return RANGS.get(d[2], 0), d[1]

    top = max(cle(d) for d in declarations)
    candidates = sorted({formater(d[0], d[1]) for d in declarations if cle(d) == top})
    # Tri explicite : les déclarations arrivent d'un ensemble, dont l'ordre varie
    # d'une exécution à l'autre. À égalité, la date la plus ancienne l'emporte.
    choix = min(d for d in declarations if cle(d) == top)
    return choix[0], choix[1], len(candidates) > 1


def age_au_deces(naissance: str, prec_n: int, deces: str, prec_d: int) -> str:
    """Âge révolu, calculé seulement quand les deux dates sont connues au jour."""
    if prec_n < 11 or prec_d < 11 or not naissance or not deces:
        return ""
    try:
        n = date.fromisoformat(naissance.lstrip("+")[:10])
        d = date.fromisoformat(deces.lstrip("+")[:10])
    except ValueError:
        return ""
    return str(d.year - n.year - ((d.month, d.day) < (n.month, n.day)))


def consolider(annees: list[int], sortie: Path, sexes: dict[str, str]) -> dict:
    personnes: dict[str, dict] = {}
    for annee in annees:
        with (DOSSIER_BRUT / f"deces_{annee}.csv").open(encoding="utf-8") as f:
            for ligne in csv.DictReader(f):
                p = personnes.setdefault(ligne["wikidata_id"], {
                    "nom": ligne["nom"], "deces": set(), "naissance": set(),
                    "editions": 0, "article": "",
                })
                p["deces"].add((ligne["deces"], int(ligne["deces_precision"] or 0),
                                ligne["deces_rang"]))
                if ligne["naissance"]:
                    p["naissance"].add((ligne["naissance"],
                                        int(ligne["naissance_precision"] or 0),
                                        ligne["naissance_rang"]))
                p["editions"] = max(p["editions"], int(ligne["nb_editions_wikipedia"] or 0))
                p["article"] = p["article"] or ligne["article_wikipedia_fr"]

    lignes = []
    hors_periode = 0
    premiere, derniere = min(annees), max(annees)
    for qid, p in personnes.items():
        dec, prec_d, dec_ambigu = meilleure(list(p["deces"]))
        nai, prec_n, nai_ambigu = meilleure(list(p["naissance"]))
        annee_deces = int(dec.lstrip("+")[:4])
        # Une personne peut avoir une date de décès secondaire dans la période
        # et une date retenue en dehors : elle n'a alors rien à faire ici.
        if not premiere <= annee_deces <= derniere:
            hors_periode += 1
            continue
        lignes.append({
            "annee_deces": annee_deces,
            "nom": p["nom"],
            "sexe": sexes.get(qid, ""),
            "date_naissance": formater(nai, prec_n),
            "precision_naissance": PRECISIONS.get(prec_n, ""),
            "date_deces": formater(dec, prec_d),
            "precision_deces": PRECISIONS.get(prec_d, ""),
            "age_au_deces": age_au_deces(nai, prec_n, dec, prec_d),
            "nb_editions_wikipedia": p["editions"],
            "dates_ambigues": "oui" if (dec_ambigu or nai_ambigu) else "",
            "article_wikipedia_fr": p["article"],
            "wikidata_id": qid,
        })

    noms_completes = completer_noms(lignes)
    lignes.sort(key=lambda r: (r["annee_deces"], r["date_deces"], r["nom"]))
    with sortie.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)

    par_annee: dict[int, int] = {}
    for r in lignes:
        par_annee[r["annee_deces"]] = par_annee.get(r["annee_deces"], 0) + 1
    return {
        "personnes": len(lignes),
        "par_annee": dict(sorted(par_annee.items())),
        "sans_date_naissance": sum(1 for r in lignes if not r["date_naissance"]),
        "naissance_moins_precise_que_le_jour": sum(
            1 for r in lignes if r["date_naissance"] and r["precision_naissance"] != "jour"),
        "dates_ambigues": sum(1 for r in lignes if r["dates_ambigues"]),
        "noms_completes": noms_completes,
        "noms_toujours_manquants": sum(1 for r in lignes if est_identifiant(r["nom"])),
        "par_sexe": {s or "inconnu": sum(1 for r in lignes if r["sexe"] == s)
                     for s in sorted({r["sexe"] for r in lignes})},
        "ecartees_car_date_retenue_hors_periode": hors_periode,
    }


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--debut", type=int, default=1990)
    parser.add_argument("--fin", type=int, default=2025)
    parser.add_argument("--force", action="store_true",
                        help="recollecte même les années déjà en cache")
    args = parser.parse_args()
    if args.debut > args.fin:
        parser.error("--debut doit être inférieur ou égal à --fin")

    annees = list(range(args.fin, args.debut - 1, -1))
    echecs = []
    for annee in annees:
        try:
            collecter_annee(annee, args.force)
        except RuntimeError as e:
            echecs.append(annee)
            print(f"   ÉCHEC {annee} : {e}", file=sys.stderr, flush=True)

    if echecs:
        print(f"\n{len(echecs)} année(s) en échec : {sorted(echecs)}. "
              "Relancez la commande : les années déjà collectées sont en cache.",
              file=sys.stderr)
        return 1

    identifiants: set[str] = set()
    for annee in annees:
        with (DOSSIER_BRUT / f"deces_{annee}.csv").open(encoding="utf-8") as f:
            identifiants.update(l["wikidata_id"] for l in csv.DictReader(f))
    try:
        sexes = collecter_sexes(identifiants)
    except (RuntimeError, requests.RequestException) as e:
        print(f"ÉCHEC sexe : {e}. Relancez la commande.", file=sys.stderr)
        return 1

    sortie = DOSSIER / f"deces_personnalites_fr_{args.debut}_{args.fin}.csv"
    bilan = consolider(sorted(annees), sortie, sexes)
    manifeste = {
        "fichier": sortie.name,
        "source": "Wikidata",
        "endpoint": ENDPOINT,
        "perimetre": ("êtres humains (P31 = Q5) de nationalité française "
                      "(P27 = Q142, doubles nationaux inclus), ayant au moins un article "
                      "Wikipédia, décédés dans la période"),
        "periode": f"{args.debut}–{args.fin}",
        "regle_de_choix_des_dates": ("déclarations dépréciées écartées ; rang "
                                     "préféré, puis précision la plus fine"),
        "licence_donnees": "CC0 (Wikidata)",
        "extrait_le": datetime.now(UTC).isoformat(timespec="seconds"),
        **bilan,
    }
    (DOSSIER / "manifest.json").write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n{bilan['personnes']} personnes écrites dans {sortie.relative_to(DOSSIER.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
