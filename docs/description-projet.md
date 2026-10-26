# SAE Maouss'IAx : description

## Observatoire des dynamiques informationnelles sur Wikipédia France dans le contexte de l'élection présidentielle de 2027

## Contexte

Les périodes électorales s'accompagnent généralement d'une forte intensification des activités informationnelles. Wikipédia constitue un cas d'étude particulièrement intéressant car il s'agit d'une source d'information largement consultée, ouverte aux contributions de tous et dont l'ensemble de l'historique éditorial est publiquement accessible.

Contrairement à une idée répandue, les potentielles tentatives d'influence informationnelle ne se limitent pas aux pages des candidats. Elles peuvent également concerner des pages thématiques fortement liées aux débats de campagne, telles que :

- immigration ;
- sécurité ;
- transition énergétique ;
- nucléaire ;
- dette publique ;
- chômage ;
- éducation ;
- santé ;
- Ukraine, Iran ;
- retraites ;
- institutions politiques.

Cette liste n'est pas exhaustive. Nous pouvons nous attendre également à certaines révisions historiques ou appropriation / détournement de concepts / symboles.

## Objectifs

L'objectif du projet est de concevoir un observatoire basé sur l'intelligence artificielle permettant de suivre l'évolution de Wikipédia France, de détecter des comportements atypiques, d'analyser leurs causes, de quantifier l'incertitude associée aux alertes générées et de fournir des outils d'explication et de visualisation.

Le projet s'inscrit dans un cadre de déploiement continu où de nouvelles données apparaissent quotidiennement après la phase d'apprentissage.

Le projet vise à construire une plateforme collaborative permettant d'étudier plusieurs signaux complémentaires décrivant l'évolution de Wikipédia.

Les étudiants devront notamment **construire une représentation dynamique de Wikipédia** à partir :

- des pages ;
- des contributeurs ;
- des catégories ;
- des liens entre pages ;
- des historiques d'édition ;
- des données de consultation.

Cette (ou ces) représentation(s) sera ensuite utilisée pour :

- **Détecter des comportements atypiques**, par exemple :
  - augmentation inhabituelle de l'activité sur certaines pages ;
  - apparition soudaine de nouveaux contributeurs ;
  - guerres d'édition ;
  - émergence de nouvelles communautés de contributeurs ;
  - évolution rapide de sous-graphes thématiques ;
  - propagation inhabituelle des modifications.
- **Étudier plusieurs familles de signaux** :
  - signal éditorial ;
  - signal structurel ;
  - signal sémantique ;
  - signal communautaire ;
  - signal d'attention du public.
- **Construire des mécanismes d'IA de confiance** :
  - quantification de l'incertitude ;
  - calibration ;
  - prédiction conforme ;
  - explicabilité des alertes.
- **Développer un observatoire interactif**, capable de :
  - suivre l'évolution de Wikipédia dans le temps ;
  - visualiser les alertes ;
  - explorer les explications produites par les modèles.

## Sources de données

### Historique des modifications Wikipédia

Contient notamment :

- auteur de la modification ;
- date ;
- commentaire ;
- contenu modifié ;
- taille de la modification.

Sources :

- MediaWiki API : <https://www.mediawiki.org/wiki/API:Main_page>
- Wikipedia Database Dumps : <https://en.wikipedia.org/wiki/Wikipedia:Database_download>

### Données de consultation

Permettent d'observer l'intérêt du public pour certaines pages.

Source :

- Wikimedia Pageviews API : <https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/>

### Clickstream Wikipédia

Décrit les transitions réelles des utilisateurs entre pages.

Source :

- <https://dumps.wikimedia.org/other/clickstream/readme.html> (pas sûr pour pages françaises)

### Structure des pages Wikipédia

- hyperliens ;
- catégories ;
- modèles.

Source :

- Wikipedia Database Dumps : <https://en.wikipedia.org/wiki/Wikipedia:Database_download>

### Pages de discussion

Permettent d'étudier les controverses et les conflits éditoriaux.

Source : MediaWiki API.

## Compétences à évaluer

- Produire niveau avancé
- Concevoir niveau avancé
- Agir niveau avancé
- Gérer niveau avancé

## Organisation du projet

### Principes

Le projet n'est pas conçu comme un ensemble de groupes travaillant sur des solutions concurrentes.

Au contraire, toute la promotion contribue à la construction d'un observatoire unique.

Chaque groupe est responsable d'un type de signal ou d'une composante scientifique spécifique.

Les résultats produits doivent être mutualisés pour pouvoir alimenter une plateforme commune.

**La mutualisation constitue un objectif pédagogique explicite du projet.**

Chaque groupe doit :

- produire des artefacts documentés ;
- publier ses jeux de caractéristiques dans un format commun ;
- documenter ses API ;
- permettre leur réutilisation par les autres groupes.

Une partie de l'évaluation pourra porter sur :

- la qualité de la contribution scientifique du groupe ;
- la qualité de la mutualisation ;
- la capacité des autres groupes à réutiliser les productions réalisées.

Ainsi, aucun groupe ne travaille isolément : chacun devient spécialiste d'un signal particulier tandis que l'ensemble de la promotion contribue à la construction d'un observatoire global des dynamiques informationnelles de Wikipédia France dans le contexte de l'élection présidentielle de 2027.
