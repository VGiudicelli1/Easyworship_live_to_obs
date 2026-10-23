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
1. **Messages `paired` / `notPaired`** (`{"action":"paired","requestrev":"0"}`) : première réponse à `connect`. `paired` = télécommande connue ; `notPaired` = inconnue, voir §8 (appairage validé en pratique le 2026-10-23).
2. **Types** : dans `status` et `slideInfo`, `pres_rowid`, `slide_rowid`, `pres_no`, `slide_no`, `schedulerev`, `liverev`, `revision`, `requestrev`, `label_*` sont des **chaînes** ; `logo/black/clear` sont des booléens JSON ; `rectype` et `permissions` des entiers. Les clés du binaire `LiveData` sont des entiers : **comparer en normalisant le type** (le script d'analyse avait ce bug).
3. **Un changement de diapo produit souvent deux `status`**, à 5–150 ms d'écart : le premier porte le nouveau `slide_rowid` avec l'**ancien** `imagehash`, le second met à jour l'`imagehash` (9 changements sur 23). Se baser sur `imagehash` (logique V1) retarde donc l'affichage, et ne distingue pas deux diapos d'image identique. **Clé recommandée : `(pres_rowid, slide_rowid)` + `logo/black/clear`**, avec un anti-rebond de ~100 ms.
4. `rectype` vaut 0 sur le `status` qui suit un changement de présentation (et à la connexion), 1 ensuite ; un `status` « 0 » est parfois suivi immédiatement du même en « 1 » (clear). *Hypothèse **infirmée** par le §10* : `rectype` 0 apparaît aussi sans changement de présentation ; ne pas s'en servir.
5. Champs `slideInfo` complets : `rectype`, `pres_rowid`, `slide_rowid`, `title`, `reference_num`, `content`, `notes`, `revision`, `label_bkcolor`, `label_txcolor`. Pour `slide_rowid = "0"` : `title` = nom de la présentation, `content` vide.
6. Pour une diapo, `title` est **vide ou une étiquette de section** (`Verse 1`…). Les diapos « crédits » de ew2vm ne sont pas rencontrées : règle sans objet ici (confirme son retrait).
7. Champs du header `LiveData` : `unknown0` vaut toujours 1 ; `unknown5` varie, proche de `liverev` (probablement une révision) ; `title_revision` et `revision` ressemblent à des horodatages/compteurs 64 bits. Non utiles pour l'application.
8. Valeurs constantes dans la session : `pres_no=slide_no="0"`, `permissions=0`, `schedulerev` fixe, `requestrev="0"` : le mécanisme `requestrev` semble inutilisé par cette version d'EW.

### Non couvert par la capture (à refaire)
Diapo **sans texte** (image/fond), présentation vide, coupure réseau et reconnexion, redémarrage d'EW, édition d'une diapo en direct (`revision` qui change sans `liverev`), diapos très longues, nouvel `uid`, version exacte d'EW.

## 8. Appairage (2e capture réelle, `uid` neuf, EW 7.4.1.9)

Source : `tests/fixtures/ew_session_appairage_anonymisee.jsonl` (58 s, 346 trames, EW 7 version 7.4.1.9, client Mac).

| t (s) | Événement |
|---|---|
| 0,006 | Client → `connect` avec un `uid` jamais vu et `device_name = "ew to obs"` |
| 0,018 | EW → **`{"action":"notPaired","requestrev":"0"}`** (aucun `status`, aucune donnée) |
| 3, 6 | Client → `heartbeat` : la connexion reste ouverte, EW ne répond rien |
| **8,694** | EW → **`paired`** puis, **dans la même milliseconde**, le premier `status` : l'utilisateur vient d'**accepter la télécommande sur le PC EasyWorship** |
| 8,695 → 8,76 | Séquence habituelle : `GetLiveData` → `LiveData` → `getSlideInfo` × n → `slideInfo` |

Conséquences :
* Un `uid` inconnu **n'est pas refusé** : EW laisse la connexion ouverte et attend la décision de l'opérateur. Le client doit **rester connecté et continuer les heartbeats** (≥ 1 toutes les 3 s) pendant l'attente, et afficher « En attente d'acceptation sur le PC EasyWorship ».
* Un `uid` déjà accepté reçoit `paired` immédiatement (capture du §7 avec l'`uid` de la V1). **Confirmé par le mainteneur** : un appareil enregistré dans EW le reste durablement (jusqu'à révocation, voir §9).
* Délai d'attente maximal d'EW avant refus/abandon : **inconnu** (non testé au-delà de 9 s). Cas « refusé » par l'opérateur : non testé, message attendu inconnu.
* `device_name` est probablement le libellé montré à l'opérateur dans la demande : choisir un nom explicite (« EasyWorship vers OBS »).
* Le port TCP de la télécommande valait **57395 dans les deux captures** (même EW, sessions différentes) : il n'est peut-être pas aussi dynamique qu'annoncé, mais ne pas s'y fier ; garder la découverte mDNS.
* Cette capture ajoute 27 changements de présentation (111 `slideInfo`) sans écart avec le §7 : mêmes champs, mêmes types, `slideInfo` dans le désordre, aucune diapo vide, aucune diapo modifiée ; `logo`/`black`/`clear` toujours faux.

## 9. Mode contrôle, révocation (3e capture, EW 7.4.1.9)

Source : `tests/fixtures/ew_session_controle_revocation_anonymisee.jsonl` (24 s). Déroulé annoncé par le mainteneur : connexion d'un `uid` neuf, appairage validé sur EW, **mode contrôle activé**, **mode contrôle désactivé**, **appairage révoqué**.

| t (s) | Événement observé | Interprétation |
|---|---|---|
| 0,009 | `notPaired` | `uid` neuf (comme §8) |
| 8,894 | `paired` + `status` + `LiveData` + 8 `slideInfo` | appairage validé sur le PC EW |
| 15,207 | `status` **identique** (même diapo, même `imagehash`, mêmes drapeaux) sauf **`permissions: 1`** | mode contrôle activé |
| 20,995 | `status` identique sauf **`permissions: 0`** | mode contrôle désactivé |
| 23,947 | **fermeture de la connexion TCP par EW, sans aucun message** (EOF, ~2,7 s après le dernier heartbeat) | appairage révoqué |

Conséquences pour l'application :
* Le champ `permissions` traduit l'état du *mode contrôle* de cette télécommande dans EW (0 / 1). L'application est en lecture seule : **elle l'ignore**. Données et mises à jour de diapos arrivent normalement avec `permissions = 0`.
* Ce `status` « parasite » ne change ni la diapo ni les drapeaux : la détection par clé `(pres_rowid, slide_rowid, logo, black, clear)` (§7) ne doit **pas** réémettre de mise à jour, ni redemander les données, quand seul `permissions` change.
* **Révocation = fermeture TCP silencieuse**, indiscernable à ce niveau d'une coupure réseau ou d'un redémarrage d'EW. Le client doit donc se reconnecter automatiquement (attente progressive, 1 s → 10 s) ; après une révocation il recevra vraisemblablement `notPaired` (**non capturé** : le script s'arrêtait à la fermeture ; utiliser `--reconnect`) et passera en état « en attente d'acceptation ». Message à l'opérateur proposé : « Connexion fermée par EasyWorship (appairage révoqué ou EW fermé) ».
* Le refus d'une demande d'appairage **n'existe pas** : EW propose seulement d'accepter ou de laisser en attente (information du mainteneur). Il n'y a donc pas de message de refus à gérer ; en revanche l'**attente peut être indéfinie** : pas de délai d'expiration côté application, heartbeats maintenus. Combien de temps EW garde la connexion `notPaired` ouverte sans réponse : **non testé**.
* Texte vide : le mainteneur pense qu'**une diapo vide n'existe pas** dans EW ; une diapo **sans texte** (images seules, etc.) est possible mais **pas encore capturée** — à confirmer ce que renvoie `slideInfo.content` (chaîne vide attendue).

## 10. Diapos vides, étiquettes, édition en direct (4e et 5e captures, EW 7.4.1.9)

Sources : `tests/fixtures/ew_session_diapos_vides_anonymisee.jsonl` (40 s) et `tests/fixtures/ew_session_edition_live_anonymisee.jsonl` (40 s). Présentations de test créées par le mainteneur (la présentation « 443 » est conservée telle quelle dans les fixtures car ses textes décrivent les cas testés ; les autres sont anonymisées).

### Port
Le port de la télécommande valait **63612** dans ces deux captures contre 57395 plus tôt : il change (probablement au redémarrage d'EW). **Ne jamais mémoriser le port**, le redécouvrir à chaque connexion.

### Diapos vides ou sans texte
* **Elles existent** : `slideInfo.content = ""`, `title = ""`, tous les autres champs normaux, et un `status` habituel à l'affichage. Une présentation de 5 diapos vides a été capturée ; la présentation « 443 » contient aussi une diapo vide au milieu.
* **Toutes les diapos vides partagent la même image** donc le même `imagehash`. Dans la capture « diapos vides » : 11 changements de diapo avec `imagehash` inchangé, dont **10 jamais suivis d'un autre `status`** (dans la 5e capture : 3 changements, tous suivis d'un 2e `status` avec nouvel `imagehash`).
  → La logique V1 (déclenchement quand `imagehash` change) **n'aurait jamais vu ces 10 changements** : le texte précédent serait resté affiché. La V1 testait en plus `if currentSlide.content:` (diapo vide ignorée). Confirmation expérimentale de la règle du §7 : l'état se recalcule à **chaque** `status`.
* Comportement attendu côté sortie : diapo vide ⇒ `text = ""` (affichage masqué), pas de maintien du texte précédent.

### Étiquettes (`title` des diapos)
* `title` d'une diapo = **nom de l'étiquette** (« Label 1 », « Verse 2 »…), vide si la diapo n'en a pas ; `label_bkcolor` / `label_txcolor` valent alors `12014644` / `12040119` pour une diapo étiquetée et `536870911` / `1250067` sinon (`536870911 = 0x1FFFFFFF`, « aucune couleur »).
* L'appartenance à un groupe n'est **pas** encodée : une diapo sans étiquette fait partie du groupe de la diapo étiquetée qui la précède (d'après le mainteneur), à déduire de l'ordre de `LiveData`. Deux étiquettes de même nom non adjacentes forment deux groupes distincts. Une diapo vide n'appartient à aucun groupe. **Inutile pour l'application** (texte seul) ; documenté pour mémoire.
* L'ordre des `slides` dans `LiveData` est l'ordre de la présentation (la nouvelle diapo ajoutée en direct apparaît en 4e position).
* Le titre de la présentation (`slide_rowid = "0"`) ne peut pas être vide (EW refuse : « diapo sans titre impossible », intitulé de la présentation de test).

### Édition en direct (capture « édition en direct »)
| t (s) | Événement | Détail |
|---|---|---|
| 10,5 | `status` sans changement de diapo ni d'`imagehash` | seul **`schedulerev`** change (modification du planning) |
| 15,6 | `status` `rectype 0` avec **nouveau `liverev`** (puis, 5 ms plus tard, un 2e `status` avec nouvel `imagehash`) | `GetLiveData` → `LiveData` de **8 diapos** (7 avant) : la diapo ajoutée (`8894`, « contenu 3 : slide ajouté en live ») est insérée à la 4e place ; les `revision` de 2 diapos modifiées ont changé, les autres non |
| 36,9 | `status` : seul `schedulerev` change | pas de changement de `liverev` : rien à recharger |

* **Un changement de contenu en direct se signale par un nouveau `liverev`** (≈ 5 s après la modification dans cette capture), pas par un événement par diapo. Il faut alors tout redemander (`GetLiveData` + `getSlideInfo`), comme pour un changement de présentation. Optimisation possible, non nécessaire : ne redemander que les diapos dont la `revision` du `LiveData` a changé (2 sur 8 ici).
* Après rechargement la diapo en direct garde le **même** `(pres_rowid, slide_rowid)` mais son texte peut avoir changé : la sortie doit être **recalculée et diffusée si le texte a changé**. Dédoublonner sur l'état de sortie `(visible, texte)` et non sur la clé de diapo.
* `schedulerev` (planning EW) change sans effet sur le direct : **à ignorer**, comme `permissions`. Un `status` reçu deux fois de suite avec la même diapo (cas du 10,5 s) ne doit rien déclencher.
* Un `status` peut précéder la fin du rechargement : tant que les `slideInfo` de la diapo courante manquent, ne pas diffuser de texte périmé *ni* vide ; attendre (≈ 0,1–0,2 s) ou conserver l'ancien état jusqu'à réception.

## 11. Coupures, fermeture d'EW, aucun live, sans appairage (6e à 9e captures, EW 7.4.1.9)

Sources : `tests/fixtures/ew_session_coupure_wifi_anonymisee.jsonl`, `ew_session_fermeture_ew_anonymisee.jsonl`, `ew_session_aucun_live_et_chants_anonymisee.jsonl`, `ew_session_sans_appairage_anonymisee.jsonl`. Les trois premières ont été lancées **sans** `--reconnect` : le script s'arrête donc à la première fermeture (la reconnexion elle-même n'a pas été observée en réel).

### Coupure du Wi‑Fi du client (test 1)
* À 10,8 s (dernier heartbeat à 9,1 s) la lecture renvoie **EOF** : le système du client ferme la connexion dès que l'interface réseau tombe. L'événement `closed_by_peer` du script est donc ici une fermeture **locale**, pas un message d'EW.
* **Non observé** : une coupure *silencieuse* (câble ou Wi‑Fi coupé côté PC EW, le client gardant son interface) où aucun EOF n'arrive. Voir ci-dessous la contrainte de détection.

### Fermeture d'EW (test 2)
* À 8,876 s : un dernier `status` (même diapo, même `liverev`, seul `schedulerev` change : EW enregistre le planning en quittant) puis **EOF dans la même milliseconde**. Aucun message d'adieu.
* **Le port change à chaque lancement d'EW** : 57395 (sessions 1 à 3) → 63612 (sessions 4 à 7) → 56326 (après ce redémarrage). Après toute coupure, **redécouvrir le port à chaque tentative** ; un port mémorisé est faux dès qu'EW a redémarré.

### Aucune diapo en direct (test 3, début de session, EW venant d'être ouvert)
* `status` avec **`pres_rowid = "0"`, `slide_rowid` négatif (`-100049`), `imagehash = ""`** ; `GetLiveData` → `LiveData` de **40 octets seulement** (en-tête, `pres_len = 0`, aucune diapo). Notre `getSlideInfo` du titre (`slide_rowid 0`, `pres_rowid 0`) **n'a jamais reçu de réponse** : ne pas attendre le titre.
* ⇒ **Rien en direct** = `imagehash` vide, ou `slide_rowid` absent de la liste du dernier `LiveData`. Sortie : texte vide, `visible = false`.

### Chants de la bibliothèque : `pres_rowid = "0"` et identifiants négatifs (test 3)
* Un chant mis en direct arrive avec **`pres_rowid = "0"`** et des `slide_rowid` **négatifs** (`-100280` … `-100288`), 9 diapos ; le titre du chant est `slideInfo` de `slide_rowid "0"`. Un second chant : `-100378` … `-100386`. Ce ne sont **pas des identifiants stables** : ils sont attribués à la mise en direct.
* ⇒ `pres_rowid = "0"` ne signifie pas « rien en direct » ; et `(pres_rowid, slide_rowid)` n'identifie une diapo **qu'avec le `liverev` courant**. À chaque nouveau `liverev`, vider le cache des diapos (comme la V1) et ne chercher le texte que dans le cache du `liverev` en cours.
* Un refrain répété est constitué de **plusieurs diapos distinctes** (identifiants différents) de contenu identique, d'étiquette `Chorus` (`label_bkcolor 5518453`).
* Les sections `Verse n` / `Chorus` sont dans `title` (voir §10). Textes multilignes avec `\r\n`, apostrophes droites `'` et typographiques `’`.

### Heartbeat envoyé par EW (test 3)
* Une fois, 2,2 s après `connect` : `{"action":"heartbeat","requestrev":"0"}` **d'EW vers le client** (jamais vu dans les 8 autres sessions). Les gérer sans rien faire. **EW est silencieux pendant des minutes** quand rien ne change : l'absence de message ne prouve pas une panne. Détecter une coupure silencieuse par un autre moyen (voir `spec/technique.md`).

### Sans appairage (test 4)
* L'`uid` de la V1, non appairé à ce moment-là, reçoit `notPaired` à 13 ms puis **rien**. La connexion reste ouverte **au moins 40 s** (13 heartbeats envoyés sans réponse ni fermeture). Pas de délai d'expiration observé ; limite supérieure inconnue. Conforme à ce qu'on attend d'un appairage révoqué (§9) : après révocation, la reconnexion donne `notPaired`.

### Conséquences pour le client
1. Reconnexion : `découverte du port → connexion → connect`, **à chaque tentative**, avec attente progressive (1 s → 10 s) ; ne jamais réutiliser un port d'une session précédente.
2. Un `notPaired` ne doit pas déclencher de nouvelle tentative : rester connecté et envoyer les heartbeats (§8).
3. L'application ne lit que le texte des diapos : **ne pas demander le titre (`slide_rowid 0`)**, cela évite un aller-retour qui peut rester sans réponse. Demander d'abord la diapo courante, puis les autres pour que la navigation soit instantanée.
