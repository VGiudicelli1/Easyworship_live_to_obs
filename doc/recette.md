# Recette : tests à valider avec le vrai matériel

Tout le code a été écrit et testé **sans EasyWorship ni OBS** (faux EW, captures réelles rejouées,
page dans Chromium). Ce document liste **tout ce qui n'a pas pu être vérifié** et que la recette doit
valider, avec EasyWorship (EW) sur le PC Windows et OBS sur le Mac.

* Cocher chaque test (☐ → ☑), noter les mesures et les écarts à l'endroit prévu.
* **P1** : bloquant, à valider avant de s'en servir pendant un culte. **P2** : important. **P3** : confort.
* « Auto » : déjà couvert par un test automatique, mais **jamais sur le matériel réel**.
* En cas de doute ou d'échec : noter l'heure exacte, garder le journal (voir §0.4) et refaire avec
  `-v`. Ne jamais joindre de texte de chants : le journal n'en contient pas.

## 0. Préparation

### 0.1 Matériel et versions à noter

| | Valeur relevée |
|---|---|
| EasyWorship (attendu 7.4.1.9) | |
| Windows (PC EW) | |
| Bonjour installé sur le PC EW (obligatoire) | ☐ oui |
| Mac : macOS, Python (≥ 3.10, 3.12 conseillé) | |
| OBS (version) | |
| Réseau : Wi‑Fi ou câble pour le PC EW / le Mac | |
| Date de la recette, personne | |

### 0.2 Lancer l'application (état actuel : en ligne de commande, pas encore d'installeur)

```
git clone https://github.com/VGiudicelli1/Easyworship_live_to_obs.git
cd Easyworship_live_to_obs && git checkout claude/ew_client
python3 -m venv venv && source venv/bin/activate
pip install -e .
python -m ew_to_obs                                   # la fenêtre (mode normal)
python -m ew_to_obs --headless --host NOM_DU_PC_EW --serve   # sans fenêtre, 1er lancement
python -m ew_to_obs --headless --serve                       # sans fenêtre, ensuite : rien à saisir
```

La fenêtre demande **tkinter** : Python de python.org, ou `brew install python-tk` (voir R-80).

Utiles : `--show-config` (affiche la configuration), `-v` (messages détaillés), `--grace 5` (délai de
grâce pour ce lancement), `--web-port 8001` (si le port 8000 est pris), `--config-dir DOSSIER`
(essais sans toucher à la vraie configuration). **Les tests de §1 à §4 se font indifféremment dans la
fenêtre ou en `--headless`** (dans la fenêtre : l'état s'affiche en haut, sinon dans la console).

### 0.3 Présentations de test à préparer dans EW

☐ **T1** chant de la bibliothèque, 4 couplets de 4 à 6 lignes, avec refrain répété ·
☐ **T2** diapos de **1, 2, 4, 6 et 8 lignes** ·
☐ **T3** une diapo **vide** et une diapo avec un **espace seulement** ·
☐ **T4** diapo **image seule**, diapo **vidéo seule**, diapo **image + texte**, diapo **vidéo + texte**
(la diapo d'accueil avec compte à rebours de 5 min) ·
☐ **T5** texte avec **emojis**, accents, apostrophes `’`, guillemets « », **gras/italique** ·
☐ **T6** diapo de **990 caractères** sur une ligne, et une de **20 lignes** (cas extrême) ·
☐ **T7** **verset biblique** (Écriture) ·
☐ **T8** diapo avec une **note** et une **référence** renseignées ·
☐ **T9** présentation de **150 diapos** (puis, si possible, **1 000**) ·
☐ **T10** présentation importée **PowerPoint/PDF** (si utilisée en réel) ·
☐ **T11** un planning (liste) contenant plusieurs de ces éléments.

### 0.4 Où sont les fichiers

| Système | Configuration + journal |
|---|---|
| macOS | `~/Library/Application Support/ew_to_obs/` (`config.json`, `ew_to_obs.log`) |
| Windows | `%APPDATA%\ew_to_obs\` |
| Linux | `~/.config/ew_to_obs/` |

Le journal (1 Mo × 3 fichiers) contient les connexions, les erreurs et **une ligne par état publié**
(`état publié : visible=True, 37 caractères`) : sert à mesurer les délais. Aucun texte de diapo.

### 0.5 Ordre conseillé (≈ 2 h 30)

1. §1 installation et appairage → 2. §5b la fenêtre → 3. §2 connexion → 4. §3 diapos → 5. §5 OBS →
6. §4 résilience → 7. §6 durée (laisser tourner pendant un vrai service ou une répétition) → 7. §7 variante Windows → 8. §8
captures complémentaires.

---

## 1. Installation, premier lancement, appairage

### R-01 · Premier lancement et appairage (P1)
- **Préparer** : aucune configuration (supprimer le dossier de §0.4 ou `--config-dir` neuf). EW ouvert.
- **Faire** : `python -m ew_to_obs --host NOM_DU_PC_EW --serve`.
- **Attendu** : message « acceptez la télécommande « EasyWorship vers OBS » sur le PC EasyWorship » ; **une
  demande apparaît dans EW** ; après acceptation, l'état passe à *connected* en < 2 s ; `config.json` et
  `ew_to_obs.log` créés ; l'adresse `http://localhost:8000/` est affichée.
- **Relever** : le texte exact de la demande dans EW (nom affiché ?), le temps entre l'acceptation et la connexion.
- ☐ OK ☐ KO — notes :

### R-02 · Deuxième lancement sans argument (P1)
- **Faire** : arrêter (Ctrl+C), relancer `python -m ew_to_obs --serve`.
- **Attendu** : connexion directe **sans nouvelle demande** dans EW ; aucune saisie ; même identité
  (`--show-config` : `client_id` inchangé).
- ☐ OK ☐ KO — notes :

### R-03 · Appairage conservé après redémarrage du PC EW (P1)
- **Faire** : redémarrer complètement le PC Windows, relancer EW, laisser l'application se reconnecter.
- **Attendu** : reconnexion automatique, **sans** nouvelle acceptation.
- ☐ OK ☐ KO — notes :

### R-04 · Attente prolongée avant d'accepter (P2)
- **Faire** : première connexion avec un nouvel identifiant (`--config-dir` neuf), **ne pas accepter**.
  Laisser **10 minutes** (heartbeats actifs), puis accepter.
- **Attendu** : reste en « attente d'acceptation » sans fermeture ni erreur ; connecte dès l'acceptation.
  *(Inconnu jusqu'ici : au-delà de 40 s, EW ferme-t-il la connexion ?)*
- **Relever** : durée maximale observée avant fermeture éventuelle par EW.
- ☐ OK ☐ KO — notes :

### R-05 · Identité de la V1 (P3)
- **Faire** : `--config-dir` neuf avec `--client-id a164e834-fc66-4cff-8e47-aa904ee9e62b`.
- **Attendu** : si cette identité est encore appairée dans EW, connexion directe ; sinon demande normale.
- ☐ OK ☐ KO — notes :

### R-06 · Révocation de l'appairage dans EW (P1)
- **Faire** : appli connectée avec un texte affiché ; dans EW, **révoquer** la télécommande.
- **Attendu** : connexion fermée ; le texte disparaît d'OBS au bout de **2 s** ; l'application se
  reconnecte, reçoit « non appairée » et affiche « attente d'acceptation » ; **ré-accepter** dans EW
  rétablit tout sans relancer l'application.
- **Relever** : la reconnexion se fait-elle seule, en combien de temps ?
- ☐ OK ☐ KO — notes :

### R-07 · Configuration abîmée ou supprimée (P2)
- **Faire** : (a) écrire du texte quelconque dans `config.json` ; (b) supprimer `config.json`.
- **Attendu** : (a) l'appli démarre, `config.json.bak` créé, message « ré-accepter dans EW » ;
  (b) démarrage avec nouvelle identité. Dans les deux cas **une nouvelle demande d'appairage** dans EW.
- ☐ OK ☐ KO — notes :

### R-08 · Dossier de configuration en lecture seule (P3)
- **Faire** : rendre le dossier non inscriptible, lancer.
- **Attendu** : avertissement dans la console, l'application fonctionne quand même (identité non conservée).
- ☐ OK ☐ KO — notes :

---

## 2. Connexion et découverte

### R-10 · Connexion par nom (`.local`) : rapidité (P1)
- **Faire** : `python -m ew_to_obs --host NOM.local --serve -v`, noter l'heure de lancement et celle de *connected*.
- **Attendu** : connexion en **< 1 s** (le nom n'est plus résolu qu'en IPv4, sans requête IPv6).
  *(Le mainteneur avait observé une lenteur avec le nom et pas avec l'IP ; la cause supposée — la requête
  IPv6 — est corrigée mais n'a pas pu être re-mesurée.)*
- **Relever** : durée mesurée : ______ s. Si > 2 s : relancer avec l'IP (R-11) et comparer.
- ☐ OK ☐ KO — notes :

### R-11 · Connexion par IPv4 (P2)
- **Faire** : même chose avec l'adresse IP.
- **Attendu** : < 0,5 s (0,02 s de découverte + 0,01 s de connexion mesurées sur la V1 améliorée).
- ☐ OK ☐ KO — durée : ______ s

### R-12 · Dernière IP mémorisée et changement d'adresse DHCP (P1)
- **Préparer** : une connexion réussie par nom (la dernière IP est enregistrée : `--show-config`).
- **Faire** : changer l'adresse IP du PC EW (renouveler le bail DHCP, ou redémarrer la box), relancer.
- **Attendu** : l'ancienne IP échoue vite (≈ 1 s), le **nom est re-résolu**, connexion établie, nouvelle IP
  mémorisée ; **aucune saisie**.
- **Relever** : délai total de reconnexion : ______ s.
- ☐ OK ☐ KO — notes :

### R-13 · Port de la télécommande qui change (P1)
- **Faire** : fermer puis rouvrir EW (le port change à chaque lancement).
- **Attendu** : reconnexion automatique sur le nouveau port, sans intervention.
- **Relever** : délai entre l'ouverture d'EW et le premier texte à l'écran : ______ s.
- ☐ OK ☐ KO — notes :

### R-14 · Bonjour absent ou télécommande désactivée (P2)
- **Faire** : désactiver la télécommande dans EW (ou arrêter le service Bonjour).
- **Attendu** : l'application ne plante pas, réessaie (attente 0 → 10 s), le journal explique l'échec ;
  elle se connecte dès que la télécommande est réactivée.
- **À améliorer si le message n'est pas clair** : noter ce qui est affiché.
- ☐ OK ☐ KO — notes :

### R-15 · Pare-feu et réseau (P2)
- **Faire** : noter toute fenêtre du pare-feu (Mac ou Windows) au lancement ; tester réseau Wi‑Fi invité
  / VLAN s'il existe.
- **Attendu** : aucune fenêtre bloquante en usage normal (écoute sur `127.0.0.1` seulement) ; si le
  réseau isole les appareils, noter le message obtenu.
- ☐ OK ☐ KO — notes :

### R-16 · Port web déjà utilisé (P3)
- **Faire** : lancer deux instances (`--serve`).
- **Attendu** : la seconde s'arrête avec un message clair proposant `--web-port 8001`, code de sortie 2.
- ☐ OK ☐ KO — notes :

---

## 3. Suivi des diapos (EW → texte affiché)

Pour chaque test, regarder l'aperçu OBS (ou `http://localhost:8000/` dans un navigateur).

### R-20 · Chant : défilement des couplets et du refrain (P1)
- **Faire** : T1, avancer et reculer dans tous les couplets, plusieurs fois.
- **Attendu** : le texte affiché est **toujours celui de la diapo en direct d'EW**, sans retard ni saut ;
  le refrain répété s'affiche à chaque occurrence.
- ☐ OK ☐ KO — notes :

### R-21 · Latence changement de diapo → OBS (P1)
- **Faire** : filmer au téléphone (ralenti) l'écran d'EW et l'aperçu OBS, changer de diapo 10 fois.
  Variante : repérer l'heure du clic et celle de la ligne `état publié` du journal.
- **Attendu** : **< 1 s** (objectif ≈ 0,3 s).
- **Relever** : médiane ______ s, maximum ______ s.
- ☐ OK ☐ KO

### R-22 · Clics très rapides (P1)
- **Faire** : T1/T9, enchaîner 20 changements de diapo en 5 s, puis s'arrêter.
- **Attendu** : l'affichage finit **toujours sur la dernière diapo** ; jamais bloqué sur une diapo antérieure.
- ☐ OK ☐ KO — notes :

### R-23 · Changement de présentation et de chant (P1)
- **Faire** : passer de T1 à T2 à T9, puis à un chant de la bibliothèque, aller-retour.
- **Attendu** : aucun texte de la présentation précédente ne reste ; pas de clignotement parasite.
- ☐ OK ☐ KO — notes :

### R-24 · Logo, noir, effacer (clear) (P1)
- **Faire** : activer/désactiver **logo**, **noir**, **clear**, seuls puis combinés, avec un texte affiché.
- **Attendu** : le texte **disparaît** pour chacun, **réapparaît** (même texte) quand tout est désactivé.
- ☐ OK ☐ KO — notes :

### R-25 · Rien en direct (P1)
- **Faire** : fermer la présentation en direct / ouvrir EW sans rien projeter.
- **Attendu** : rien d'affiché ; pas d'erreur ; l'affichage démarre dès qu'une diapo passe en direct.
- ☐ OK ☐ KO — notes :

### R-26 · Diapo vide et diapo sans texte (P1)
- **Faire** : T3 puis T4 (image seule, vidéo seule).
- **Attendu** : **aucun texte affiché** (le texte de la diapo précédente ne doit pas rester).
- ☐ OK ☐ KO — notes :

### R-27 · Diapo avec média **et** texte (P1)
- **Faire** : la diapo d'accueil (vidéo de compte à rebours + texte), puis image + texte.
- **Attendu** : le **texte** est affiché ; le média et le compte à rebours ne le sont pas (limite connue).
- ☐ OK ☐ KO — notes :

### R-28 · Nombre de lignes et taille du texte (P1)
- **Faire** : T2 (1, 2, 4, 6, 8 lignes) dans le bandeau OBS réel, avec et sans `?lines=4`.
- **Attendu** : texte lisible de 2 à 8 lignes ; avec `lines=4`, même taille jusqu'à 4 lignes.
- **Relever** : réglage retenu (taille de la source, `lines`, `valign`) : ____________
- ☐ OK ☐ KO — notes :

### R-29 · Cas extrêmes (P3)
- **Faire** : T6 (990 caractères, 20 lignes).
- **Attendu** : pas de plantage ; le texte reste **dans l'écran** (éventuellement tronqué/très petit).
- ☐ OK ☐ KO — notes :

### R-30 · Emojis, accents, guillemets, mise en forme (P1)
- **Faire** : T5.
- **Attendu** : accents et `’ « »` corrects ; **emojis en couleur** dans OBS (voir R-52) ; **gras/italique ne
  sont pas rendus** (texte brut, limite connue) ; un caractère « � » en fin de ligne est possible s'il est
  déjà dans le texte source d'EW.
- ☐ OK ☐ KO — notes :

### R-31 · Verset biblique (P2)
- **Faire** : T7.
- **Attendu** : le texte du verset est affiché ; noter si la **référence** (livre, chapitre) apparaît ou
  non (elle n'est pas affichée aujourd'hui).
- **Relever** : le comportement observé + une capture `tools/ew_capture.py --redact` (voir §8).
- ☐ OK ☐ KO — notes :

### R-32 · Notes et références renseignées (P3)
- **Faire** : T8.
- **Attendu** : seul le contenu de la diapo est affiché (pas les notes) ; aucun message d'erreur.
- ☐ OK ☐ KO — notes :

### R-33 · Modification d'une diapo pendant qu'elle est en direct (P2)
- **Faire** : diapo en direct, la modifier dans l'éditeur d'EW (ajouter une phrase), valider.
- **Attendu** : le texte affiché **se met à jour** (jusqu'à ~5 s d'attente observée sur les captures),
  sans clignotement.
- **Relever** : délai de mise à jour : ______ s.
- ☐ OK ☐ KO — notes :

### R-34 · Planning (liste) modifié (P3)
- **Faire** : ajouter/déplacer/supprimer des éléments du planning pendant qu'une diapo est en direct.
- **Attendu** : aucun effet sur l'affichage.
- ☐ OK ☐ KO — notes :

### R-35 · Mode contrôle d'EW activé/désactivé (P3)
- **Faire** : activer puis désactiver le mode contrôle de la télécommande dans EW.
- **Attendu** : aucun effet sur l'affichage ; l'application reste connectée.
- ☐ OK ☐ KO — notes :

### R-36 · Grosses présentations (P2)
- **Faire** : T9 (150 diapos), puis 1 000 diapos si possible ; naviguer.
- **Attendu** : chargement < 1 s pour 150 ; pour 1 000 : pas de blocage, texte correct.
  *(Au-delà de ~1 000 diapos la liste dépasse 16 Ko : cas non vu en réel.)*
- **Relever** : délai de chargement : ______ s.
- ☐ OK ☐ KO — notes :

### R-37 · Présentation importée PowerPoint/PDF (P3)
- **Faire** : T10.
- **Attendu** : texte affiché s'il existe ; texte vide pour une diapo image ; noter tout comportement
  inattendu.
- ☐ OK ☐ KO — notes :

---

## 4. Résilience (coupures, pannes)

Règle attendue : à la perte de connexion le **texte reste affiché 2 s** (pas de clignotement sur
micro-coupure), puis l'écran passe à vide ; à la reconnexion le texte courant revient **tout seul**.
Le délai se règle : `lost_grace_seconds` dans `config.json` ou `--grace`.

### R-40 · Coupure Wi‑Fi du Mac (P1)
- **Faire** : avec un texte affiché, couper le Wi‑Fi du Mac. Variantes de durée : **~1 s, ~5 s, ~30 s**
  (commande : `networksetup -setairportpower en0 off && sleep 2 && networksetup -setairportpower en0 on`,
  interface à vérifier avec `networksetup -listallhardwareports`).
- **Attendu** : ~1 s → **aucun clignotement** ; ~5 s et ~30 s → texte masqué après 2 s, **retour
  automatique** dès que le réseau revient.
- **Relever** : délai entre le retour du réseau et le texte affiché : ______ s ; la valeur de 2 s convient-elle ?
- ☐ OK ☐ KO — notes :

### R-41 · Fermeture puis réouverture d'EW (P1)
- **Faire** : quitter EW normalement, attendre 20 s, le rouvrir et remettre une diapo en direct.
- **Attendu** : texte masqué après 2 s ; reconnexion et affichage **sans toucher à l'application**.
- **Relever** : délai total : ______ s.
- ☐ OK ☐ KO — notes :

### R-42 · Plantage d'EW (P1)
- **Faire** : terminer le processus EW par le Gestionnaire des tâches.
- **Attendu** : comme R-41 (aucun texte périmé dans OBS, reconnexion automatique).
- ☐ OK ☐ KO — notes :

### R-43 · **Coupure silencieuse** (P1, le plus risqué)
- **Faire** : avec un texte affiché, **débrancher le câble réseau du PC EW** (ou couper son Wi‑Fi) sans
  fermer EW ni toucher au Mac.
- **Attendu** : la perte est détectée par les heartbeats / le keepalive TCP en **≤ ~30 s** (réglage : 10 s
  de silence puis 3 sondes de 3 s) ; texte masqué ; reconnexion automatique au retour du câble.
  *(Jamais observé en réel : le comportement exact dépend de l'OS.)*
- **Relever** : durée entre le débranchement et le masquage du texte : ______ s ; reconnexion : ______ s.
- ☐ OK ☐ KO — notes :

### R-44 · Veille du Mac et du PC EW (P2)
- **Faire** : mettre le Mac en veille 1 min puis réveiller ; idem pour le PC EW.
- **Attendu** : retour automatique à l'affichage correct (peut demander quelques secondes).
- ☐ OK ☐ KO — notes :

### R-45 · Changement de réseau (P3)
- **Faire** : passer le Mac d'un Wi‑Fi à un autre (ou câble ↔ Wi‑Fi).
- **Attendu** : reconnexion automatique.
- ☐ OK ☐ KO — notes :

### R-46 · Redémarrage de la box / du routeur (P3)
- **Attendu** : reconnexion automatique, même si les adresses IP ont changé (cf. R-12).
- ☐ OK ☐ KO — notes :

### R-47 · Deux clients avec la même identité (P3)
- **Faire** : lancer deux instances sur le même Mac (autre port web) avec la même configuration.
- **Attendu** : noter ce qui se passe (EW peut en refuser une ou les deux accepter). Informatif.
- ☐ noté — comportement observé :

### R-48 · Arrêt de l'application (P2)
- **Faire** : Ctrl+C avec un texte affiché ; relancer.
- **Attendu** : sortie propre (code 0), le texte disparaît d'OBS ; aucun processus résiduel.
- ☐ OK ☐ KO — notes :

---

## 5. Affichage dans OBS (Mac)

### R-50 · Mise en place des sous-titres sur toutes les scènes caméra (P1)
- **Faire** : créer **une** source *Navigateur* `http://localhost:8000/?lines=4` (taille du bandeau, ex.
  1920 × 360), placée en bas ; l'ajouter à chaque scène caméra par *Ajouter une source existante*.
- **Attendu** : le même texte apparaît sur toutes les scènes caméra, en blanc sur gris translucide ; le
  fond de la page est transparent ; **un seul** navigateur connecté (le journal le dit).
- ☐ OK ☐ KO — notes :

### R-51 · Changement de scène (P1)
- **Faire** : passer d'une scène caméra à une autre pendant qu'un texte est affiché.
- **Attendu** : le texte **reste** affiché sans clignotement ni rechargement visible ; option « éteindre la
  source quand elle n'est pas visible » **décochée**.
- ☐ OK ☐ KO — notes :

### R-52 · Emojis et polices dans OBS (P1)
- **Faire** : T5 dans le navigateur d'OBS (CEF, différent de Chromium).
- **Attendu** : emojis en couleur, accents corrects. Sinon noter lesquels manquent.
- ☐ OK ☐ KO — notes :

### R-53 · Lisibilité réelle à l'antenne (P1)
- **Faire** : tester sur l'image caméra réelle : contraste, taille, position, marge (`valign`, `padding`,
  `margin`, `radius`, `bg`).
- **Relever** : URL finale retenue : ______________________________
- ☐ OK ☐ KO

### R-54 · Mise à jour de la page (P3)
- **Faire** : modifier un paramètre d'URL dans OBS.
- **Attendu** : pris en compte tout de suite (pas de cache ancien).
- ☐ OK ☐ KO

### R-55 · Charge machine (P2)
- **Faire** : pendant 10 min avec changements de diapo, observer le processeur du Mac (Moniteur d'activité)
  et le nombre d'images OBS perdues.
- **Attendu** : processeur de l'application négligeable (< 5 %), aucune image perdue due à la page.
- **Relever** : valeurs : ______
- ☐ OK ☐ KO

### R-56 · Aperçu du style sans EW (P3)
- **Faire** : `http://localhost:8000/?demo=1` et `?demo=Mon%20texte` dans OBS.
- **Attendu** : aperçu immédiat, utilisable pour régler le style.
- ☐ OK ☐ KO

---

## 5b. Fenêtre de l'application

### R-80 · Ouverture de la fenêtre sur le Mac (P1)
- **Faire** : `python -m ew_to_obs` avec le Python que vous utiliserez réellement.
- **Attendu** : la fenêtre s'ouvre (~720 × 440). Sinon un message explique comment installer tkinter
  (Python de python.org, ou `brew install python-tk`) et propose `--headless` ; code de sortie 3.
- **Relever** : quel Python (python.org / Homebrew / système) ; version de Tk affichée par
  `python -c "import tkinter; print(tkinter.TkVersion)"` (8.6 attendu).
- ☐ OK ☐ KO — notes :

### R-81 · Premier lancement dans la fenêtre (P1)
- **Préparer** : configuration vide (`--config-dir` neuf).
- **Faire** : saisir le nom du PC EW, **Appliquer** (ou Entrée).
- **Attendu** : message d'aide « Aucun PC EasyWorship configuré… » avant la saisie ; après Appliquer :
  pastille orange *Recherche…* puis *En attente d'acceptation* avec le message en gras
  « Dans EasyWorship, acceptez la télécommande « EasyWorship vers OBS » » ; après acceptation :
  pastille verte *Connecté à EasyWorship*. Le PC est mémorisé (relancer : plus rien à saisir).
- ☐ OK ☐ KO — notes :

### R-82 · Pastille et messages de perte (P1)
- **Faire** : couper le Wi‑Fi du Mac, puis le remettre (ou fermer/rouvrir EW).
- **Attendu** : pastille rouge *Connexion perdue : reconnexion automatique* avec le détail de l'essai
  suivant, puis verte au retour. Les couleurs sont lisibles (orange/rouge/vert/gris).
- ☐ OK ☐ KO — notes :

### R-83 · Copier l'adresse et la coller dans OBS (P1)
- **Faire** : bouton **Copier** puis coller dans l'adresse de la source navigateur d'OBS.
- **Attendu** : « Adresse copiée » apparaît 2 s ; le collage donne `http://localhost:8000/?lines=4`
  entière (aucun caractère manquant).
- ☐ OK ☐ KO — notes :

### R-84 · Réglages de la page et port (P2)
- **Faire** : changer « Réglages de la page » (ex. `lines=6&valign=bottom`) et « Port de la page »
  (ex. 8001), **Appliquer**.
- **Attendu** : l'adresse affichée suit la saisie (seulement si valide) ; après Appliquer la connexion
  redémarre et la page répond sur le nouveau port ; **il faut recoller la nouvelle adresse dans OBS**
  (OBS ne la change pas tout seul). Valeurs conservées au relancement.
- ☐ OK ☐ KO — notes :

### R-85 · Port de la page déjà utilisé (P2)
- **Faire** : occuper le port (une autre instance, ou `python -m http.server 8000`), lancer la fenêtre.
- **Attendu** : bandeau rouge « Le port 8000 est déjà utilisé… » ; la connexion à EW fonctionne quand
  même ; après changement de port + Appliquer, le bandeau disparaît.
- ☐ OK ☐ KO — notes :

### R-86 · Saisies invalides (P3)
- **Faire** : nom vide, `http://x`, port `abc` / `70000`, réglages avec espace ou `<`.
- **Attendu** : message rouge précis pour chacun, **rien n'est modifié ni enregistré** ; corriger fait
  disparaître le message.
- ☐ OK ☐ KO

### R-87 · Compteur de navigateurs et aperçu (P1)
- **Faire** : avec OBS ouvert et la source partagée sur plusieurs scènes ; changer de diapo.
- **Attendu** : « Navigateurs (OBS) » indique **1 connecté** (une seule source partagée) ; ouvrir la
  même adresse dans Safari/Chrome le fait passer à 2 ; l'**aperçu** montre le texte diffusé, `— rien
  d'affiché —` quand masqué, `— diapo sans texte —` pour une diapo vide.
- **Relever** : compteur observé avec la source dans N scènes : ______
- ☐ OK ☐ KO — notes :

### R-88 · Fermeture propre (P1)
- **Faire** : fermer par la croix, par **Quitter**, par **Cmd+Q** (essayer les trois, relancer à chaque fois).
- **Attendu** : le texte disparaît d'OBS, aucun processus Python résiduel (Moniteur d'activité), le
  port web est libre immédiatement (relance sans erreur), la télécommande se déconnecte d'EW.
- ☐ OK ☐ KO — notes :

### R-89 · Fenêtre cachée, minimisée ou derrière OBS (P1)
- **Faire** : pendant 30 min, laisser la fenêtre **minimisée / masquée / derrière OBS**, avec des
  changements de diapo réguliers (macOS peut ralentir une application en arrière-plan : « App Nap »).
- **Attendu** : délai d'affichage inchangé (< 1 s, cf. R-21), aucune reconnexion intempestive.
- **Relever** : délai médian en arrière-plan ______ s. Si dégradé : noter si le problème disparaît avec
  `--headless` lancé dans un terminal.
- ☐ OK ☐ KO — notes :

### R-90 · Apparence (P3)
- **Faire** : mode sombre de macOS, écran Retina, redimensionnement de la fenêtre, texte très long dans
  l'aperçu.
- **Attendu** : tout reste lisible (boutons, champs, pastille) ; aucun texte coupé en taille normale.
- ☐ OK ☐ KO — notes :

### R-91 · « Ouvrir le dossier du journal » (P2)
- **Attendu** : le Finder (ou l'explorateur) s'ouvre sur le dossier de §0.4, contenant `ew_to_obs.log`.
- ☐ OK ☐ KO

### R-92 · Fenêtre sous Windows (P2)
- **Faire** : mêmes tests R-81, R-83, R-88 sur Windows (Python de python.org, tkinter inclus).
- ☐ OK ☐ KO — notes :

### R-93 · Sans fenêtre possible (P3)
- **Faire** : sur une machine sans tkinter, `python -m ew_to_obs`.
- **Attendu** : message clair + commande `--headless` ; code 3.
- ☐ OK ☐ KO

---

## 6. Longue durée

### R-60 · Un service complet (≈ 3 h) (P1)
- **Faire** : laisser tourner pendant un vrai culte ou une répétition complète, avec usage normal d'EW.
- **Attendu** : aucun plantage, aucun texte erroné, mémoire et processeur stables, journal raisonnable.
- **Relever** : durée ______ ; nombre de reconnexions dans le journal ______ ; taille du journal ______ ;
  mémoire au début / à la fin ______ / ______.
- ☐ OK ☐ KO — incidents :

### R-61 · Plusieurs jours (P2)
- **Attendu** : si l'application reste ouverte entre deux cultes, elle se retrouve fonctionnelle (retour de
  veille, EW relancé).
- ☐ OK ☐ KO — notes :

---

## 7. Variante : application sur le PC Windows d'EW

*(Optionnel, à étudier : démarrage automatique en fin de projet.)*

### R-70 · Connexion en local (P2)
- **Faire** : sur le PC EW, `python -m ew_to_obs --host localhost --serve`.
- **Attendu** : découverte mDNS et connexion en local réussies (non testé : le mDNS en boucle locale peut
  se comporter différemment).
- ☐ OK ☐ KO — notes :

### R-71 · OBS (Mac) lit la page du PC EW (P2)
- **Faire** : `--web-bind 0.0.0.0` ; dans OBS : `http://NOM_DU_PC_EW:8000/?lines=4`.
- **Attendu** : affichage identique ; règle de pare-feu Windows pour le port 8000 si besoin (noter laquelle).
- ☐ OK ☐ KO — notes :

### R-72 · Sécurité de l'écoute réseau (P2)
- **Attendu** : par défaut (`127.0.0.1`) la page n'est **pas** joignable depuis un autre appareil ; avec
  `0.0.0.0` elle l'est (donc à réserver au réseau de confiance : aucune authentification).
- ☐ OK ☐ KO

### R-73 · Autres systèmes (P3)
- **Faire** : lancer sur Windows et Linux si utile (la suite de tests passe déjà sur Ubuntu, Windows, macOS).
- ☐ noté

---

## 8. Captures complémentaires (`tools/ew_capture.py`)

Pour enrichir les tests automatiques (cas jamais capturés). Toujours avec `--redact` avant de partager.

```
python tools/ew_capture.py NOM_DU_PC_EW --reconnect --duration 300 --redact
```

| ☐ | Cas à capturer (noter l'heure de chaque action) |
|---|---|
| ☐ | Coupure silencieuse (R-43), avec le moment du débranchement |
| ☐ | Attente `notPaired` de 10 min (R-04) et fermeture éventuelle par EW |
| ☐ | Plantage d'EW (R-42) |
| ☐ | Verset biblique et diapo avec note + référence (R-31, R-32) |
| ☐ | Présentation importée PowerPoint (R-37) |
| ☐ | Présentation de 1 000 diapos (R-36) |
| ☐ | Diapo avec média + texte (R-27) |

---

## 9. Hypothèses jamais vérifiées en réel (à confirmer par la recette)

| # | Hypothèse | Test |
|---|---|---|
| H1 | La résolution IPv4 seule rend la connexion par nom aussi rapide que par IP | R-10, R-11 |
| H2 | La dernière IP mémorisée évite toute saisie après un changement DHCP | R-12 |
| H3 | Le keepalive TCP détecte une coupure silencieuse en ≲ 30 s sur macOS **et** Windows | R-43 |
| H4 | EW garde la connexion `notPaired` ouverte au-delà de 40 s | R-04 |
| H5 | Une identité révoquée est ré-acceptable sans relancer l'application | R-06 |
| H6 | Le navigateur d'OBS (CEF) rend les emojis et la taille de texte comme Chromium | R-52, R-28 |
| H7 | 2 s de délai de grâce conviennent aux coupures réelles | R-40 |
| H8 | Une présentation de 1 000 diapos se charge correctement | R-36 |
| H9 | Le mDNS fonctionne en boucle locale (variante app sur le PC EW) | R-70 |
| H10 | Un changement de contenu en direct est repéré par EW dans un délai raisonnable | R-33 |
| H11 | Aucune fenêtre de pare-feu bloquante n'apparaît | R-15 |
| H12 | Une fenêtre masquée ou en arrière-plan ne ralentit pas l'affichage (App Nap de macOS) | R-89 |
| H13 | tkinter est disponible et la fenêtre s'affiche correctement avec le Python choisi sur le Mac | R-80, R-90 |
| H14 | Copier, fermer par Cmd+Q et le dossier du journal se comportent normalement sur macOS et Windows | R-83, R-88, R-91, R-92 |

## 10. Ce qui est déjà couvert automatiquement (rappel)

211 tests : décodage des trames coupées n'importe où, rejeu de 13 captures réelles (diapos, appairage,
révocation, coupures, relance d'EW, vides, médias, emojis, 150 diapos), client contre un faux EW sur
TCP réel (appairage, reconnexion, délai de grâce, heartbeats), découverte IPv4 d'abord et mDNS parallèle,
configuration et journal, ligne de commande, serveur web (WebSocket), page dans Chromium (taille du
texte, texte brut, URL, reconnexion), service et **fenêtre** (états, validation des saisies, copie,
fermeture) sous Linux avec un écran virtuel. **Aucun de ces tests n'a touché un vrai EasyWorship ni OBS.**

## 11. Rapport de recette à renvoyer

☐ Tableau §0.1 rempli · ☐ tests cochés avec mesures · ☐ `ew_to_obs.log` (sans texte de diapo) ·
☐ `config.json` **avec `client_id` masqué** · ☐ captures `--redact` du §8 · ☐ URL OBS retenue (R-53) ·
☐ liste des écarts ressentis (affichage, délais, confort).
