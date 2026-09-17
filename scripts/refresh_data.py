"""Régénère les données du projet depuis les sources publiques.

    uv run python -m scripts.refresh_data            # sources ouvertes
    uv run python -m scripts.refresh_data --hmd      # + tables HMD (compte requis)

Écrit dans `data/sources/` un CSV par jeu de données, plus un `manifest.json`
qui enregistre pour chacun l'URL, les paramètres, le millésime déclaré par le
fournisseur et la date d'extraction. Le diff Git de ces fichiers est la trace
de ce qui a changé d'un rafraîchissement à l'autre.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from scripts import sources
from scripts.sources import SourceError

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sources"

# Chaque entrée : nom de fichier → fonction sans argument
OPEN_DATASETS = {
    "esperance_vie_fr_insee": sources.fetch_insee_life_expectancy,
    "esperance_vie_fr_tous_ages_eurostat": sources.fetch_eurostat_life_expectancy_fr,
    "esperance_vie_fr_longue_owid": sources.fetch_owid_life_expectancy,
    "naissances_fr_insee": sources.fetch_insee_births,
    "distribution_deces_eurostat": sources.fetch_eurostat_death_distribution,
    "esperance_vie_europe_eurostat": sources.fetch_eurostat_europe,
    "deces_par_age_eurostat": sources.fetch_eurostat_deaths_by_age,
}

# Produit par scripts/collecte_personnalites.py, trop long pour être relancé à
# chaque rafraîchissement.
PERSONNALITES_PAR_DEFAUT = (Path(__file__).resolve().parents[1] / "data" / "personnalites"
                            / "deces_personnalites_fr_1990_2025.csv")


def write(name: str, df, provenance: dict, manifest: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    manifest[name] = {"fichier": f"{name}.csv", **provenance}
    annees = provenance.get("annees", provenance.get("annee_retenue", "—"))
    print(f"  ok  {name:34s} {len(df):5d} lignes   {annees}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hmd", action="store_true",
                        help="ajoute les tables HMD (HMD_USER / HMD_PASSWORD requis)")
    parser.add_argument("--personnalites", type=Path, default=PERSONNALITES_PAR_DEFAUT,
                        help="CSV consolidé de scripts/collecte_personnalites.py")
    args = parser.parse_args()

    manifest: dict = {}
    echecs: list[str] = []

    print("Sources ouvertes")
    for name, fetch in OPEN_DATASETS.items():
        try:
            df, provenance = fetch()
            write(name, df, provenance, manifest)
        except SourceError as e:
            echecs.append(name)
            print(f"  ÉCHEC  {name} : {e}", file=sys.stderr)

    print("\nPersonnalités (collecte Wikidata)")
    try:
        df, provenance = sources.import_personnalites(args.personnalites)
        write("deces_personnalites_wikidata", df, provenance, manifest)
    except SourceError as e:
        echecs.append("deces_personnalites_wikidata")
        print(f"  ÉCHEC  personnalités : {e}", file=sys.stderr)

    if args.hmd:
        print("\nHuman Mortality Database")
        user, pwd = os.environ.get("HMD_USER"), os.environ.get("HMD_PASSWORD")
        if not (user and pwd):
            print("  ignoré : HMD_USER / HMD_PASSWORD non définis", file=sys.stderr)
            echecs.append("hmd")
        else:
            try:
                session = sources.hmd_session(user, pwd)
                for sexe in ("femmes", "hommes"):
                    df, provenance = sources.fetch_hmd_life_table(sexe, session)
                    write(f"distribution_deces_hmd_{sexe}", df, provenance, manifest)
            except SourceError as e:
                echecs.append("hmd")
                print(f"  ÉCHEC  HMD : {e}", file=sys.stderr)

    if manifest:
        existant = OUT_DIR / "manifest.json"
        if existant.exists():
            # Un rafraîchissement partiel ne doit pas effacer la provenance
            # des jeux qui n'ont pas été retentés.
            manifest = {**json.loads(existant.read_text(encoding="utf-8")), **manifest}
        existant.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nManifeste écrit : {existant.relative_to(Path.cwd())}")

    if echecs:
        print(f"\n{len(echecs)} source(s) en échec : {', '.join(echecs)}", file=sys.stderr)
        return 1
    print("\nToutes les sources ont été rafraîchies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
