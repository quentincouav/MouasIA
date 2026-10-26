# SAE Maouss IAx

**Ce qu'on étudie ici : comment les lecteurs naviguent entre les pages que notre tri associe à la présidentielle.**
Ces pages sont très variées : un candidat ou un parti, mais aussi un sujet de débat (retraites, immigration, laïcité…), une loi, une institution, et parfois des pages qui n'ont rien de politique et que le tri a retenues par erreur.
On regarde sur quelles pages les gens arrivent, d'où ils viennent (un moteur de recherche, une autre page Wikipédia…) et vers quelles pages ils partent ensuite. On garde un historique mois par mois, ce qui permet de comparer les mois entre eux.

## Ce que ça fait

1. **On récupère les données.** Chaque mois, Wikimedia publie le *clickstream* de Wikipédia FR, c'est-à-dire les « l'utilisateur était sur la page A et a cliqué vers la page B », avec le nombre de clics.
2. **On garde les pages qui semblent liées au sujet.** On les range dans nos catégories (Institutions, Élections, Partis, Personnalités, Débats publics). Pour ça, on utilise une liste de mots-clés et la liste de pages trouvées par le crawler d'un autre groupe ([find_relevant_wiki_pages](https://gitlab.cri.epita.fr/arthur.magnin/find_relevant_wiki_pages)). Les pages trouvées par le crawler mais qu'aucun de nos mots-clés ne reconnaît vont dans un thème à part, « Autres sujets politiques ».
3. **On construit un graphe.** Les pages sont les nœuds et les clics entre pages sont les liens. On calcule ensuite pour chaque page :
   - son importance dans le réseau ;
   - son audience estimée ;
   - sa communauté ;

   Le graphe contient aussi les pages voisines, celles d'où viennent ou vers lesquelles partent les lecteurs, même si notre tri ne les a pas retenues.
4. **On met tout à disposition** grâce à une petite API. Les autres groupes peuvent récupérer nos résultats sans relancer le calcul.
5. **Tout se met à jour tout seul.** Quand l'API tourne, elle vérifie toutes les 12 h si un nouveau mois est sorti et le traite automatiquement.


## Utilisation

Le pipeline et l'API se lancent depuis le dossier `script/`.

**Traiter un mois de données :**

```bash
cd script
python pipeline.py                              # dernier mois disponible
python pipeline.py --month 2026-09              # un mois précis
python pipeline.py --from 2026-01 --to 2026-09  # plusieurs mois d'un coup
```

Attention : le fichier d'un mois est assez gros, le premier lancement prend donc un peu de temps. Ce fichier est gardé dans `data/raw/`.

**Lancer l'API :**

```bash
cd script
python main.py
```

| Route | Ce qu'elle renvoie |
|---|---|
| `/months` | Les mois déjà traités |
| `/themes` | Nos thèmes et leurs mots-clés |
| `/summary` | Le résumé d'un mois (nombre de pages, top 10…) |
| `/data/{n}` | Les `n` lignes du clickstream les plus cliquées (clics entre pages et arrivées depuis l'extérieur) |
| `/graph` | Le graphe (à afficher avec D3.js, Gephi, etc.). Par défaut, il ne contient que les pages retenues par notre tri et les liens d'au moins 50 clics, sinon il est illisible. Pour changer ce seuil : `?min_clics=10` |
| `POST /update` | Lance le traitement d'un mois (le dernier disponible par défaut) |
| `/update/jobs` | L'état des traitements en cours et récents |

Pour `/summary`, `/data`, `/graph` et `POST /update`, on peut choisir le mois avec `?month=2026-09`. Sans ce paramètre, c'est le dernier mois traité (ou, pour `POST /update`, le dernier mois publié) qui est utilisé.

Si vous retraitez avec `pipeline.py --force` un mois que l'API a déjà affiché, redémarrez l'API : sinon elle continue de montrer l'ancienne version. Un nouveau mois, lui, apparaît sans redémarrage.

## Les données qu'on produit

Elles sont dans `data/processed/<mois>/`, un dossier par mois :

- `metrics.csv` : **le fichier le plus utile pour les autres groupes**, une ligne par page retenue par notre tri ;
- `graph.json` : le graphe complet, avec les pages voisines non retenues (marquées `hors_theme`) ;
- `edges.csv.gz` : les lignes du clickstream qu'on a gardées (clics entre pages, et arrivées depuis un moteur de recherche ou un autre site) ;
- `summary.json` : le résumé du mois.

Il y a aussi `data/processed/history.csv`, qui regroupe tous les mois dans un seul fichier. C'est pratique pour suivre une page dans le temps.

Colonnes principales de `metrics.csv` :

| Colonne | Signification |
|---|---|
| `page` | Titre de la page (comme dans l'URL Wikipédia) |
| `theme` | Thème auquel on l'a rattachée |
| `rang` / `pagerank` | Importance de la page dans le réseau (1 = la plus centrale) |
| `clics_entrants` | Clics venant d'autres pages Wikipédia |
| `entrees_externes` | Arrivées depuis l'extérieur (moteurs de recherche, autres sites, accès direct…) |
| `audience_estimee` | Les deux additionnés |
| `communaute` | Numéro de la communauté de la page. Attention : il est recalculé chaque mois, donc le groupe 3 de janvier n'est pas forcément le groupe 3 de février |
| `pertinence` | Score donné par le crawler de l'autre groupe (vide si la page n'est pas dans sa liste) |

## Limites

- **Un seul point par mois.** Wikimedia ne publie le clickstream qu'une fois par mois, donc on ne voit pas ce qui se passe jour par jour.
- **Les petits flux sont invisibles.** Wikimedia retire les transitions de moins de 10 clics, pour protéger la vie privée.
- **On ne mesure que l'attention du public.** Les modifications des pages, les contributeurs et les pages de discussion ne sont pas traités ici.

## Tests

À lancer depuis la racine du repo (depuis `script/`, pytest ne trouve aucun test) :

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests utilisent de fausses données et n'ont pas besoin d'internet. Un test est sauté si le submodule n'est pas téléchargé, c'est normal.
