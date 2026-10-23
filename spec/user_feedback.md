# Retours utilisateur

Source : retour du mainteneur (utilisateur principal) après usage de la version fonctionnelle, projet arrêté depuis. Chaque retour est relié à l'état du code observé et à l'action proposée.

| # | Retour | Constat dans le code | Action proposée |
|---|---|---|---|
| F1 | Il faut **2 applications** : l'une convertit la diapo EW en fichier texte, l'autre lit ce fichier et le sert à un navigateur | `version1`/`dev` = EW → `ew_out.txt` (Tkinter). `version2` = fichier → web (Input_File → Output_Web) mais **sans** entrée EW (`todo.txt` : « create EW input » jamais fait). Le fichier texte sert uniquement de colle entre les deux. | **Fusionner** en une seule application : client EW → serveur web, en mémoire, sans fichier intermédiaire. Fichier texte retiré du périmètre initial (UC6, possible plus tard). |
| F2 | **Pas de mémoire**, notamment de l'IP du PC qui héberge EW | `Params.load()` / `Params.save()` de v1 sont des `pass`. IP par défaut codée en dur : `192.168.1.213`. Identifiant client EW codé en dur. Bouton « save/recall » de v2 non câblés. | Fichier de config utilisateur (JSON) dans le dossier de config de l'OS. **Mémoriser le nom d'hôte** plutôt que l'IP (DHCP). Découverte automatique mDNS en plus. |
| F3 | Tentative d'interface « **connecteurs** » non aboutie | `version2` : `widget`, `flow`, `i_widget`, `i_flow`, `interfaceSelectedWidget` (≈ 1 000 lignes). Boutons recall/save/add/delete jamais implémentés ; `Output_Web` encore branché en dur dans `app.py` avec un `test.txt` ; `link_flows` (dessin des liens) non fusionnée. | **Abandonner** l'approche générique. Application basique, un seul chemin : EW → web. |
| F4 | Repasser sur une app **plus basique, adaptée à notre situation** | — | Voir `spec/technique.md` (architecture cible) et `STRATEGIES.md`. |
| F5 | Process de **build et d'installation** | Makefile macOS seulement (`.app`, chemin `lib/python3.8` alors que la CI est en Python 3.12), cible `dist/ew_to_txt.app` ≠ sortie `ew_to_obs`. La CI lance `make` puis `ls build` mais **ne publie aucun artefact**. Pas d'installeur. Il faut copier à la main le dossier `public`. | Pipeline CI macOS + Windows + Linux qui produit un installeur et le publie en release GitHub. Voir `doc/build_et_installation.md`. |

## Retours implicites (déduits de l'analyse)

* **F6** – Le serveur web écoute sur `socket.gethostname()` seulement : l'URL à saisir dans OBS est difficile à prévoir et peut échouer silencieusement (`except: pass`). Il faut afficher l'URL dans l'interface avec un bouton « copier ».
* **F7** – La page web charge `socket.io` depuis un **CDN** (`cdn.socket.io`) : sans internet, l'affichage ne marche pas. Embarquer la bibliothèque.
* **F8** – Pas de retour d'état visible pour l'opérateur (connecté à EW ? navigateur connecté ? dernière diapo reçue ?).
* **F9** – Fermeture : v2 gère une sortie propre, v1 non. À conserver sous une forme simple.

## À confirmer avec l'utilisateur

* ~~OBS sur le même PC qu'EW ?~~ **Réponse** : non. EW sur Windows ; OBS et les deux applications Python sur le même Mac.
* ~~OS ?~~ **Réponse** : multiplateforme (Mac, Windows, Linux) si possible. Usage actuel Mac ; Windows (PC d'EW, démarrage automatique) à l'étude.
* ~~Version d'EW ?~~ **Réponse** : EasyWorship 7, version 7.4.1.9.
* ~~Garder export fichier, filtre, crédits ?~~ **Réponse** : probablement non, à revoir avec la nouvelle pile.
* ~~Capture de trames réelles~~ : **faites** (2026-10-23), voir `doc/protocole_easyworship.md` §7–8.
* Le nom du PC EW est-il stable sur le réseau local (DHCP + DNS local / mDNS) ? À tester.
* Prérequis découvert : EW exige **Bonjour** sur son PC pour activer la télécommande.
