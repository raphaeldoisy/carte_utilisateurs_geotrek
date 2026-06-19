<img width="1826" height="879" alt="image" src="https://github.com/user-attachments/assets/1f43ca8b-eec3-4b82-89a6-1260d2065d75" />


*Dernière mise à jour : 19/06/2026 *

# Description succincte

Le projet permet de suivre et d'ajouter facilement de nouvelles structures utilisant Geotrek.

La liste ne se veut pas exhaustive car il est difficile d'aller chercher toutes les structures utilisant Geotrek dans son ensemble.

On peut passer sur les objets de la carte pour avoir leur nom.

On a le nombre d'objets par type et le nombre total d'objets.



# Comment a été faite cette base de données?

Basé sur les cartes utilisateurs faite avec QGIS (2025 et 2021).

Basé sur les structures ayant intégré l'agrégateur IGN


# Comment ajouter un objet ?

C'est dans cette interface qu'il est possible de gérer la couche d'objets. Nous pouvons recherche, désélectionner, sélectionner les objets que l'on souhaite voir.\
Les objets proposés à la sélection etc sont basés sur [data.gouv.fr](https://data.gouv.fr) et sont déposés dans data/source\
Les autres sont des couches statiques qu'il faut changer dans QGIS (ex: autres_ot, pnx...)

<img width="1148" height="879" alt="image" src="https://github.com/user-attachments/assets/72391ea0-3d47-4f4b-a350-80d790e38abd" />




Le bouton "Générer *objet*.geojson" va écraser le fichier geojson existant pour la carte et donc le remplacer.



Il est aussi possible d'importer une liste d'objets. Les objets recensés de base qui correspondent à des objets déjà sélectionnés seront alors ajoutés automatiquement. Les autres objets seront affichés à l’utilisateur afin qu'il puisse vérifier par lui-même si l'algo a raté quelque chose (comme un accent, un tiret ....)


