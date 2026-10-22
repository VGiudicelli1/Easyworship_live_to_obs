# Stratégies

Décisions à prendre pour repartir sur une application basique. Pour chaque point : options, avantages/inconvénients, **recommandation**.

## S1. Que faire du code existant ?

| Option | + | − |
|---|---|---|
| A. Repartir de `version2` | Build et page web déjà là | Moteur widgets/flux inutile, pas de client EW, Python ≥ 3.12 imposé, eventlet |
| B. Repartir de `dev` (v1) | Client EW **testé en réel** ; peu de code | Pas de serveur web, UI à refaire |
| **C. Nouveau paquet propre, en important le client EW de v1 et la page de v2** | Code minimal, adapté au besoin, tests dès le départ | Réécriture partielle (≈ 400 lignes de protocole à nettoyer) |

**Recommandation : C.** Le protocole est la partie précieuse et risquée ; le reste est simple à refaire.

## S2. Langage et pile

| Option | + | − |
|---|---|---|
| **Python 3.12 + asyncio + aiohttp + Tkinter** | Réutilise le protocole existant, un seul langage, un seul process, peu de dépendances | Exécutable lourd (≈ 30–50 Mo) |
| Node/Electron | UI web moderne | Réécriture du protocole, exécutable très lourd |
| Go ou Rust | Binaire unique léger | Réécriture complète, compétences à acquérir |
| Python + serveur web uniquement (UI dans le navigateur) | Pas de Tkinter | L'opérateur doit ouvrir un navigateur pour configurer |

**Recommandation : Python + aiohttp + Tkinter.** Option à garder : page de configuration dans le navigateur plus tard si Tkinter pose problème.

## S3. Retrouver le PC EasyWorship (retour F2)

| Option | + | − |
|---|---|---|
| IP mémorisée | Simple | Casse avec DHCP : c'est le problème actuel |
| **Nom d'hôte mémorisé, résolu à chaque connexion** | Insensible aux changements d'IP, simple | Dépend du DNS local / NetBIOS / mDNS du réseau |
| Découverte mDNS (`zeroconf`) | Zéro saisie | Multicast parfois bloqué ; dépendance en plus |
| **Combinaison : mDNS pour proposer, nom mémorisé, saisie manuelle en repli** | Couvre tous les cas | Un peu plus de code |

**Recommandation : la combinaison.** Le prérequis EW « Bonjour installé » garantit que l'annonce mDNS existe côté PC EW. À valider sur le réseau réel (voir risque dans `spec/technique.md`). Ordre de développement : nom mémorisé d'abord (couvre la demande), mDNS ensuite.

## S4. Sortie vers OBS

| Option | + | − |
|---|---|---|
| Fichier texte + source « Texte » OBS | Zéro serveur | Pas de mise en page auto, fichier à surveiller |
| Source navigateur sur une page servie par l'app (actuel) | Mise en page libre, auto-dimensionnement | Un serveur local |
| Plugin OBS / obs-websocket (modifier une source) | Natif OBS | Dépend d'obs-websocket, API plus complexe |

**Recommandation : source navigateur** (déjà validée par l'usage) avec WebSocket natif, fichier texte en option.

## S5. Build et distribution (retour F5)

| Option | + | − |
|---|---|---|
| Script manuel / Makefile | Simple | Source du problème actuel |
| **GitHub Actions : PyInstaller `--onedir` sur macOS, Windows, Linux (+ dmg / Inno Setup), release sur tag** | Reproductible, un clic pour publier | Mise en place initiale ; exécutable non signé |
| Paquet pip (`pipx install`) | Très simple pour les devs | Inadapté aux opérateurs non techniques |

**Recommandation : GitHub Actions + installeur.** Voir `doc/build_et_installation.md`.

## S6. Qualité et tests sans matériel EW

* Simulateur EW (serveur TCP rejouant des trames capturées) → tests automatisés du client.
* Capturer des trames réelles lors d'un essai (logger `SEND/RECV` existant).
* Test de fumée du binaire en CI : démarrage `--headless`, `GET /`.

## S7. Gestion des branches

1. Travail sur `claude/analyse_repo` (cette branche) : documentation uniquement.
2. Branche d'implémentation par étape du plan (`doc/plan_de_migration.md`), PR vers `main`.
3. À la fin : tags `v1.0.0` (= `version1`), `v2.0.0-abandonné` (= `version2`) ; suppression de `link_flows`, `dev`, `version1`, `version2`.

## S8. Ce qu'on ne fait pas (YAGNI)

Export fichier, règle « crédits », filtre de présentations (retirés, à rediscuter), connecteurs configurables, sauvegarde de graphes, plugins, multi-sources, contrôle d'EW, base de données, authentification.

## Synthèse

> **Un paquet Python unique** : client EW asynchrone (repris de v1, nettoyé) → état en mémoire → serveur aiohttp (HTTP + WebSocket) → source navigateur OBS. Config JSON avec **nom du PC EW mémorisé** (+ découverte mDNS). Fenêtre Tkinter d'une page. **Installeur Windows (et macOS) produit par GitHub Actions** à chaque tag.
