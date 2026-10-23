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
| `GET /` | Page d'affichage (`public/index.html`), à mettre dans une *Source navigateur* OBS |
| `GET /index.js`, `/index.css` | Ressources statiques embarquées (aucun CDN) |
| `GET /ws` | Mise à niveau WebSocket |

URL à saisir dans OBS : `http://localhost:<port>/` (application sur le Mac d'OBS) ou `http://<nom-du-pc-ew>:<port>/` (application sur le PC EW, écoute réseau activée) (par défaut port 8000), affichée dans l'UI avec bouton « copier ». Paramètres de requête envisagés pour personnaliser sans reconstruire : `?bg=rgba(0,0,0,.6)&color=white&padding=20`.

### WebSocket `/ws`
* Serveur → navigateur, un seul type de message JSON :

```json
{ "visible": true, "text": "Ligne 1\nLigne 2" }
```

* À chaque **nouvelle connexion**, le serveur envoie immédiatement l'état courant.
* Le navigateur vide l'affichage s'il perd la connexion et se reconnecte automatiquement (délai croissant plafonné).
* `text` vide (diapo vide, ou `visible = false`) : la page masque la zone de texte. `visible = false` est aussi envoyé quand **rien n'est en direct** dans EW et quand la connexion à EW est **perdue depuis plus de 2 s** (délai de grâce : les micro-coupures ne font pas clignoter le texte).
* Aucun message navigateur → serveur.

*Existant à remplacer :* v2 utilise `socket.io` (événement `data` avec le texte brut seul, sans notion de `visible`).

## 3. Interface opérateur (fenêtre)

Une seule fenêtre, pas de canvas ni de panneau latéral.

```
┌ Easyworship → OBS ───────────────────────────┐
│ PC EasyWorship : [ PC-REGIE        ] [Chercher]│
│ État EW        : ● Connecté                   │
│ Navigateurs    : 1 connecté                   │
│ URL pour OBS   : http://PC-REGIE:8000/ [Copier]│
│ Aperçu         : « Dieu est amour … »         │
│ ☐ Démarrer avec le système                    │
│                       [Ouvrir les logs] [Quitter]│
└───────────────────────────────────────────────┘
```

Règles :
* Démarrage automatique de la connexion si un hôte est mémorisé.
* Un seul bouton Démarrer/Arrêter si nécessaire ; sinon l'application tourne tant qu'elle est ouverte.
* Fermeture = arrêt propre des sockets.
* État EW : `Recherche… / Connexion… / En attente d'acceptation sur le PC EasyWorship / Connecté / Perdu (nouvel essai dans N s)`. « Perdu » regroupe coupure réseau, EW fermé et **appairage révoqué** (EW ferme alors la connexion sans message) ; après une révocation l'état repasse en « en attente d'acceptation » à la reconnexion. L'état « en attente » (sans délai d'expiration) correspond à la réponse `notPaired` d'EW (l'opérateur doit accepter la télécommande dans EW) ; la connexion reste ouverte et les heartbeats continuent.

## 4. Configuration (`config.json`)

Emplacement : dossier de configuration utilisateur de l'OS (voir `spec/technique.md`).

```json
{
  "version": 1,
  "ew_host": "PC-REGIE",
  "web_port": 8000,
  "web_bind": "127.0.0.1",
  "client_id": "<uuid généré au premier lancement, conservé : c'est l'identité appairée dans EW>",
  "device_name": "EasyWorship vers OBS",
  "lost_grace_seconds": 2,
  "autostart": false
}
```

* Valeurs par défaut sûres si le fichier est absent ou corrompu (le fichier fautif est renommé `.bak`, jamais bloquant).
* `ew_host` accepte un nom ou une IP.

## 5. Ligne de commande (utile pour les tests et un service)

```
ew_to_obs [--host NOM] [--port 8000] [--headless] [--config CHEMIN] [--log-level info]
```

`--headless` : pas d'UI, utile pour tests et déploiement sans écran.
