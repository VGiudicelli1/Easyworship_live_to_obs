# Easyworship_live_to_obs

Afficher dans **OBS** le texte de la diapo en direct d'**EasyWorship** (EW), via une *Source navigateur*.

> [!WARNING]
> Ce projet dépend d'une **API non documentée et propriétaire** d'EasyWorship (télécommande réseau), comme le projet dont il s'inspire, [ew2vm](https://github.com/mikenor/ew2vm.git) de Michael Norton. Il peut cesser de fonctionner à chaque mise à jour d'EW. Voir [Compatibilités](#compatibilités).
> Michael Norton demande à soutenir [une demande de fonctionnalité pour une API officielle](https://support.easyworship.com/support/discussions/topics/6000033648).

## État du projet

Application **fonctionnelle**, essayée en réel avec EasyWorship 7.4.1.9 (PC Windows) et OBS (Mac) : lecture de la diapo en direct, appairage, reconnexion automatique, page pour OBS, démarrage automatique sous Windows. Une seule application, volontairement basique, qui se souvient du PC EasyWorship. Ce qui reste à valider en conditions réelles est listé dans **[doc/recette.md](doc/recette.md)**.

## Prérequis

* **EasyWorship 7** (testé : 7.4.1.9) avec la *télécommande* activée. Au premier lancement, **EW demande d'accepter la télécommande** « ew2obs (nom de la machine) » (appairage, une seule fois). EW exige que **Bonjour** (Apple) soit installé sur son PC pour activer cette télécommande.
* **OBS** avec une *Source navigateur*.
* **Python 3.12 ou plus récent** (testé 3.12 à 3.15) sur macOS, Windows ou Linux.

## Démarrage rapide (Windows, sur le PC d'EasyWorship)

```
git clone https://github.com/vgiudicelli1/easyworship_live_to_obs && cd easyworship_live_to_obs
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
pip install -r venv/requirements.txt
pip install -e . --no-deps
python -m ew_to_obs --host localhost --serve --loglevel 2 --saveconf   # enregistre la config, ne démarre pas
python -m ew_to_obs --headless                                          # 1er lancement : accepter la télécommande dans EW
packaging\autostart\ew_to_obs_tache.cmd                                # (invite administrateur) démarrage automatique
```

Puis, dans OBS, une source *Navigateur* : `http://NOM_DU_PC_EW:8000/?lines=4`.

**Notices** (en français, pas à pas) :

* **[Notice d'installation](doc/notice_installation.md)** : Windows, Mac, Linux, démarrage automatique, mise à jour, désinstallation.
* **[Notice d'utilisation](doc/notice_utilisation.md)** : déroulé d'un culte, réglage d'OBS, paramètres de la page, ce qui s'affiche, dépannage.

## Ligne de commande

```
python -m ew_to_obs                                      # la fenêtre (Mac, usage manuel) : saisir le PC EW une fois
python -m ew_to_obs --headless --serve                   # sans fenêtre, ce que lance le démarrage automatique
python -m ew_to_obs --ci --host NOM --loglevel 2 2>> ew.log   # mode service (= --headless --serve), journal sur stderr
python -m ew_to_obs --headless --host NOM                # sans page : une ligne JSON par changement de diapo
python -m ew_to_obs --show-config                        # affiche la configuration (lecture seule)
```

Options : `--host`, `--serve`, `--loglevel 0..3`, `--web-port`, `--web-bind`, `--grace`, `--browser-grace`, `--saveconf` (les enregistre comme valeurs par défaut puis quitte), `--config-dir`, `-v`. Voir [spec/interfaces.md](spec/interfaces.md). La configuration et le journal sont dans le dossier utilisateur de l'OS (`%APPDATA%\ew_to_obs`, `~/Library/Application Support/ew_to_obs`, `~/.config/ew_to_obs`).

## Développement

```
python -m venv .venv && source .venv/bin/activate        # Windows : .venv\Scripts\activate.bat
pip install -e ".[dev]"
python -m pytest            # 207 tests ; 19 (page) ignorés sans Playwright, ceux de la fenêtre sans tkinter + écran (Linux : xvfb-run)
ruff check src tests && ruff format --check src tests
```

Tests de la page dans un navigateur : `pip install -e ".[dev,browser]" && playwright install chromium`. Les tests rejouent des **captures réelles anonymisées** du protocole EW (`tests/fixtures/`) et utilisent un faux EW (`tests/fake_ew.py`). Intégration continue : un job Ubuntu à chaque push ; tous les systèmes et le navigateur sur les pull requests.

| Module | Rôle |
|---|---|
| `protocol.py` | trames (CRLF + octets joints), messages, binaire de `LiveData` |
| `live.py` | logique pure : messages d'EW → état `(visible, texte)` |
| `discovery.py` | résolution IPv4, port par mDNS (parallèle), connexion TCP |
| `config.py`, `logs.py` | configuration JSON dans le dossier de l'OS (identité, PC EW, dernière IP), journal tournant sans texte de diapo |
| `client.py` | boucle asynchrone : appairage, reconnexion, délai de grâce de 2 s (aussi côté page), heartbeats, keepalive |
| `web.py` + `public/` | serveur `aiohttp` (page + WebSocket) ; page sans CDN, texte brut, taille de police ajustée à la zone |
| `service.py`, `ui.py`, `status_text.py` | la fenêtre Tkinter : le service tourne dans un thread, la fenêtre lit un instantané toutes les 250 ms |

## Documentation

| Document | Contenu |
|---|---|
| [doc/notice_installation.md](doc/notice_installation.md) | **Installer** l'application et le démarrage automatique |
| [doc/notice_utilisation.md](doc/notice_utilisation.md) | **Utiliser** l'application, régler OBS, dépanner |
| [doc/recette.md](doc/recette.md) | Tests à valider avec le vrai matériel, hypothèses, rapport |
| [doc/protocole_easyworship.md](doc/protocole_easyworship.md) | Protocole de télécommande EW tel que le code l'utilise |
| [doc/capture_trames.md](doc/capture_trames.md) | Capturer les trames EW avec `tools/ew_capture.py` |
| [doc/build_et_installation.md](doc/build_et_installation.md) | Exécutable, installeur, publication (préparés, non validés) |
| [spec/metier.md](spec/metier.md), [spec/user_feedback.md](spec/user_feedback.md) | Besoin, cas d'usage, retours utilisateur |
| [spec/technique.md](spec/technique.md), [spec/interfaces.md](spec/interfaces.md) | Architecture, règles, interfaces et paramètres |
| [STRATEGIES.md](STRATEGIES.md), [doc/plan_de_migration.md](doc/plan_de_migration.md), [doc/branches.md](doc/branches.md) | Historique : options étudiées, plan de réalisation, ancien code |

## Compatibilités

| Version d'EasyWorship | Compatible |
|:--:|:--:|
| **EasyWorship 7.4.1.9** (build 7.4.1.9) | Testé en réel (EW sous Windows) : connexion, appairage, lecture des diapos, reconnexion, démarrage automatique |

| Version d'OBS | Compatible |
|:--:|:--:|
| utilisé en production par le mainteneur (version exacte à renseigner) | Source navigateur : affichage et latence vérifiés |

## Retrouver l'ancien code

L'ancien code reste dans l'historique du dépôt :

* `version1` (= `dev`) : application Tkinter EW → fichier texte.
* `version2` : widgets/flux + sortie web (Python ≥ 3.12, PyInstaller).
* `link_flows` : expérimentation sans suite.

## Licence

MIT, voir [LICENSE.txt](LICENSE.txt).
