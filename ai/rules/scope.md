# Paliers de rigueur du projet

Les règles d'architecture hexagonale et de TDD s'appliquent différemment selon le contexte.
Avant d'écrire du code, identifie où se situe le projet (ou le module modifié) sur ces trois axes.
En cas de doute, demande à l'humain plutôt que de deviner.

## Axe 1 — Taille / durée de vie

- **P (Prototype / script jetable)** — code exploratoire, PoC, script à usage unique, durée de vie < quelques semaines.
- **M (Module / service standard)** — application ou service métier destiné à durer et à être maintenu par une équipe.
- **L (Système large / multi-équipes)** — plusieurs services, plusieurs équipes, code destiné à vivre des années.

## Axe 2 — Complexité métier

- **Simple** — logique CRUD, peu de règles métier, peu de cas limites.
- **Modérée** — plusieurs règles métier interdépendantes, quelques invariants à protéger.
- **Élevée** — nombreuses règles métier, invariants critiques, calculs ou workflows complexes.

## Axe 3 — Sensibilité

- **Standard** — pas de données sensibles, pas d'enjeu réglementaire ou financier direct.
- **Sensible** — données personnelles (PII), données de santé, données financières, secrets, ou système exposé publiquement.
- **Critique** — impact direct sur la sécurité des personnes, la conformité réglementaire (RGPD, HIPAA, PCI-DSS…), ou des flux financiers significatifs.

## Comment combiner les axes

- Le niveau le plus élevé sur n'importe quel axe l'emporte. Un petit script (P) qui touche à des données de santé (Critique) suit les règles du palier Critique sur ce point précis.
- Par défaut, si rien n'est précisé par l'humain : considérer **M / Modérée / Standard**.
- Un module peut avoir un palier différent du reste du projet (ex. le module de paiement est Critique même si le reste de l'app est Standard). Appliquer le palier le plus strict au module concerné, pas à tout le projet.
- Si une règle plus bas mentionne "palier P", "palier L", "Sensible", etc., elle se réfère à cette grille.
