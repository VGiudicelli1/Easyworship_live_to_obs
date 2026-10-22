# Protocole de la télécommande EasyWorship (tel qu'utilisé par le code)

> Source : rétro-ingénierie par ew2vm (Michael Norton), reprise dans `src/ew_api.py` de la branche `dev`. **Non documenté par EasyWorship**. Aucune garantie. Ce document décrit ce que fait le code, pas une spécification officielle. À compléter avec des captures de trames réelles.

## 1. Connexion

1. **Résolution du port** (EW ≥ 7.2.3) : requête DNS (mDNS) `PTR _ezwremote._tcp.local.` envoyée **en unicast UDP** à `<hôte EW>:5353`. On lit la cible du PTR, puis dans la section *additionnelle* l'enregistrement `SRV` correspondant → **port TCP**.
2. `socket.create_connection((hôte, port), timeout=7)`.
3. Premier message (client → EW) :
   ```json
   {"device_type":0,"action":"connect","uid":"<client_id>","device_name":"ew to obs"}
   ```
   `uid` est un identifiant client libre (UUID) ; le code actuel utilise une valeur fixe partagée.

## 2. Format des trames

```
<JSON UTF-8>\r\n[<size octets binaires>]
```
Les octets binaires n'existent que si `action ∈ {LiveData, ScheduleData, currentImage, slideImage}`, leur longueur est `size` dans le JSON. Le récepteur doit accumuler les octets jusqu'à avoir tout le message (JSON + `\r\n` + `size`) avant de traiter.

## 3. Messages

### Client → EW
| action | Champs | Rôle |
|---|---|---|
| `connect` | `device_type`, `uid`, `device_name` | Identification |
| `heartbeat` | `requestrev` | Envoyé si rien n'a été émis depuis 3 s |
| `GetLiveData` | `requestrev` | Demande la liste des diapos de la présentation live |
| `getSlideInfo` | `slide_rowid`, `revision`, `requestrev`, `rectype:1`, `pres_rowid` | Demande titre + contenu d'une diapo. `slide_rowid:0` = titre de la présentation |

### EW → client
| action | Champs utiles | Rôle |
|---|---|---|
| `status` | `requestrev`, `liverev`, `imagehash`, `slide_rowid`, `logo`, `black`, `clear` | Notification d'état : changement de présentation (`liverev`), de diapo (`imagehash` + `slide_rowid`), contenu masqué (`logo`/`black`/`clear`) |
| `LiveData` | `size` + binaire | Binaire : en-tête `<lqqqlq` (40 octets : ?, `liverev`, `pres_rowid`, `title_revision`, `nb_diapos`, ?), puis `nb_diapos` × `<qq` (`rowid`, `revision`) |
| `slideInfo` | `slide_rowid`, `title`, `content` | Réponse à `getSlideInfo` |
| `ScheduleData`, `currentImage`, `slideImage` | `size` + binaire | Ignorés par l'application (non utilisés) |

## 4. Algorithme (machine à états de `procmsg`)

À chaque message reçu :

1. Mémoriser `requestrev` s'il est présent (il doit être renvoyé dans les requêtes ; sert à invalider les réponses périmées).
2. Si `status` : stocker `liverev_pending`, `imagehash_pending`, `slide_rowid_pending` ; `contentvisible_pending = not (logo or black or clear)`.
3. Si `LiveData` : vider les diapos, mémoriser `liverev` et `pres_rowid`, créer les diapos (rowid, revision), demander le titre (`slide_rowid:0`).
4. Si `slideInfo` : stocker `content`/`title` dans la diapo ; si le titre correspond à la liste « crédits » → le contenu devient le *crédit* de la présentation et la diapo reste vide.
5. Si le contenu doit être visible et que `imagehash_pending ≠ imagehash` :
   * si `liverev_pending ≠ liverev` → vider la file d'envoi, `GetLiveData` ;
   * sinon demander `getSlideInfo` pour toute diapo non encore demandée ; quand toutes ont répondu et que la diapo courante (`slide_rowid_pending`) existe avec un contenu → **événement `current_slide_changed`**, `imagehash ← imagehash_pending`.
6. Si l'`imagehash` est à jour et que le contenu n'était pas visible → événement `content_visible`.
7. Si le contenu ne doit plus être visible alors qu'il l'était → événement `content_unvisible`.

## 5. Points d'attention / inconnues

* Le champ `imagehash` identifie l'image affichée ; il change à chaque diapo, **même si le texte est identique**.
* Une diapo sans texte (image, fond) a `content` vide → la logique actuelle n'émet alors **pas** `current_slide_changed` (le texte précédent reste affiché). Comportement probablement à corriger : afficher un texte vide.
* Le contenu est du texte brut ; le formatage (gras, retours à la ligne) n'a pas été étudié.
* La table des octets inconnus (`unknownrawdata0`, `unknownrawdata5`) n'est pas comprise.
* Plusieurs télécommandes peuvent-elles se connecter en même temps avec le même `uid` ? Inconnu ; d'où l'intérêt d'un UUID par installation.
* Versions d'EW testées : **inconnues** (README : « I hope because i use it »). À renseigner avec l'utilisateur.

## 6. Pistes de tests sans EW

* Écrire un **simulateur** (serveur TCP + annonce mDNS) qui rejoue des trames capturées (`tests/fixtures/*.jsonl`).
* Capturer les trames réelles avec le logger `LoggerPrint` (déjà présent, affiche `SEND`/`RECV`) pendant un culte-test.
