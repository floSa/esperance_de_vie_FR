"""Vérifie que chaque page Streamlit s'exécute sans lever d'exception.

Complète les tests unitaires : ceux-ci couvrent les calculs, celui-ci attrape
les erreurs de rendu (colonne absente, import mort, données non générées).

    uv run python scripts/check_pages.py
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parent.parent
TIMEOUT = 120

# Les pages importent `common` et `data` en supposant la racine du dépôt sur
# le chemin, comme le fait `streamlit run`.
sys.path.insert(0, str(RACINE))


def main() -> int:
    # accueil.py n'est pas rendu seul : ses liens exigent la navigation d'app.py,
    # qui l'affiche comme page par défaut.
    pages = ["app.py"] + sorted(glob.glob("vues/*.py", root_dir=RACINE))
    echecs = 0
    for page in pages:
        app = AppTest.from_file(str(RACINE / page), default_timeout=TIMEOUT).run()
        if app.exception:
            echecs += 1
            print(f"ÉCHEC  {page}", file=sys.stderr)
            for exc in app.exception:
                print(f"       {exc.value}", file=sys.stderr)
        else:
            notes = sum("Comment lire" in str(m.value) for m in app.markdown)
            print(f"ok     {page:38s} {notes} note(s) de lecture")

    if echecs:
        print(f"\n{echecs} page(s) en erreur", file=sys.stderr)
        return 1
    print(f"\n{len(pages)} pages rendues sans erreur.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
