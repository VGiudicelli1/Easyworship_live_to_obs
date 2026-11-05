# Notice d'utilisation

Pour l'installation, voir la [notice d'installation](notice_installation.md). Cette notice décrit l'usage courant : déroulé d'un culte, réglage d'OBS, réglages de la page, dépannage.

## 1. Déroulé d'un culte

1. **Allumer** le PC EasyWorship (l'application démarre seule, si le démarrage automatique est installé) et le PC/Mac d'OBS.
2. **Ouvrir EasyWorship**, puis le service. L'application se connecte seule à EW, même si EW est lancé après elle ou relancé en cours de route (le port d'EW change à chaque lancement : l'application le retrouve à chaque connexion).
3. **Ouvrir OBS.** La source navigateur affiche les sous-titres dès qu'une diapo est en direct.
4. Pendant le culte : **rien à faire**. Passer les diapos dans EasyWorship comme d'habitude.

Rien à faire non plus si EW est fermé puis rouvert, si le Wi‑Fi se coupe brièvement ou si la télécommande est retirée dans EW : l'application se reconnecte toute seule.

## 2. Dans OBS

Une seule source navigateur, partagée par toutes les scènes caméra.

1. *Sources* → **+** → **Navigateur**. Nom conseillé : `Sous-titres EW`.
2. **URL** : `http://NOM_DU_PC_EW:8000/?lines=4`
   * `NOM_DU_PC_EW` : le nom de la machine qui exécute l'application (ou son adresse IP si le nom n'est pas reconnu). `localhost` si OBS est sur la même machine.
   * `lines=4` : taille de texte stable (voir §3).
3. **Largeur × hauteur** : la taille du **bandeau** voulu, par exemple **1920 × 360**. Placer la source en bas de l'image.
4. Laisser **décochées** « Éteindre la source lorsqu'elle n'est pas visible » et « Actualiser le navigateur lorsque la scène devient active » : la source reste à jour hors écran et le texte apparaît tout de suite au changement de scène.
5. Optionnel : monter la fréquence d'images à 60 pour un rendu plus fluide.
6. Dans **chaque scène caméra** : *+* → **Ajouter une source existante** → `Sous-titres EW` (une seule source, donc une seule connexion).

Le fond de la page est **transparent** ; le texte est blanc dans un cadre gris translucide. La scène OBS qui montre le live d'EasyWorship en plein écran n'est pas concernée.

**Si le texte n'apparaît pas** : clic droit sur la source → *Propriétés* → bouton **Actualiser le cache du navigateur** (ou rouvrir les propriétés). Si EasyWorship n'a rien en direct, la page est vide : c'est normal. Pour vérifier le style sans EW, ajouter `&demo=1` à l'adresse.

## 3. Réglages de la page (paramètres d'URL)

À ajouter à l'adresse, séparés par `&` : `http://NOM:8000/?lines=4&valign=bottom&bg=rgba(0,0,0,.65)`. Une valeur invalide est ignorée.

| Paramètre | Effet | Défaut |
|---|---|---|
| `grace` | secondes (0 à 60) avant de masquer le texte si la page perd l'application ; `0` = tout de suite | 2 (réglable dans la config : `--browser-grace`) |
| `lines` | **taille stable** : la police ne dépasse pas celle qui fait tenir N lignes (un texte de 2 à 4 lignes garde la même taille ; au-delà, elle diminue) | taille ajustée à chaque diapo |
| `bg` | couleur de fond du cadre (`transparent` pour aucun ; `#` s'écrit `%23` ou s'omet : `bg=003366`) | `rgba(127,127,127,.7)` |
| `color` | couleur du texte | blanc |
| `valign` | position verticale : `top`, `middle`, `bottom` | `middle` |
| `align` | `left`, `center`, `right` | `center` |
| `max` | taille maximale du texte (px) | 133 px (100 pt) |
| `padding`, `margin`, `radius` | marge intérieure, marge autour, arrondi (px) | 20 pt, 20 pt, 10 pt |
| `font` | police (ex. `font=Georgia`) | police système, emojis compris |
| `demo` | `demo=1` ou `demo=Mon%20texte` : aperçu sans EasyWorship | — |

Exemples :

* Sous-titres classiques en bas : `?lines=4&valign=bottom`
* Fond noir plus sombre : `?lines=4&valign=bottom&bg=rgba(0,0,0,.75)`
* Aperçu pour régler le style : `?lines=4&valign=bottom&demo=1`

Pour que ces réglages soient proposés par défaut dans la fenêtre (Mac), les saisir dans le champ « Réglages de la page ».

Très long texte : la police diminue jusqu'à 8 px, puis le texte est coupé mais ne sort jamais de l'écran. Ces cas extrêmes ne sont pas rendus parfaitement.

## 4. Ce qui s'affiche selon la diapo

| Dans EasyWorship | Dans OBS |
|---|---|
| Diapo avec texte (chant, verset…) | le **texte brut**, sans mise en forme (retours à la ligne et emojis conservés) |
| Diapo avec image/vidéo **et** du texte | le texte |
| Diapo avec image/vidéo seule, diapo vide | rien (pas de cadre) |
| Logo, écran noir, écran effacé (*clear*) | rien |
| Rien en direct | rien |
| Connexion de l'application à EW perdue **plus de 2 s** | rien (en dessous de 2 s : le texte reste, pas de clignotement) |
| Connexion d'OBS (la page) à l'application perdue **plus de 2 s** | rien ; en dessous de 2 s le texte reste, et la page se reconnecte toute seule dès que possible |

L'image, la vidéo et le compte à rebours ne sont jamais transmis : seul le texte l'est.

## 5. La fenêtre (Mac / usage manuel)

`python -m ew_to_obs` ouvre une fenêtre :

* **PC EasyWorship** : nom (ou IP) du PC d'EW, puis **Appliquer**. Il est mémorisé.
* **État** : pastille verte = connecté. *En attente d'acceptation* : accepter la télécommande dans EW (§6).
* **Adresse pour OBS** et bouton **Copier**.
* **Navigateurs (OBS)** : nombre de pages connectées.
* **Réglages de la page** et **Port de la page** (8000 par défaut).
* **Aperçu** : le texte actuellement diffusé.
* **Ouvrir le dossier du journal**.

Sur le PC d'EW, en démarrage automatique, il n'y a **pas de fenêtre** : l'état se lit dans le journal (§6) ou en ouvrant l'adresse de la page.

## 6. Dépannage

| Symptôme | Cause probable | Que faire |
|---|---|---|
| Rien ne s'affiche dans OBS, EW a une diapo en direct | application non lancée, pare-feu, mauvais nom | ouvrir `http://NOM:8000/?demo=1` dans un navigateur du Mac ; si ça échoue : vérifier que la tâche tourne (`schtasks /Query /TN "Easyworship vers OBS"`), utiliser l'IP du PC, autoriser le port 8000 dans le pare-feu |
| La page marche en navigateur mais pas dans OBS | cache de la source | *Actualiser le cache du navigateur* dans les propriétés de la source |
| « En attente d'acceptation » | EW n'a pas encore accepté la télécommande | sur le PC EW, accepter **« ew2obs (NOM_DE_LA_MACHINE) »**. Si la demande n'apparaît pas, vérifier que **Bonjour** est installé sur le PC EW et que la télécommande est active |
| La demande d'appairage revient à chaque lancement | le dossier de configuration change (compte différent, tâche sous SYSTEM sans `--config-dir`) | relancer `ew_to_obs_tache.cmd` : il passe le dossier de l'utilisateur ; ne pas supprimer `%APPDATA%\ew_to_obs` |
| « Connexion perdue » en boucle | PC EW éteint/veille, EW fermé, réseau coupé, télécommande retirée dans EW | rien à faire si EW revient : reconnexion automatique. Sinon vérifier réseau et Bonjour |
| Le nom du PC n'est pas trouvé | résolution de nom locale | mettre son adresse **IPv4** à la place du nom (`--host 192.168.x.x --saveconf`) |
| « Port déjà utilisé » | deux copies de l'application, ou autre programme sur 8000 | n'en garder qu'une (`schtasks /End …`), ou changer le port : `--web-port 8001 --saveconf` (et l'adresse dans OBS) |
| Le texte met un instant à changer | normal à un changement de **présentation** (EW met 0,1 à 0,3 s à répondre) ; dans la même présentation c'est instantané | — ; si c'est bien plus lent, lire le journal (ci-dessous) |
| Texte coupé ou trop petit | beaucoup de lignes pour la taille du bandeau | agrandir le bandeau ou retirer `lines=` ; vérifier la hauteur de la source |
| Caractères bizarres (□) | police sans cet emoji/caractère | essayer `?font=…` avec une police complète |

### Journal

* Windows : `%APPDATA%\ew_to_obs\ew_to_obs.log` ; Mac : `~/Library/Application Support/ew_to_obs/ew_to_obs.log` ; Linux : `~/.config/ew_to_obs/ew_to_obs.log` (rotation 1 Mo × 3).
* Il contient les connexions, les changements d'état et les erreurs, avec, pour chaque changement de diapo, le délai en ms après le message d'EW (« état publié … N ms après le status d'EW »). **Le texte des diapos n'y est jamais écrit** : le fichier peut être joint à un rapport.
* Niveau de détail : `--loglevel 0..3` (3 = tout) ; l'enregistrer avec `--saveconf`.
* Afficher la configuration actuelle : `python -m ew_to_obs --show-config`.

### Remise à zéro

Fermer l'application, supprimer `config.json` dans le dossier ci-dessus : une nouvelle identité sera créée et **EW redemandera d'accepter** la télécommande (penser à retirer l'ancienne « ew2obs (…) » dans EW).

## 7. Limites connues

* Dépend d'une **API non documentée** d'EasyWorship : une mise à jour d'EW peut la casser. Version testée : **7.4.1.9**.
* Texte brut seulement (pas de gras, couleurs ni tailles d'EW).
* Pas d'authentification sur la page : réseau de confiance.
* Les points jamais vérifiés en réel (coupure réseau silencieuse, plantage d'EW, Bible/notes/PowerPoint…) sont listés dans [recette.md](recette.md).
