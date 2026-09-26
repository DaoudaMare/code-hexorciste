# Architecture hexagonale

Ces règles s'appliquent au langage du projet, quel qu'il soit. Le vocabulaire "port" et
"adaptateur" se traduit dans l'idiome local :

| Concept          | Python              | Java / C#         | TypeScript      | Go                | Rust        | Flutter / Dart                          |
|------------------|----------------------|-------------------|-----------------|-------------------|-------------|-----------------------------------------|
| Port             | `Protocol` / ABC     | interface         | `interface`     | `interface`       | `trait`     | `abstract interface class`              |
| Adaptateur       | classe concrète      | classe concrète   | classe concrète | struct            | struct      | classe concrète                         |
| Injection        | constructeur/param    | constructeur/DI   | constructeur/DI | constructeur      | constructeur| constructeur                            |

## Règles de base (tous paliers)

- Le domaine n'importe ni framework web, ni driver de base de données, ni SDK cloud, ni
  système de fichiers, ni bibliothèque d'I/O réseau.
- Les ports (interfaces/traits/protocols) vivent dans le domaine ou la couche application.
  Les adaptateurs les implémentent à l'extérieur (infrastructure).
- Un cas d'usage (use case / service applicatif) dépend d'un port, jamais d'un adaptateur
  concret. Il ne connaît pas la technologie derrière le port.
- La persistance passe par un port de type Repository. L'implémentation concrète
  (SQL, NoSQL, fichier, API externe) reste dans l'infrastructure.
- Le sens des dépendances va toujours de l'extérieur vers l'intérieur : infrastructure →
  application → domaine. Jamais l'inverse.

**Mauvais** : le domaine importe un driver SQL, un framework web, un client HTTP ou le
système de fichiers. En Flutter, il importe `package:flutter`, un widget, `http`,
`shared_preferences` ou un plugin.
**Bon** : le domaine déclare un port `OrderRepository` (ou équivalent idiomatique).
L'infrastructure l'implémente, dans le langage du projet. En Flutter, les widgets et
plugins restent des adaptateurs ; le domaine est du Dart pur.

## Modulation par taille (axe 1)

- **Palier P (prototype/script)** : la séparation stricte en dossiers `domain/`,
  `application/`, `infrastructure/` n'est pas obligatoire. En revanche, la règle
  d'import (le cœur métier n'appelle pas directement un framework ou une I/O externe) reste
  recommandée dès qu'il y a plus d'une fonction de logique métier. Ne pas bloquer une
  itération rapide pour imposer une arborescence complète.
- **Palier M (module standard)** : structure en couches explicite attendue
  (`domain/`, `application/` ou `usecases/`, `infrastructure/` ou `adapters/`). Chaque
  port a au moins une implémentation testée séparément du domaine.
- **Palier L (système large)** : en plus de ce qui précède — chaque module/service expose
  ses ports publics dans un espace de noms dédié et documenté ; les changements de contrat
  d'un port sont versionnés ou passent par une revue explicite, car d'autres équipes en
  dépendent ; éviter les dépendances circulaires entre modules du domaine.

## Modulation par complexité métier (axe 2)

- **Simple** : un seul port Repository par agrégat suffit généralement ; pas besoin de
  sur-découper en multiples ports si la logique reste CRUD.
- **Modérée** : isoler les invariants métier dans des objets du domaine (entités, value
  objects) plutôt que dans les cas d'usage, pour qu'ils soient protégés partout où
  l'entité est manipulée.
- **Élevée** : envisager de séparer lecture et écriture (ports distincts) si les
  modèles de consultation et de modification divergent fortement ; documenter chaque
  invariant critique en commentaire ou en test dédié à côté du code qui le protège.

## Modulation par sensibilité (axe 3)

- **Sensible** : aucune donnée personnelle ou secret ne doit transiter par un log,
  une exception, ou un message d'erreur remonté à l'extérieur du système ; les
  adaptateurs qui touchent à des PII valident et journalisent les accès à la frontière,
  pas dans le domaine.
- **Critique** : ajouter un port dédié pour l'audit (`AuditLogger` ou équivalent) et
  l'appeler explicitement à chaque opération sensible depuis la couche application, pas
  depuis le domaine ni l'infrastructure directement ; les secrets (clés, identifiants)
  sont injectés via un port de configuration, jamais codés en dur ni lus directement
  depuis l'environnement au milieu du domaine ; tout appel à un système externe critique
  (paiement, dossier médical, etc.) passe par un port avec un adaptateur qui peut être
  substitué par un double de test strict — jamais par un mock qui masque une vraie
  validation métier.

## Signal d'alerte

Si tu t'apprêtes à écrire `import` (ou équivalent) d'une bibliothèque technique
(HTTP, SQL, cloud SDK, filesystem, framework web, `package:flutter`, plugin Flutter) dans un fichier situé dans `domain/`
ou équivalent : arrête-toi, introduis un port à la place, et propose l'implémentation
concrète dans l'infrastructure.
