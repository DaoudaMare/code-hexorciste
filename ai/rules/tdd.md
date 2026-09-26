# TDD (Test-Driven Development)

Le nom et l'outil de test suivent le langage du projet : `pytest`/`unittest` (Python),
`JUnit` (Java), `go test` (Go), `Jest`/`Vitest` (TypeScript/JavaScript), `xUnit`/`NUnit`
(C#), `cargo test` (Rust), `RSpec` (Ruby), etc. Les règles ci-dessous ne dépendent
d'aucun de ces outils en particulier.

## Règles de base (tous paliers)

- Pour un comportement nouveau, modifié ou déplacé : écrire d'abord le test qui échoue.
- Écrire ensuite le minimum de code pour le faire passer.
- Nettoyer (refactorer) seulement après que le test passe, sans changer le comportement
  observable.
- Les tests du domaine n'ouvrent ni base de données, ni connexion réseau, ni fichier réel.
  Utiliser des doubles de test (fakes/stubs) pour les ports.

**Mauvais** : déplacer ou modifier le calcul, puis ajouter un test après coup.
**Bon** : un test « le total inclut la taxe » en échec, puis le minimum de code pour le
faire passer, puis le rangement dans le domaine. Le nom du test suit la convention de
l'outil du langage utilisé.

## Modulation par taille (axe 1)

- **Palier P (prototype/script)** : le TDD strict n'est pas exigé pour du code
  exploratoire jetable. Dès qu'une portion de ce code est promue vers un usage durable
  (palier M ou L), elle doit recevoir sa suite de tests avant d'être étendue davantage.
- **Palier M (module standard)** : TDD attendu pour toute la logique métier
  (domaine + cas d'usage). Le code d'infrastructure pur (ex. un simple wrapper de
  configuration) peut être testé après coup si le risque est faible.
- **Palier L (système large)** : TDD attendu pour la logique métier ET pour les
  contrats de port (tests de contrat), car d'autres modules ou équipes dépendent de ces
  interfaces ; tout changement de contrat public s'accompagne d'un test de non-régression
  avant la modification.

## Modulation par complexité métier (axe 2)

- **Simple** : un test par cas nominal et un par cas limite évident suffisent
  généralement.
- **Modérée** : couvrir explicitement chaque invariant métier identifié par un test
  dédié, nommé d'après la règle qu'il protège plutôt que d'après la méthode testée.
- **Élevée** : privilégier des tests basés sur des exemples représentatifs des cas
  limites réels (valeurs nulles, montants négatifs, dates limites, concurrence) plutôt
  que sur la structure interne du code ; envisager des tests de propriété
  (property-based testing) si l'outillage du langage le permet et si les invariants
  s'y prêtent.

## Modulation par sensibilité (axe 3)

- **Sensible** : ajouter des tests qui vérifient explicitement l'absence de fuite de
  données sensibles (pas de PII dans les logs, les messages d'erreur, ou les réponses
  d'API) ; tester les cas d'accès refusé autant que les cas d'accès autorisé.
- **Critique** : les vérifications de sécurité, d'autorisation ou de conformité ne sont
  jamais remplacées par un mock qui court-circuite la logique réelle — un test qui mock
  la vérification elle-même ne prouve rien ; ajouter des tests de régression avant toute
  modification d'un flux critique (paiement, santé, identité), même si le comportement
  semble inchangé ; documenter dans le test lui-même quelle exigence réglementaire ou
  quel risque métier il couvre, pour qu'il ne soit pas supprimé par erreur plus tard.

## Signal d'alerte

Si tu es sur le point d'écrire du code de comportement (pas de la config, pas du
CSS/HTML pur) sans qu'un test échouant existe déjà pour ce comportement : arrête-toi et
écris le test d'abord — sauf si le contexte est clairement palier P.
