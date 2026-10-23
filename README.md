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

* **EasyWorship 7** avec la *télécommande* activée. EW exige que **Bonjour** (Apple) soit installé sur son PC pour activer cette télécommande.
* **OBS** avec une *Source navigateur*.
* Application visée : macOS, Windows et Linux.

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
| EasyWorship 7 (version exacte à confirmer, ≥ 7.2.3 pour la découverte du port) | Utilisée par le mainteneur ; test réel en juin 2024 |

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
