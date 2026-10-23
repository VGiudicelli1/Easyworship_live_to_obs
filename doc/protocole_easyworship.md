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
4. Si `slideInfo` : stocker `content`/`title` dans la diapo ; (code existant seulement) si le titre correspond à la liste « crédits » → le contenu devient le *crédit* de la présentation et la diapo reste vide. Cette règle est retirée de la cible.
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
* Version d'EW testée : **EW 7** (de mémoire du mainteneur, version exacte à confirmer ; la découverte de port dynamique suppose ≥ 7.2.3).
* **Prérequis EW : Bonjour installé** sur le PC EasyWorship, sinon la télécommande n'est pas activable (et le service mDNS `_ezwremote._tcp` n'est pas annoncé).
* Captures de trames réelles : **pas encore disponibles** (pas d'accès à EW pour le moment). Les tests initiaux devront utiliser des trames reconstruites depuis le code / ew2vm, à valider ensuite.

## 6. Pistes de tests sans EW

* Écrire un **simulateur** (serveur TCP + annonce mDNS) qui rejoue des trames capturées (`tests/fixtures/*.jsonl`).
* Capturer les trames réelles avec le logger `LoggerPrint` (déjà présent, affiche `SEND`/`RECV`) pendant un culte-test.


## 7. Constats sur capture réelle (2026-10-23)

Source : `tests/fixtures/ew_session_reelle_anonymisee.jsonl` (60 s, EW 7 sous Windows, client Mac, titres et textes remplacés par des textes factices de même structure). Ce qui suit **corrige ou complète** les sections 1 à 6, rédigées d'après le code seul.

### Confirmé
* Découverte du port par requête mDNS unicast, puis TCP : fonctionne. Le port est **dynamique** (57395 dans la capture). Le nom `<nom-du-pc>.local` se résout depuis le Mac.
* Trame = ligne JSON + `\r\n`, binaire de `size` octets après `LiveData` ; format du binaire `<lqqqlq` + `n × <qq` exact (72 octets pour 2 diapos = 40 + 2×16, 152 pour 7).
* EW répond **10 ms** après `connect` avec un `status`. Les heartbeats toutes les 3 s suffisent : EW n'y répond pas, la connexion tient.
* Dès qu'un `status` annonce un `liverev` inconnu, `GetLiveData` → `LiveData` en 3–10 ms, puis `getSlideInfo` en rafale ; les `slideInfo` reviennent **dans le désordre** (≈ 50 ms pour le titre, ≈ 150 ms pour les diapos). Délai total changement de présentation → texte connu : **≈ 0,1–0,3 s**.
* Au sein d'une présentation, aucune nouvelle requête : seul `status` circule (le contenu est déjà en cache). Si la même présentation est ré-affichée, `liverev` change et tout est redemandé.
* `logo`, `black`, `clear` sont présents dans **chaque** `status`, indépendants (combinaisons vues : `black+clear`, `logo+clear`). Visible = aucun des trois.
* Les retours à la ligne du texte sont `\r\n`, le texte contient apostrophes typographiques, accents et doubles espaces : normaliser en `\n` côté sortie, ne pas « nettoyer ».

### Nouveau / différent de ce qu'on croyait
1. **Message `paired`** (`{"action":"paired","requestrev":"0"}`) : première réponse à `connect`, jamais géré par la V1. Signifie vraisemblablement « télécommande reconnue ». *Reste à tester avec un `uid` jamais utilisé* (voir risque dans `spec/technique.md`).
2. **Types** : dans `status` et `slideInfo`, `pres_rowid`, `slide_rowid`, `pres_no`, `slide_no`, `schedulerev`, `liverev`, `revision`, `requestrev`, `label_*` sont des **chaînes** ; `logo/black/clear` sont des booléens JSON ; `rectype` et `permissions` des entiers. Les clés du binaire `LiveData` sont des entiers : **comparer en normalisant le type** (le script d'analyse avait ce bug).
3. **Un changement de diapo produit souvent deux `status`**, à 5–150 ms d'écart : le premier porte le nouveau `slide_rowid` avec l'**ancien** `imagehash`, le second met à jour l'`imagehash` (9 changements sur 23). Se baser sur `imagehash` (logique V1) retarde donc l'affichage, et ne distingue pas deux diapos d'image identique. **Clé recommandée : `(pres_rowid, slide_rowid)` + `logo/black/clear`**, avec un anti-rebond de ~100 ms.
4. `rectype` vaut 0 sur le `status` qui suit un changement de présentation (et à la connexion), 1 ensuite ; un `status` « 0 » est parfois suivi immédiatement du même en « 1 » (clear). *Hypothèse non confirmée* : 0 = présentation, 1 = diapo.
5. Champs `slideInfo` complets : `rectype`, `pres_rowid`, `slide_rowid`, `title`, `reference_num`, `content`, `notes`, `revision`, `label_bkcolor`, `label_txcolor`. Pour `slide_rowid = "0"` : `title` = nom de la présentation, `content` vide.
6. Pour une diapo, `title` est **vide ou une étiquette de section** (`Verse 1`…). Les diapos « crédits » de ew2vm ne sont pas rencontrées : règle sans objet ici (confirme son retrait).
7. Champs du header `LiveData` : `unknown0` vaut toujours 1 ; `unknown5` varie, proche de `liverev` (probablement une révision) ; `title_revision` et `revision` ressemblent à des horodatages/compteurs 64 bits. Non utiles pour l'application.
8. Valeurs constantes dans la session : `pres_no=slide_no="0"`, `permissions=0`, `schedulerev` fixe, `requestrev="0"` : le mécanisme `requestrev` semble inutilisé par cette version d'EW.

### Non couvert par la capture (à refaire)
Diapo **sans texte** (image/fond), présentation vide, coupure réseau et reconnexion, redémarrage d'EW, édition d'une diapo en direct (`revision` qui change sans `liverev`), diapos très longues, nouvel `uid`, version exacte d'EW.
