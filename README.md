# 🗺️ Carte des Utilisateurs Geotrek

![Interface de la carte](https://github.com/user-attachments/assets/1f43ca8b-eec3-4b82-89a6-1260d2065d75)
*Dernière mise à jour : 19/06/2026*


## 📌 Description succincte

Le projet **Carte des Utilisateurs Geotrek** permet de :
- **Suivre et ajouter facilement** de nouvelles structures utilisant Geotrek.
- **Visualiser** les objets sur une carte interactive en passant la souris sur eux pour afficher leur nom.
- **Afficher** le nombre d'objets par type et le **nombre total d'objets** sur la carte.

> ⚠️ **Note** : La liste des structures n'est pas exhaustive, car il est difficile de recenser toutes les structures utilisant Geotrek dans son ensemble. De plus le projet github vient avec les Geojson de base pour avoir la carte avec la dernière mise à jour.


## 🛠️ Installation

1. **Cloner le dépôt**
 ```bash
 git clone https://github.com/raphaeldoisy/carte_utilisateurs_geotrek.git
```

2. **Créer un environnement virtuel**

Dans votre dossier : 
```bash

python -m venv venv
```
3. **Activer l'environnement virtuel**
```bash
# Sur Linux/macOS
source venv/bin/activate

# Sur Windows
venv\Scripts\activate
```

4. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

5. **Lancer l'application**
```bash
# Pour le développement
python app.py
```
Accéder à l'application
Ouvrir un navigateur à l'adresse : http://localhost:5000

## 🌍 Gestion des objets
Il est possible de gérer les couches d’objets en appuyant sur les bouton du nom de l'objet sur la page principale et les fonctionnalités sont les suivantes :
* Rechercher les objets
* Désélectionner ou sélectionner les objets à afficher sur la carte via le bouton "Générer le ***.json"
* Importer des objets en masse via un fichier csv/txt/Geojson

<img width="1148" height="879" alt="Capture d’écran du 2026-06-19 18-13-31" src="https://github.com/user-attachments/assets/8b0ad29e-60f2-42ef-95ac-639b712c74d7" />

## 📊 Origine de la base de données
La base de données a été construite à partir de :
* Cartes utilisateurs réalisées avec QGIS (versions 2025 et 2021).
* Structures ayant intégré l’agrégateur IGN.

Les couches suivantes sont gérées via URL de data.gouv.fr (qu'on retrouve configuré dans app.py sous le paramètre urlData). Elles peuvent être mises à jour via l'application :
* Region
* Département
* EPCI

Les couches suivantes sont gérés en Geojson (dans le dossier data) et ne peuvent pas être mises à jour via l'application. Il est nécessaire d'intervenir avec un logiciel comme QGIS :
* PNX
* Autres_OT

Le couche PNR est un shape dans le dossier data dont il est possible de mettre à jour via l'application


