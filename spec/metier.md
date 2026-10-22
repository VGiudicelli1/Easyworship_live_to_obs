# Spécification métier

## Contexte

Une église (ou tout lieu de culte / événement) projette textes de chants et versets avec **EasyWorship** (logiciel propriétaire, version 7) sur un PC Windows « régie projection ». La captation vidéo est diffusée via **OBS**, qui tourne sur un Mac. On veut que le texte de la diapo actuellement projetée (« live ») apparaisse aussi dans OBS, par exemple en sous-titre ou en incrustation sur le flux diffusé.

## Objectif

> Récupérer en temps réel le contenu texte de la diapo en direct d'EasyWorship et l'afficher dans OBS via une *Source navigateur*.

## Acteurs

| Acteur | Rôle |
|---|---|
| Opérateur EW | Pilote les diapos dans EasyWorship. Ne doit rien faire de plus. |
| Opérateur OBS / vidéo | Installe et lance l'application, ajoute une source navigateur dans OBS. |
| EasyWorship | Source de vérité (diapo live). API non documentée, propriétaire. |
| OBS | Consommateur : affiche une page web. |

## Cas d'usage

1. **UC1 – Afficher la diapo live dans OBS.** Quand l'opérateur EW change de diapo, le texte dans OBS change en moins d'une seconde.
2. **UC2 – Masquer quand EW masque.** Si EW passe en *logo*, *black* ou *clear*, le texte disparaît d'OBS.
3. **UC3 – Premier démarrage.** L'opérateur indique une seule fois le PC qui héberge EW ; l'application s'en souvient aux lancements suivants.
4. **UC4 – Reconnexion automatique.** Si EW est redémarré ou si le réseau coupe, l'application se reconnecte sans intervention.
5. **UC5 – Installation.** L'opérateur installe l'application depuis un installeur, sans Python ni ligne de commande.
5b. **UC5b – Démarrage automatique (Windows, à l'étude).** Variante : l'application tourne sur le PC Windows d'EW et démarre avec la session ; OBS (Mac) lit alors la page via le réseau.
6. **UC6 – Export fichier texte (retiré du périmètre initial).** Possible plus tard.

## Règles métier

* **Texte seul** : seul le contenu textuel de la diapo est transmis (pas l'image).
* **Fonctions héritées de ew2vm retirées du périmètre initial** (décision du mainteneur : « je ne pense pas » les garder) : règle des diapos de crédits, filtre de présentations, export vers un fichier texte. Elles pourront être rajoutées plus tard si le besoin apparaît.
* **Contenu masqué** = texte vide côté sortie.
* **Mise en page du texte** : le texte est automatiquement agrandi au maximum dans la zone de la source navigateur (déjà fait dans `public/index.js` en v2).
* **Lecture seule** : l'application ne pilote jamais EW ; elle ne fait qu'observer.

## Topologie de déploiement

| | Aujourd'hui | Variante à l'étude |
|---|---|---|
| PC EW (Windows, EW 7 + **Bonjour**) | EasyWorship seul | EasyWorship + application (démarrage auto) |
| Mac OBS | OBS + application | OBS seul |
| URL source navigateur | `http://localhost:8000/` | `http://<nom-pc-ew>:8000/` |
| Application → EW | réseau local (nom du PC EW) | `localhost` |

Prérequis EW : **Bonjour doit être installé sur le PC EW**, sinon la télécommande (API non officielle exploitée) n'est pas activable.

## Hors périmètre (décision proposée)

* Pas de graphe de « connecteurs » / widgets reconfigurables (tentative v2 abandonnée).
* Pas de support d'autres logiciels que EW → OBS (vMix était la cible de l'inspiration ew2vm, pas la nôtre).
* Pas de contrôle d'EW depuis OBS.
* Pas d'accès internet requis pendant le culte (voir risque CDN dans `technique.md`).

## Contraintes et risques métier

* **API non officielle** d'EW : peut casser à chaque mise à jour d'EW. Il faut un tableau de versions testées et un message d'erreur clair si le protocole change.
* **Fiabilité en direct** : un plantage pendant un culte est inacceptable → démarrage automatique, reconnexion, journal de logs consultable.
* **Utilisateurs non techniques** : tout doit tenir en une fenêtre simple et un installeur.
* **Licence / légalité** : l'application imite un client « télécommande » EW. À vérifier vis-à-vis des CGU d'EW ; le projet source (ew2vm) a le même statut.

## Critères de réussite

* Installation + premier affichage dans OBS en **moins de 10 minutes** pour un non-développeur.
* Changement de diapo visible dans OBS en **< 1 s**.
* **Zéro saisie d'IP** dans le cas normal (nom du PC mémorisé).
* Fonctionnement **> 3 h** sans intervention, avec reconnexion si EW redémarre.
