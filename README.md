# Easyworship_live_to_obs

Afficher dans **OBS** le texte de la diapo en direct d'**EasyWorship** (EW), via une *Source navigateur*.

> [!WARNING]
> Ce projet dépend d'une **API non documentée et propriétaire** d'EasyWorship (télécommande réseau), comme le projet dont il s'inspire, [ew2vm](https://github.com/mikenor/ew2vm.git) de Michael Norton. Il peut cesser de fonctionner à chaque mise à jour d'EW. Voir [Compatibilités](#compatibilités).
> Michael Norton demande à soutenir [une demande de fonctionnalité pour une API officielle](https://support.easyworship.com/support/discussions/topics/6000033648).

## État du projet

| Date | Statut |
|:--:|:--|
| 2024-06 | v1 : EW → fichier texte (testée en réel) |
| 2024-12 | v2 : architecture « connecteurs » + sortie web, **abandonnée** (ne parle pas à EW) |
| 2026-10 | **Analyse du dépôt et nouvelle spécification** (cette branche). Aucun code applicatif sur `main` pour l'instant |

Objectif : **une seule application**, simple, qui se souvient du PC EasyWorship, avec un installeur.

## Prérequis

* **EasyWorship 7** (testé : 7.4.1.9) avec la *télécommande* activée. Au premier lancement, **EW demande d'accepter la nouvelle télécommande** (appairage) sur le PC EasyWorship. EW exige que **Bonjour** (Apple) soit installé sur son PC pour activer cette télécommande.
* **OBS** avec une *Source navigateur*.
* Application visée : macOS, Windows et Linux.

## Développement

Étapes 1 et 2 du [plan](doc/plan_de_migration.md) : le **client EasyWorship** et le **serveur web avec la page pour OBS** (`src/ew_to_obs/`) sont écrits et testés ; la configuration, l'interface et le packaging restent à faire.

```
python -m venv venv && source venv/bin/activate     # Windows : venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest            # 104 tests (+ 16 dans un vrai navigateur si Playwright est installé)
ruff check src tests && ruff format --check src tests
python -m ew_to_obs --host NOM_OU_IP_DU_PC_EW            # affiche une ligne JSON à chaque changement de diapo
python -m ew_to_obs --host NOM_OU_IP_DU_PC_EW --serve    # + sert la page pour OBS sur http://localhost:8000/
```

Dans OBS : *Sources → + → Navigateur*, coller `http://localhost:8000/`, largeur et hauteur de la scène (ex. 1920 × 1080). Le fond reste transparent. Réglages par l'URL (`?valign=bottom&bg=rgba(0,0,0,.65)&color=white…`) : voir [spec/interfaces.md](spec/interfaces.md) ; `?demo=1` pour régler le style sans application. Tests dans un navigateur : `pip install -e ".[dev,browser]" && playwright install chromium`.

| Module | Rôle |
|---|---|
| `protocol.py` | trames (CRLF + octets joints), messages, binaire de `LiveData` |
| `live.py` | logique pure : messages d'EW → état `(visible, texte)` |
| `discovery.py` | résolution IPv4, port par mDNS (parallèle), connexion TCP |
| `client.py` | boucle asynchrone : appairage, reconnexion, délai de grâce de 2 s, heartbeats, keepalive |
| `web.py` + `public/` | serveur `aiohttp` (page + WebSocket) ; page sans CDN, texte brut, taille de police ajustée à la zone |

## Documentation (branche `claude/analyse_repo`)

| Document | Contenu |
|---|---|
| [spec/metier.md](spec/metier.md) | Besoin, cas d'usage, règles métier, critères de réussite |
| [spec/user_feedback.md](spec/user_feedback.md) | Retours utilisateur et actions |
| [spec/technique.md](spec/technique.md) | Inventaire de l'existant, dette, architecture cible |
| [spec/interfaces.md](spec/interfaces.md) | Interfaces EW, navigateur, opérateur, configuration |
| [STRATEGIES.md](STRATEGIES.md) | Options étudiées et recommandation |
| [doc/branches.md](doc/branches.md) | Analyse de chaque branche |
| [doc/protocole_easyworship.md](doc/protocole_easyworship.md) | Protocole de télécommande EW tel que le code l'utilise |
| [doc/build_et_installation.md](doc/build_et_installation.md) | Build, installeur, CI/CD |
| [doc/capture_trames.md](doc/capture_trames.md) | Capturer les trames EW avec `tools/ew_capture.py` |
| [doc/plan_de_migration.md](doc/plan_de_migration.md) | Étapes de réalisation |

## Compatibilités

| Version d'EasyWorship | Compatible |
|:--:|:--:|
| **EasyWorship 7.4.1.9** (build 7.4.1.9) | Testé le 2026-10-23 (EW sous Windows, client Mac) : connexion, appairage, lecture des diapos |

| Version d'OBS | Compatible |
|:--:|:--:|
| inconnue | « J'espère, je l'utilise » (à renseigner) |

## Retrouver le code existant

Le code n'est pas sur `main` :

* `version1` (= `dev`) : application Tkinter EW → fichier texte.
* `version2` : widgets/flux + sortie web (Python ≥ 3.12, PyInstaller).
* `link_flows` : expérimentation sans suite.

## Licence

MIT, voir [LICENSE.txt](LICENSE.txt).
