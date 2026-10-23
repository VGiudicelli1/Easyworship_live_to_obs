# Spécification technique

## 1. Inventaire de l'existant

Dépôt : 5 branches, 1 seul auteur, historique 2024-06 → 2024-12. Détail dans `doc/branches.md`.

| Branche | Contenu | Utile pour la suite ? |
|---|---|---|
| `main` | README + licence MIT | Base |
| `dev` = `version1` | **Client EW → fichier texte** (Tkinter). Contient **toute la logique de protocole EW** (`ew_api.py`, `storage.py`, `logger.py`) | **Oui – c'est le cœur à réutiliser** |
| `version2` | Architecture widgets/flux : `Input_File` (watchdog) → `Output_Web` (socket.io + eventlet) + page `public/` ; build PyInstaller | Page web et auto-dimensionnement du texte : **oui**. Moteur widgets/flux : **non** |
| `link_flows` | `version2` + 3 commits (tests widgets, CSS, dessin des liens). Non fusionnée, divergente de `version2` (qui a un commit CSS de plus) | Non |

### Ce que fait réellement `ew_api.py` (v1)

1. Interroge en **mDNS unicast** (UDP 5353 sur l'hôte EW) l'enregistrement `_ezwremote._tcp.local.` pour trouver le **port TCP dynamique** (EW ≥ 7.2.3).
2. Ouvre une connexion **TCP brute** (pas un WebSocket) vers `host:port`.
3. Échange des **messages JSON terminés par `\r\n`**, certains suivis d'un bloc binaire de `size` octets (`LiveData`, `ScheduleData`, `currentImage`, `slideImage`).
4. Envoie `{"action":"connect","device_type":0,"uid":<client_id>,"device_name":...}` puis un `heartbeat` toutes les 3 s.
5. Machine à états alimentée par les messages `status` (`liverev`, `imagehash`, `slide_rowid`, `logo/black/clear`) : si la révision change → `GetLiveData` ; sinon → `getSlideInfo` pour chaque diapo ; quand le contenu de la diapo courante est connu → événement `current_slide_changed`.

> Précision par rapport à la demande initiale : le lien avec EW n'est **pas** un websocket. Seul le lien app → navigateur utilise un websocket (via socket.io).

Détails du protocole : `doc/protocole_easyworship.md`.

## 2. Dette et défauts constatés

### Protocole EW (`src_v1/`)
* `Params.load/save` vides ; hôte `192.168.1.213` et `client_id` figés en dur.
* Résolution : `socket.getaddrinfo(host, 5353)` dans le constructeur → **échoue si l'hôte est un nom non résolu** (exception non gérée à la construction).
* **Déclenchement sur `imagehash` et `if currentSlide.content:`** : une diapo vide, ou dont l'image est identique à la précédente, n'est jamais affichée (10 cas sur 11 dans la capture « diapos vides », `doc/protocole_easyworship.md` §10). À remplacer par le recalcul de l'état à chaque `status`.
* `Slide.isNull()` est **inversée** (renvoie `True` quand le rowid est valide) ; `__str__` affiche « Slide NULL » pour une diapo valide ; `__bool__` s'appuie dessus. Fonctionne par accident.
* `EventsManager`/`EW_API` : `self.events = EventsManager()` redondant ; `raise 'existing event'` (lève un `str`, invalide en Python 3).
* `fireEvent('disconnected')` n'est émis qu'à la fin du thread d'envoi ; **aucune reconnexion** : la boucle `connect()` + `sleep(3)` du `__main__` est un test.
* Concurrence : deux threads (rx/tx) manipulent `storage` sans verrou ; `connected` partagé sans synchronisation ; le thread `rx` bloque sur `recv` sans timeout.
* Les callbacks Tkinter sont appelés **depuis le thread réseau** (non thread-safe).
* Variables inutilisées (`title` local, `content_sent`, `credit_sent`), regex avec séquences d'échappement non brutes (`'\A'`, `'\s'`) → `SyntaxWarning`.
* `interface.py` : widgets posés dans `master` et non dans `self` (le Frame est vide), `lbl_chargement` factice.
* `test.py` (406 lignes) : fichier d'expérimentation, pas de tests automatiques.

### Moteur widgets/flux (`src/` de version2)
* Surdimensionné pour 1 flux de texte. `Widget.NULL`, UID statiques, `Flow` à callbacks, `i_Widget` (≈170 lignes de Canvas), `InterfaceSelectedWidget` (≈270 lignes).
* Boutons `recall`/`save` sans commande ; `app.py` câble `test.txt` en dur ; `edit_file.py` est un script de test.
* `Output_Web.start` : boucle active `eventlet.sleep(0)` (consomme du CPU) ; `except: pass` qui masque toutes les erreurs de bind ; écoute sur `socket.gethostname()` uniquement ; `eventlet.wsgi.server` lancé dans un thread séparé d'un `GreenPool`, ce qui mélange threads natifs et greenlets sans `monkey_patch`.
* f-string avec guillemets imbriqués (`f"...{self.read_param("port")}..."`) → **Python ≥ 3.12 obligatoire**, alors que le Makefile référence `lib/python3.8`.
* `eventlet` est en mode maintenance ; `dnspython` est requis pour le build via `main_imports_pyinstaller.py` (liste de hidden-imports fragile).
* `os.chdir("/".join(sys.executable.split("/")[:-1]))` : ne fonctionne pas sous Windows (séparateur `\`).
* Écriture de `err.txt` et `meta` dans le dossier de l'exécutable : interdit dans `Program Files`.

### Build / CI
* `.github/workflows/build.yml` : ubuntu, Python 3.12, `pip install -r requirements.txt`, `make`, `ls build`. Le Makefile vise un `.app` macOS (`dist/ew_to_txt.app` alors que `-n ew_to_obs`), copie `public/` avec `|| echo`, aucun artefact publié, aucun test.
* `requirements.txt` contient des paquets spécifiques macOS (`macholib`) → installation Windows/Linux douteuse.
* README : deux procédures de build contradictoires (« old method »).
* `.gitignore` : ignore `lib`, `bin`, `include` (génériques, risque de masquer du code).

### Page web (`public/`)
* Dépend d'un CDN pour socket.io (intégrité SRI correcte mais hors-ligne impossible).
* Algorithme d'ajustement de police par dichotomie : bon principe, 10 itérations, à rejouer au redimensionnement de la fenêtre (non fait).
* `disconnect` vide le texte : bon comportement pour OBS.

## 3. Architecture cible (proposition)

```
┌──────────────┐  TCP JSON (mDNS → port)   ┌─────────────────────────────┐   HTTP + WebSocket   ┌────────────┐
│ EasyWorship  │ ◄───────────────────────► │ ew_to_obs (un seul process) │ ◄──────────────────► │ OBS source │
│  (PC régie)  │                           │  ├ ew_client  (réseau EW)   │                      │ navigateur │
└──────────────┘                           │  ├ state      (diapo live)  │                      └────────────┘
                                           │  ├ web_server (HTTP + WS)   │
                                           │  ├ config     (JSON utilisateur)
                                           │  └ ui         (fenêtre simple / tray)
                                           └─────────────────────────────┘
```

### Modules
| Module | Responsabilité | Source de départ |
|---|---|---|
| `ew_client` | Connexion, découverte du port, boucle de messages, reconnexion automatique avec backoff, émission d'un `LiveState(text, visible)` | `ew_api.py` + `storage.py` nettoyés |
| `discovery` | Résolution du nom d'hôte mémorisé ; recherche mDNS (`_ezwremote._tcp`) des PC EW du réseau | nouveau (lib `zeroconf`) |
| `state` | Dernier état (texte, visible) ; notifie les abonnés | nouveau, ~30 lignes |
| `web_server` | Sert `public/` + diffuse l'état aux navigateurs ; envoie l'état courant à chaque nouvelle connexion | `output_web.py` + `public/` |
| `config` | Lecture/écriture JSON (hôte, port web, options) dans le dossier de config de l'OS | nouveau |
| `ui` | Fenêtre : nom du PC EW, état, URL OBS (copier), démarrer/arrêter, journal | `interface.py` (v1) simplifiée |
| ~~`file_export`~~ | Retiré du périmètre initial (possible plus tard) | `logger.LoggerSlideContentToTxt` |

### Choix techniques proposés
* **Langage : Python ≥ 3.11** (le protocole est déjà écrit et validé en Python).
* **Réseau/serveur : `asyncio` + `aiohttp`** (HTTP statique et WebSocket dans un même serveur, un seul thread d'event loop). Alternative plus légère : `websockets` + `http.server`. On abandonne `eventlet` et `socket.io` (le navigateur utilise l'API `WebSocket` native, aucune dépendance front).
* **Client EW** : coroutines `asyncio.open_connection` à la place de 2 threads + deque ; `asyncio.timeout` pour le heartbeat/lecture.
* **UI** : Tkinter minimal (stdlib, déjà utilisé), à faire tourner dans le thread principal, event loop asyncio dans un thread dédié avec passage de messages thread-safe. Option : icône de zone de notification.
* **Config** : `platformdirs` → `%APPDATA%\ew_to_obs\config.json` / `~/Library/Application Support/ew_to_obs/config.json`.
* **Logs** : `logging` avec fichier rotatif dans le dossier de config (plus de `err.txt` à côté de l'exécutable).
* **Tests** : `pytest`; rejouer des **captures de trames EW** (fichier de messages) contre `ew_client` ; test du serveur web via client WebSocket.
* **Build** : PyInstaller (`--onedir`, plus fiable que `--onefile` pour l'antivirus et le démarrage) puis installeur (voir `doc/build_et_installation.md`).

### Découverte et mémoire du PC EW (retour F2)
Contexte : EW sur Windows avec **Bonjour** (obligatoire pour la télécommande), application sur le Mac d'OBS. Bonjour est précisément le service mDNS qui annonce `_ezwremote._tcp` : la découverte mDNS est donc cohérente avec le prérequis EW.

1. Config : `ew_host` = **nom** (ex. `PC-REGIE` ou `PC-REGIE.local`), jamais une IP seule par défaut.
2. Au démarrage : résoudre le nom (DNS local du routeur DHCP / NetBIOS / mDNS) à **chaque tentative de connexion**, de sorte qu'un changement d'IP DHCP soit sans effet.
3. Premier lancement : lancer une recherche mDNS `_ezwremote._tcp.local.` et proposer la liste des PC trouvés ; mémoriser le choix.
4. Repli : saisie manuelle du nom ou de l'IP.
5. **Validé (capture du 2026-10-23)** : la requête mDNS *unicast* vers `<nom-du-pc>.local:5353` fonctionne depuis le Mac vers le PC Windows, le nom `.local` se résout, et le port TCP est dynamique. Reste à valider : l'exploration en *multicast* (liste des PC EW) et le comportement DHCP (changement d'IP).

### Reconnexion et détection de coupure (établies sur captures réelles)
* À chaque tentative : **découverte du port**, puis connexion, puis `connect`. Le port est attribué par EW (3 valeurs différentes observées, changement certain après fermeture puis réouverture d'EW) : on le découvre par mDNS, il n'est jamais saisi ni mémorisé.
* Fermeture observée dans tous les cas (Wi‑Fi local coupé, EW fermé, appairage révoqué) : **EOF** sur la lecture. Première nouvelle tentative **immédiate**, puis attente progressive 0,5 s → 10 s ; état « Perdu (nouvel essai dans N s) ».
* **Délai de grâce de 2 s** (décision du mainteneur) : à la perte de connexion le dernier état reste affiché ; la sortie ne passe à `visible = false` que si la connexion n'est pas rétablie au bout de **2 s** (paramètre `lost_grace_seconds`, réglable). La valeur de 2 s est une décision du mainteneur, **non mesurée** : le test des micro-coupures réseau est abandonné (« on ne va pas s'embêter avec »), on ajustera sur le terrain si besoin. Une micro-coupure rétablie plus vite ne fait donc pas clignoter le texte. À la reconnexion, EW envoie immédiatement un `status` (≈ 10 ms après `connect`, ≈ 0,1 s avec le texte) : l'état est recalculé et diffusé seulement s'il a changé. Les 2 s s'appliquent aussi à la fermeture d'EW et à la révocation de l'appairage ; avant toute connexion réussie, la sortie reste à `visible = false`.
* **Coupure silencieuse** (aucun EOF) : non observée. EW pouvant se taire des minutes, on ne peut pas utiliser l'absence de messages. Prévoir : TCP keepalive (`SO_KEEPALIVE`, délais courts) et échec d'écriture des heartbeats ; à tester en débranchant le PC EW.
* **Résolution du nom** : IPv4 seule (aucune requête AAAA, qui attend un délai sur un nom `.local`), IPv6 uniquement si le nom n'a aucune IPv4 ; chronométrer la résolution. La configuration garde `ew_host` (nom) **et** `last_ip` (dernière IPv4 qui a fonctionné) : tenter d'abord `last_ip`, re-résoudre le nom en parallèle, adopter la nouvelle IP si elle diffère (DHCP). Constat : avec l'IP, découverte 0,02 s + connexion 0,01 s (`doc/protocole_easyworship.md` §14).
* **Réseau : IPv4 d'abord, IPv6 en dernier recours** (l'IPv6 n'a jamais répondu côté EW). Requête mDNS envoyée **en parallèle** à toutes les adresses du nom, première réponse gagnante ; connexion TCP à l'IP qui a répondu, 3 s par adresse, 10 s au total. Aucune attente cumulée par adresse : une tentative qui échoue doit l'être en moins de 5 s, sinon la reconnexion (et le délai de grâce de 2 s) devient inopérante (≈ 29 s mesurés avec l'ancien enchaînement).
* Les heartbeats d'EW vers le client existent (une fois vu) : les ignorer.

### Contrat WebSocket app → navigateur
Un seul message JSON : `{"visible": bool, "text": str}`. Détail dans `spec/interfaces.md`.

### Règle d'émission de l'état (établie sur captures réelles)
1. L'état de sortie est `(visible, text)` avec `visible = not (logo or black or clear)` et `text` = contenu de la diapo `(pres_rowid, slide_rowid)` du dernier `status`, normalisé `\r\n` → `\n`.
2. Il est **recalculé** à chaque `status` et à chaque `slideInfo`/`LiveData` reçu, puis diffusé **seulement s'il a changé** (les `status` répétés, ceux où seuls `permissions`/`schedulerev` bougent, et le double `status` d'un changement de diapo ne produisent rien).
3. Un texte vide est un état valide (diapo vide ou sans texte). **Rien en direct** (`imagehash` vide, ou `slide_rowid` absent du dernier `LiveData`) ⇒ `visible = false`, texte vide.
4. Nouveau `liverev` ⇒ **vider le cache des diapos** puis tout recharger (`GetLiveData`, `getSlideInfo`) ; les `slide_rowid` des chants (`pres_rowid = "0"`, identifiants négatifs) ne sont valables que pour un `liverev`. En attendant les `slideInfo` manquants, ne pas diffuser de texte périmé. Ne pas demander le titre (`slide_rowid 0`). Tout demander d'un coup (150 diapos en 0,2 s, EW répond dans son ordre).
5. Ne dépendre ni de `imagehash`, ni de `rectype`, ni de `slide_no`/`pres_no`.
6. Le texte est toujours `content` : une diapo avec média **et** texte (ex. accueil avec compte à rebours vidéo) diffuse son texte ; une diapo sans texte (média seul) donne un texte vide (`visible = true`). Ni le média, ni son nom (`title`), ni un compte à rebours ne sont transmis. `liverev "0"` / `imagehash` vide ⇒ EW pas prêt ou rien en direct. Aucune mise en forme n'est transmise : texte brut. UTF-8 décodé avec remplacement (EW peut envoyer un `U+FFFD`).

## 4. Exigences non fonctionnelles
* Latence diapo → OBS < 1 s.
* Reconnexion automatique à EW ; l'application ne plante pas si EW est absent au démarrage.
* Aucun accès internet requis à l'exécution.
* Écoute web par défaut sur `127.0.0.1:8000` (cas actuel : OBS et application sur le même Mac). Option « accessible sur le réseau » (`0.0.0.0`) pour la variante où l'application tourne sur le PC Windows d'EW ; documenter alors le pare-feu.
* **Multiplateforme** : Python + bibliothèques pures (asyncio, aiohttp, Tkinter) ; aucun chemin ni séparateur codé en dur ; tests et build en CI sur macOS, Windows et Linux.
* **Démarrage automatique** : Windows (dossier Démarrage ou clé `Run`), macOS (LaunchAgent / Éléments de connexion), Linux (`~/.config/autostart`) via une petite fonction par OS, optionnelle.
* Aucune écriture dans le dossier d'installation.
* Pas de secret ni de donnée personnelle stockés ; le `client_id` doit être **généré à la première exécution** (UUID) et non partagé entre installations.

## 5. Risques techniques
| Risque | Gravité | Parade |
|---|---|---|
| **Appairage** : un `uid` neuf reçoit `notPaired` et attend que l'opérateur accepte (validé le 2026-10-23) ; l'appairage est durable ; l'opérateur peut le **révoquer** dans EW (connexion TCP fermée sans message) ; aucun refus explicite | Moyenne | `client_id` généré par installation et conservé. États « en attente d'acceptation » (sans expiration, heartbeats maintenus) et « connexion fermée par EW » ; reconnexion automatique avec attente progressive. **À tester** : attente prolongée sans réponse, reconnexion après révocation (`notPaired` ?) |
| EW change son protocole | Haute | Tests sur captures, versions testées dans le README, message d'erreur explicite |
| mDNS bloqué par le réseau (VLAN, Wi-Fi invité) | Moyenne | Saisie manuelle du nom/IP en repli |
| Antivirus / SmartScreen bloque l'exécutable non signé | Moyenne | `--onedir`, installeur, documenter ; signature de code si budget |
| Pare-feu Windows bloque le port web (variante app sur le PC d'EW) | Moyenne | Documenter ; cas actuel (app sur le Mac d'OBS) sans port exposé |
| **Bonjour absent du PC EW** : la télécommande EW ne s'active pas | Haute | Détecter l'échec de découverte et afficher « Installer Bonjour sur le PC EasyWorship » ; documenter le prérequis |
| Pas de matériel EW en CI | Haute | Simulateur EW minimal (serveur TCP rejouant des trames) pour les tests |
