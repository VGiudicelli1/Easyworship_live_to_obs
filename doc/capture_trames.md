# Capturer les trames d'EasyWorship

Script : `tools/ew_capture.py` (Python ≥ 3.8, macOS / Windows / Linux). Fonctionne avec la bibliothèque standard seule ; si `dnspython` est installé (`pip install dnspython`, comme pour la V1), le script l'utilise pour trouver le port, **exactement comme `ew_api.py` de la V1**.

## Prérequis
* PC EasyWorship allumé, **Bonjour installé**, télécommande EW activée.
* Le Mac (ou autre) qui lance le script est sur le même réseau local.
* Recommandé : `pip install dnspython` (même méthode de découverte que la V1). Sans lui, un repli manuel équivalent est utilisé.

## Utilisation
```
python3 tools/ew_capture.py NOM_DU_PC_EW                  # 60 s, port découvert par mDNS
python3 tools/ew_capture.py NOM_DU_PC_EW --duration 300   # 5 minutes
python3 tools/ew_capture.py NOM_DU_PC_EW --port 51234     # si la découverte mDNS échoue
python3 tools/ew_capture.py NOM_DU_PC_EW --redact         # masque titres et textes
python3 tools/ew_capture.py --analyze captures/xxx.jsonl  # ré-analyser un fichier
python3 tools/ew_capture.py --selftest                    # vérifier le script sans EW
```
Windows : remplacer `python3` par `py`.

## Scénario conseillé pendant la capture (≈ 5 min)
1. Démarrer le script, attendre la connexion.
2. Passer plusieurs diapos d'un chant, revenir en arrière.
3. Passer en **logo**, **noir**, **clear**, puis réafficher.
4. Changer de présentation (chant → verset), puis une diapo sans texte (image/fond).
5. Diapo avec accents, retours à la ligne, texte long, éventuellement mise en forme (gras, etc.).
6. Redémarrer EW ou couper le réseau 10 s (comportement de reconnexion).
7. Noter la **version exacte d'EW** et l'heure de chaque action, pour corréler avec le fichier.

## Sorties
* `captures/ew_capture_AAAAMMJJ_HHMMSS.jsonl` : une ligne JSON par trame (`t`, `dir` = send/recv, `msg`, `extra_len`, `extra_b64`, `decoded` pour `LiveData`). Les images (`currentImage`, `slideImage`) ne sont enregistrées qu'en taille + empreinte SHA‑1.
* Résumé affiché à la fin : actions vues, champs, valeurs distinctes de `status`, délais, et **points d'attention** (action inconnue, champ `size` hors liste, binaire incohérent, champs « inconnus » du header non nuls).
* Le dossier `captures/` est ignoré par Git : les fichiers contiennent le texte des diapos. Pour partager une capture, utiliser `--redact` (le script ne masque que `title`, `content`, `device_name`) et relire le fichier avant publication.

## Premier lancement avec un nouvel `uid`
EW répond `notPaired` et affiche une demande à accepter **sur le PC EasyWorship** ; le script reste connecté (heartbeats) et un message « EN ATTENTE D'APPAIRAGE » s'affiche. Après acceptation, les données arrivent.

## Si la connexion échoue
Le script affiche chaque étape : serveurs mDNS interrogés (toutes les adresses de l'hôte, IPv4 et IPv6), méthode utilisée, erreur exacte. Si dnspython échoue, il retente avec le repli manuel. Vérifier dans l'ordre : Bonjour installé et télécommande activée sur le PC EW ; le nom du PC se résout (`ping NOM`) ; essayer l'IP à la place du nom ; pare-feu Windows (UDP 5353 et port TCP de la télécommande) ; si la découverte échoue seule, `--port` avec le port affiché par EW. Si le port est ouvert mais EW ne répond pas, accepter l'éventuelle demande d'appairage de la télécommande sur EW.

## Ce que le script envoie
Seulement `connect` (avec **l'uid `a164e834-…` et le nom `ew to obs` de la V1**, modifiables par `--client-id` / `--device-name`), `heartbeat` toutes les 3 s, et, sauf `--passive`, `GetLiveData` / `getSlideInfo` comme le fait `ew_api.py`. Jamais de commande de pilotage. `--passive` est utile si l'on soupçonne que ces requêtes perturbent EW.

## Suite
Les fichiers `.jsonl` (masqués) alimenteront `tests/fixtures/` pour tester `ew_client` sans EW (étape 1 de `doc/plan_de_migration.md`) et compléteront `doc/protocole_easyworship.md`.
