# Interfaces

Trois interfaces : (1) EasyWorship ↔ application, (2) application ↔ navigateur OBS, (3) application ↔ opérateur. Plus la configuration.

## 1. Application ↔ EasyWorship (existant, non documenté officiellement)

* **Découverte du port** : requête mDNS `PTR _ezwremote._tcp.local.` envoyée en UDP au port 5353 de l'hôte EW ; la réponse contient en section additionnelle un enregistrement `SRV` dont le port est le port TCP (dynamique depuis EW 7.2.3). Timeout 3 s.
* **Transport** : TCP, timeout de connexion 7 s.
* **Trame** : une ligne JSON UTF‑8 terminée par `\r\n`, éventuellement suivie de `size` octets binaires si `action ∈ {LiveData, ScheduleData, currentImage, slideImage}`.
* Messages et séquence détaillés : `doc/protocole_easyworship.md`.

Interface interne cible (module `ew_client`) :

```python
@dataclass(frozen=True)
class LiveState:
    text: str        # contenu texte de la diapo en direct ("" si rien)
    visible: bool    # False si logo / black / clear

class EwClient:
    async def run(self, host: str) -> None        # boucle infinie avec reconnexion
    on_state: Callable[[LiveState], None]
    on_status: Callable[[ConnectionStatus], None] # SEARCHING, CONNECTING, WAITING_PAIRING, CONNECTED, LOST  # LOST inclut révocation de l'appairage
```

## 2. Application ↔ navigateur (OBS)

### HTTP
| Route | Rôle |
|---|---|
| `GET /` | Page d'affichage (`public/index.html`), à mettre dans une *Source navigateur* OBS (réponses avec `Cache-Control: no-store`) |
| `GET /index.js`, `/index.css` | Ressources statiques embarquées (aucun CDN) |
| `GET /ws` | Mise à niveau WebSocket (ping serveur toutes les 20 s) |
| `GET /favicon.ico` | `204` (pas d'icône) ; toute autre route : `404` |

URL à saisir dans OBS : `http://localhost:<port>/` (application sur le Mac d'OBS) ou `http://<nom-du-pc-ew>:<port>/` (application sur le PC EW, écoute réseau activée) (par défaut port 8000), affichée dans l'UI avec bouton « copier ». 

**Réglages par l'URL** (implémentés, valeurs invalides ignorées ; `#` s'écrit `%23`, ou omis : `bg=003366`) :

| Paramètre | Effet | Défaut |
|---|---|---|
| `bg` | couleur de fond du cadre de texte (`transparent` pour aucun) | `rgba(127,127,127,.7)` |
| `color` | couleur du texte | `#fff` |
| `padding` / `margin` / `radius` | marge intérieure, marge autour de la zone, arrondi (px) | 20 / 20 / 10 |
| `align` | `left`, `center`, `right` (position et alignement du texte) | `center` |
| `valign` | `top`, `middle`, `bottom` (ex. bandeau en bas : `?valign=bottom`) | `middle` |
| `font` | famille de police (lettres, chiffres, espaces, virgules, guillemets) | police système + emojis |
| `max` | taille de police maximale (px) | taille de la zone |
| `lines` | taille **stable** : la police ne dépasse pas celle qui fait tenir N lignes (ex. `lines=4` : un texte de 2 ou 4 lignes garde la même taille, au-delà elle diminue) | désactivé (taille ajustée à chaque diapo) |
| `demo` | `?demo=1` ou `?demo=Mon%20texte` : aperçu du style sans application (aucun WebSocket) | — |

Le texte est affiché en **texte brut** (`textContent`, jamais de HTML), à la plus grande taille de police qui tient dans la zone (8 px minimum ; en dessous le texte est coupé mais ne sort jamais de l'écran), recalculée à chaque changement et à chaque redimensionnement. Le fond de la page reste transparent. Si le WebSocket est perdu, la page masque le texte et se reconnecte seule (délai 0,5 s doublé jusqu'à 5 s).

### WebSocket `/ws`
* Serveur → navigateur, un seul type de message JSON :

```json
{ "visible": true, "text": "Ligne 1\nLigne 2" }
```

* À chaque **nouvelle connexion**, le serveur envoie immédiatement l'état courant.
* Le navigateur vide l'affichage s'il perd la connexion et se reconnecte automatiquement (délai croissant plafonné).
* `text` vide (diapo vide, ou `visible = false`) : la page masque la zone de texte. `visible = false` est aussi envoyé quand **rien n'est en direct** dans EW et quand la connexion à EW est **perdue depuis plus de 2 s** (délai de grâce : les micro-coupures ne font pas clignoter le texte).
* Le texte est du **texte brut** (emojis compris, retours à la ligne `\n`) : la page l'affiche tel quel, sans interpréter de HTML (`textContent`, jamais `innerHTML`).
* Aucun message navigateur → serveur.

*Existant à remplacer :* v2 utilise `socket.io` (événement `data` avec le texte brut seul, sans notion de `visible`).

## 3. Interface opérateur (fenêtre) — implémentée

Une seule page (Tkinter), ouverte par défaut par `python -m ew_to_obs` ; pas de menus, de canvas ni de panneau latéral. `--headless` pour s'en passer.

```
┌ Easyworship vers OBS ────────────────────────────────────────┐
│ PC EasyWorship     [ PC-REGIE                   ] [Appliquer] │
│ État               ● Connecté à EasyWorship                   │
│ (message à lire absolument, en gras, si besoin)               │
│ Navigateurs (OBS)  1 connecté                                 │
│ Adresse pour OBS   [ http://localhost:8000/?lines=4 ] [Copier]│
│ Réglages de la page [ lines=4                        ]        │
│ Port de la page    [ 8000 ]                                   │
│ Aperçu             ┌──────────────────────────────────┐       │
│                    │ texte actuellement affiché        │       │
│                    └──────────────────────────────────┘       │
│                     [Ouvrir le dossier du journal] [Quitter]  │
└───────────────────────────────────────────────────────────────┘
```

Règles :
* La connexion démarre **toute seule** si un PC EW est mémorisé ; sinon la fenêtre demande de le saisir (« Aucun PC EasyWorship configuré »). Aucun bouton Démarrer/Arrêter : l'application tourne tant que la fenêtre est ouverte.
* **Appliquer** (ou Entrée) : valide le nom du PC, le port (1–65535) et les réglages de la page, les mémorise (`config.json`) et redémarre la connexion et le serveur web. Toute valeur invalide affiche un message en rouge sans rien changer.
* **État** (pastille de couleur) : `Recherche d'EasyWorship…` (orange) · `En attente d'acceptation sur le PC EasyWorship` (orange, avec le message « Dans EasyWorship, acceptez la télécommande « <nom> » ») · `Connecté à EasyWorship` (vert) · `Connexion perdue : reconnexion automatique` (rouge, avec le détail et le délai du prochain essai) · `Arrêté` / `Aucun PC EasyWorship configuré` (gris). « Perdu » regroupe coupure réseau, EW fermé et appairage révoqué.
* **Port web occupé** : message d'erreur rouge (« Le port 8000 est déjà utilisé… »), la connexion à EW continue ; il suffit de changer le port et d'appliquer.
* **Adresse pour OBS** : adresse de la page + réglages saisis (mise à jour en direct, seulement si les réglages sont valides) ; **Copier** la place dans le presse-papiers.
* **Aperçu** : texte actuellement diffusé (400 caractères au plus), `— rien d'affiché —` si masqué, `— diapo sans texte —` si vide.
* Fermer la fenêtre ou **Quitter** (Cmd+Q) : arrêt propre (connexion à EW et serveur web fermés, page masquée dans OBS).
* La fenêtre lit l'état du service toutes les 250 ms ; tout le réseau tourne dans un autre thread (aucun appel Tk hors du thread principal).
* Pas encore : « Démarrer avec le système » (étape 7bis du plan).

## 4. Configuration (`config.json`) — implémentée

Dossier de configuration de l'OS (`~/Library/Application Support/ew_to_obs/` sur macOS, `%APPDATA%\ew_to_obs\` sous Windows, `~/.config/ew_to_obs/` sous Linux ; `EW_TO_OBS_CONFIG_DIR` ou `--config-dir` pour le remplacer). Jamais dans le dossier d'installation. Le même dossier contient `ew_to_obs.log`.

```json
{
  "version": 1,
  "ew_host": "PC-REGIE",
  "last_ip": "192.168.1.78",
  "client_id": "0b6c0f3e-…",
  "device_name": "EasyWorship vers OBS",
  "web_port": 8000,
  "web_bind": "127.0.0.1",
  "lost_grace_seconds": 2.0,
  "obs_query": "lines=4"
}
```

| Champ | Rôle | Mémorisé par |
|---|---|---|
| `ew_host` | nom (ou IPv4) du PC EW | `--host` (la dernière IP est alors oubliée) |
| `last_ip` | dernière IPv4 qui a fonctionné, tentée en premier | automatique |
| `client_id` | identité de la télécommande appairée dans EW, **générée une fois** | automatique (`--client-id` pour la changer) |
| `device_name` | nom montré à l'opérateur dans EW | `--device-name` |
| `obs_query` | réglages de la page ajoutés à l'adresse donnée à OBS (défaut `lines=4`) | fenêtre (« Réglages de la page ») |
| `web_port` | port de la page | fenêtre (« Port de la page ») ; `--web-port` pour un seul lancement |
| `web_bind`, `lost_grace_seconds` | valeurs durables, **modifiables à la main** | `--web-bind`, `--grace` ne valent que pour le lancement |

* Fichier absent : valeurs par défaut, identité générée et **écrite dès le premier lancement** (sinon l'appairage serait perdu).
* Chaque champ invalide reprend sa valeur par défaut (avertissement dans le journal) ; un fichier illisible est renommé `config.json.bak` et l'application démarre avec les valeurs par défaut — **la télécommande est alors à ré-accepter dans EW**.
* Écriture atomique (fichier temporaire puis remplacement), droits `600` ; dossier non inscriptible : avertissement, l'application continue.

## 5. Ligne de commande

```
python -m ew_to_obs                                 # la fenêtre (mode normal)
python -m ew_to_obs --headless --host NOM --serve   # sans fenêtre, 1er lancement : le PC EW est mémorisé
python -m ew_to_obs --headless --serve              # sans fenêtre, ensuite : rien à saisir
```

Options : `--host`, `--client-id`, `--device-name` (mémorisés) ; `--port` (diagnostic), `--grace`, `--web-port`, `--web-bind` (ce lancement seulement) ; `--headless` (sans fenêtre) ; `--saveconf` (enregistre `--host`, `--serve`, `--loglevel`, `--web-port`, `--web-bind`, `--grace` comme valeurs par défaut, puis quitte sans démarrer) ; `--ci` (mode service : `--headless --serve`, état de connexion dans le journal sur stderr) ; `--loglevel 0..3` (stderr : erreurs, avertissements, infos, détails ; 2 par défaut avec `--ci`) ; `--serve` (page pour OBS, mode sans fenêtre : la fenêtre la sert toujours) ; `--config-dir`, `--show-config` (lecture seule), `-v`. Sans `--serve`, une ligne JSON `{"visible":…, "text":…}` par changement d'état sur la sortie standard. Codes de sortie : 0 normal, 2 pas de PC EW connu (mode sans fenêtre) ou port web occupé, 3 fenêtre impossible (tkinter ou écran absent).

## 5b. Journal

`ew_to_obs.log` (1 Mo × 3) : connexions, états, erreurs et **une ligne par état publié** (`visible=…, N caractères`). **Jamais le texte des diapos.**
