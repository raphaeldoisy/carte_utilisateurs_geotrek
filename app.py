from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import folium
import geopandas as gpd
import json
import os
import csv
import re
import unicodedata
from difflib import get_close_matches
from io import TextIOWrapper
import gc
import requests
import tempfile
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'ta_cle_secrete_ici'

# Chemin vers le dossier data
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Configuration des types d'objets (EPCI, Régions, PNR, etc.)
OBJECT_TYPES = {
    'region': {
        'urlData': "https://object.data.gouv.fr/contours-administratifs/2025/geojson/regions-1000m.geojson",
        'column': "nom",
        'color': "#6a0000",
        'tooltip_fields': ['nom'],
        'display_name': "Région",
        'selectable': True
    },
    'departement': {
        'urlData': "https://object.data.gouv.fr/contours-administratifs/2025/geojson/departements-1000m.geojson",
        'column': "nom",
        'color': "#d96f43",
        'tooltip_fields': ['nom'],
        'display_name': "Département",
        'selectable': True
    },
    'epci': {
        'urlData': "https://object.data.gouv.fr/contours-administratifs/2025/geojson/epci-1000m.geojson",
        'column': "nom",
        'color': "#f5f5f5",
        'tooltip_fields': ['nom'],
        'display_name': "EPCI",
        'selectable': True  # <-- Indique si la couche est sélectionnable
    },
    'pnx': {
        'color': "#1a341f",
        'tooltip_fields': ['NOM'],
        'display_name': "Parc National Français",
        'selectable': False
    },
    'pnx_belge': {
        'color': "#1a341f",
        'tooltip_fields': ['NOM'],
        'display_name': "Parc National Belge",
        'selectable': False
    },
    'pnx_italy': {
        'color': "#1a341f",
        'tooltip_fields': ['NOM'],
        'display_name': "Parc National Italien",
        'selectable': False
    },
    'pnr': {
        'urlData': "data/source/pnr_polygonPolygon.shp",
        'column': "name",
        'color': "#749278",
        'tooltip_fields': ['name'],
        'display_name': "Parc Naturel Régional",
        'selectable': True
    },
    'autres_ot': {
        'color': "#FF92FA",
        'tooltip_fields': ['nom'],
        'display_name': "Autres et OT",
        'selectable': False
    }
    
    
    # Ajoute d'autres types ici (ex: départements, parcs_nationaux, etc.)
}

# Dictionnaire pour stocker les données de chaque type
data = {}

# Ordre de chargement des couches (du fond vers le premier plan)
LAYER_ORDER = [
            # 1. Chargé en premier (fond)
    'autres_ot',
    'pnr',
    'pnx',
    'pnx_belge',
    'pnx_italy',
    'epci',
    'departement',
    'region'
]

# Dossier de cache (créé automatiquement)
CACHE_DIR = Path("temp_shapefile_cache")
CACHE_DIR.mkdir(exist_ok=True)

def load_remote_file(url_or_path, cache_expiry_days=7):
    """
    Charge un fichier (GeoJSON ou Shapefile) depuis une URL ou un chemin local.
    Args:
        url_or_path: URL ou chemin local du fichier
        cache_expiry_days: Durée de validité du cache (en jours)
    Returns:
        GeoDataFrame
    """
    # Si c'est une URL
    if isinstance(url_or_path, str) and url_or_path.startswith(('http://', 'https://')):
        file_hash = hashlib.md5(url_or_path.encode()).hexdigest()

        # Détecter le type de fichier
        if url_or_path.endswith('.geojson'):
            # Cas GeoJSON (fichier unique)
            cache_path = CACHE_DIR / f"{file_hash}.geojson"
            if cache_path.exists():
                mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
                if datetime.now() - mod_time < timedelta(days=cache_expiry_days):
                    return gpd.read_file(str(cache_path))

            # Télécharger le GeoJSON
            response = requests.get(url_or_path, timeout=30)
            response.raise_for_status()
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            return gpd.read_file(str(cache_path))

        else:
            cache_dir = CACHE_DIR / file_hash
            cache_dir.mkdir(exist_ok=True)
            required_extensions = ['.shp', '.shx', '.dbf']

            # Vérifier si tous les fichiers requis sont en cache
            all_cached = True
            for ext in required_extensions:
                cache_path = cache_dir / f"{file_hash}{ext}"
                if not cache_path.exists():
                    all_cached = False
                    break
                mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
                if datetime.now() - mod_time > timedelta(days=cache_expiry_days):
                    all_cached = False
                    break

            if all_cached:
                return gpd.read_file(str(cache_dir / f"{file_hash}.shp"))
            base_url = url_or_path.rsplit('.', 1)[0]
            for ext in required_extensions:
                file_url = f"{base_url}{ext}"
                cache_path = cache_dir / f"{file_hash}{ext}"
                try:
                    response = requests.get(file_url, timeout=30)
                    response.raise_for_status()
                    with open(cache_path, 'wb') as f:
                        f.write(response.content)
                except requests.exceptions.RequestException as e:
                    raise Exception(f"Fichier {file_url} introuvable: {e}")

            return gpd.read_file(str(cache_dir / f"{file_hash}.shp"))

    else:
        # Chemin local (GeoJSON ou Shapefile)
        return gpd.read_file(url_or_path)
    
# Fonction pour normaliser les noms
def normalize_name(value):
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = re.sub(r"\b(communaute|communauté)\b", "", value)
    value = re.sub(r"\bde\b|\bdu\b|\bdes\b|\bd'\b|\ble\b|\bla\b|\bles\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())

# Fonction générique pour faire correspondre les noms
def match_name(name, name_list):
    if name in name_list:
        return name
    normalized_map = {normalize_name(e): e for e in name_list}
    key = normalize_name(name)
    if key in normalized_map:
        return normalized_map[key]
    close = get_close_matches(key, normalized_map.keys(), n=1, cutoff=0.85)
    if close:
        return normalized_map[close[0]]
    return None

# Charger les données pour chaque type d'objet
for obj_type, config in OBJECT_TYPES.items():
    try:
        file_path = config['urlData']  # Peut être une URL ou un chemin local

        # Charger depuis une URL ou un fichier local
        if isinstance(file_path, str) and file_path.startswith(('http://', 'https://')):
            gdf = load_remote_file(file_path)
        else:
            gdf = gpd.read_file(file_path)

        column = config['column']

        # Si la colonne configurée n'existe pas, essayer des alternatives
        if column not in gdf.columns:
            # Liste des noms de colonnes possibles pour les noms
            possible_columns = ['NOM', 'nom', 'NOM_PNR', 'nom_pnr', 'NAME', 'name', 'LIBELLE', 'libelle', 'NOM_DEP', 'NOM_SITE']
            for col in possible_columns:
                if col in gdf.columns:
                    column = col
                    break
            else:
                # Si aucune colonne ne correspond, prendre la première colonne de type string
                for col in gdf.columns:
                    if gdf[col].dtype == 'object':
                        column = col
                        break
                else:
                    raise ValueError(f"Aucune colonne de type 'nom' trouvée dans {config['urlData']}. Colonnes disponibles : {gdf.columns.tolist()}")

        obj_list = sorted(gdf[column].unique().tolist())
        data[obj_type] = {
            'gdf': gdf,
            'column': column,
            'list': obj_list,
            'total': len(obj_list),
            'color': config['color'],
            'tooltip_fields': config['tooltip_fields'],
            'display_name': config['display_name']
        }
        print(f"[SUCCESS] {obj_type} chargé avec la colonne '{column}' ({len(obj_list)} entrées).")

    except Exception as e:
        print(f"[ERREUR] {obj_type} : {e}")
        data[obj_type] = {
            'gdf': None,
            'column': None,
            'list': [],
            'total': 0,
            'color': config['color'],
            'tooltip_fields': config['tooltip_fields'],
            'display_name': config['display_name']
        }

# Fonction pour convertir les timestamps
def convert_timestamps(obj):
    if hasattr(obj, 'isoformat'):  # Works for pandas.Timestamp and datetime.datetime
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Fonction générique pour charger les features GeoJSON
def load_geojson_features(data_dir):
    features = []

    # Lister tous les fichiers GeoJSON dans le dossier
    geojson_files = [f for f in os.listdir(data_dir) if f.endswith('.geojson')]

    # Trier les fichiers selon LAYER_ORDER
    def get_layer_order(filename):
        layer_name = os.path.splitext(filename)[0]
        try:
            return LAYER_ORDER.index(layer_name)  # Retourne l'index dans LAYER_ORDER
        except ValueError:
            return len(LAYER_ORDER)  # Place les couches non listées à la fin

    # Trier les fichiers selon l'ordre défini
    geojson_files_sorted = sorted(geojson_files, key=get_layer_order)

    for filename in geojson_files_sorted:
        if filename.endswith('.geojson'):
            file_path = os.path.join(data_dir, filename)
            try:
                gdf = gpd.read_file(file_path)
                layer_name = os.path.splitext(filename)[0]
                for feature in gdf.itertuples():
                    properties = feature._asdict()
                    # Trouver le bon champ pour le nom
                    name_property = properties.get('NOM', properties.get('NOM_DEP',
                                properties.get('NOM_SITE', properties.get('nom_site',
                                properties.get('nom', 'Unknown')))))
                     # Ajouter le display_name depuis la configuration
                    display_name = data.get(layer_name, {}).get('display_name', layer_name)
                    selectable = data.get(layer_name, {}).get('selectable', False)
                    features.append({
                        "layer_name": layer_name,
                        "name": name_property,
                        "display_name": display_name,  # <-- Ajout du display_name
                        "selectable": selectable,
                        "properties": properties
                    })
            except Exception as e:
                print(f"Erreur lors du chargement de {filename} : {e}")
    return features


def create_map():

    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6)

    # Ajouter IGN Orthophoto comme option
    folium.TileLayer(
        tiles='https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
        attr='&copy; IGN',
        name='IGN Orthophoto',
        control=True
    ).add_to(m)

    # Ajouter IGN plan V2 comme option
    folium.TileLayer(
        tiles='https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
        attr='&copy; IGN',
        name='IGN plan V2',
        control=True
    ).add_to(m)

    data_dir = 'data'
    layer_styles = {obj_type: {'fillColor': data[obj_type]['color'], 'color': data[obj_type]['color'], 'weight': 2, 'fillOpacity': 0.5}
                    for obj_type in OBJECT_TYPES}
    geojson_files = [f for f in os.listdir(data_dir) if f.endswith('.geojson')]

    # Trier les fichiers selon LAYER_ORDER
    def get_layer_order(filename):
        layer_name = os.path.splitext(filename)[0]
        try:
            return LAYER_ORDER.index(layer_name)
        except ValueError:
            return len(LAYER_ORDER)

    geojson_files_sorted = sorted(geojson_files, key=get_layer_order)

    # Ajouter les couches dans l'ordre INVERSE pour que la dernière dans LAYER_ORDER soit au-dessus
    for filename in reversed(geojson_files_sorted):
        if filename.endswith('.geojson'):
            file_path = os.path.join(data_dir, filename)
            layer_name = os.path.splitext(filename)[0]
            try:
                gdf = gpd.read_file(file_path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                geojson_data = json.loads(gdf.to_json(default=convert_timestamps))
                if not geojson_data.get('features'):
                    continue
                style = layer_styles.get(layer_name, {'fillColor': 'gray', 'color': 'gray', 'weight': 1, 'fillOpacity': 0.5})
                tooltip_fields = data.get(layer_name, {}).get('tooltip_fields', ['NOM'])

                # Vérifier si la couche contient des points
                has_points = (gdf.geometry.type == 'Point').any()
                # Utiliser FeatureGroup pour un meilleur contrôle
                fg = folium.FeatureGroup(name=layer_name)
                if has_points:
                    # Ajouter les points comme des cercles avec la bonne couleur
                    for _, row in gdf[gdf.geometry.type == 'Point'].iterrows():
                        popup_text = ""
                        for field in tooltip_fields:
                            if field in row:
                                popup_text = str(row[field])
                                break
                        folium.CircleMarker(
                            location=[row.geometry.y, row.geometry.x],
                            radius=6,
                            fill_color="#FF92FA",  # Couleur par défaut : gris,  # <-- Couleur depuis OBJECT_TYPES
                            color= '#FF92FA',  # Couleur par défaut : gris,        # <-- Couleur depuis OBJECT_TYPES
                            fill_opacity=0.5,
                            weight=2,
                            fill=True,
                            popup=popup_text
                        ).add_to(fg)
                else:
                    
                    tooltip = folium.GeoJsonTooltip(fields=tooltip_fields, aliases=['Nom'], localize=True)
                    folium.GeoJson(
                        geojson_data,
                        name=layer_name,
                        style_function=lambda feature, style=style: style,
                        tooltip=tooltip
                    ).add_to(fg)
                fg.add_to(m)

                # Libérer la mémoire
                del gdf, geojson_data
                gc.collect()  # Force le garbage collector
            except Exception as e:
                print(f"Erreur lors du chargement de {filename}: {e}")

    folium.LayerControl().add_to(m)
    return m

# Fonction générique pour gérer la sélection
def selection(obj_type):
    obj_data = data[obj_type]
    obj_list = obj_data['list']
    column_name = obj_data['column']
    display_name = obj_data['display_name']

    # Lire les objets déjà sélectionnés
    selected_obj = []
    try:
        existing_geojson_path = os.path.join(DATA_DIR, f"{obj_type}.geojson")
        print(f"[SUCCESS] {existing_geojson_path} chargé.")
        if os.path.exists(existing_geojson_path):
            existing_gdf = gpd.read_file(existing_geojson_path)
            if column_name in existing_gdf.columns:
                selected_obj = existing_gdf[column_name].unique().tolist()
    except Exception as e:
        print(f"Erreur lors de la lecture de {obj_type}.geojson : {e}")

    missing_obj = []

    # Gérer l'upload de fichier
    if request.method == "POST" and "file" in request.files and request.files["file"].filename != "":
        try:
            file = request.files["file"]
            file_content = TextIOWrapper(file.stream, encoding='utf-8').read()
            uploaded_obj_list = []

            if file.filename.endswith('.csv'):
                reader = csv.reader(file_content.splitlines())
                for row in reader:
                    if row:
                        uploaded_obj_list.extend(row)
            elif file.filename.endswith('.geojson'):
                geojson_data = json.loads(file_content)
                for feature in geojson_data.get('features', []):
                    if 'properties' in feature and column_name in feature['properties']:
                        uploaded_obj_list.append(feature['properties'][column_name])
            else:
                uploaded_obj_list = [line.strip() for line in file_content.splitlines() if line.strip()]

            # Filtrage tolérant
            valid_obj_list = []
            for obj in uploaded_obj_list:
                match = match_name(obj, obj_list)
                if match:
                    valid_obj_list.append(match)
                else:
                    missing_obj.append(obj)

            # Ajouter les nouveaux objets à la sélection existante
            selected_obj = list(set(selected_obj + valid_obj_list))

            flash(f"{len(valid_obj_list)} nouveaux {display_name} ajoutés à la sélection (sur {len(uploaded_obj_list)} importés).", "info")
            if missing_obj:
                flash(f"{display_name} non trouvés : {', '.join(missing_obj)}", "warning")

            return render_template(f"selection_{obj_type}.html",
                                   obj_list=obj_list,
                                   total_obj=obj_data['total'],
                                   selected_obj=selected_obj,
                                   obj_type=obj_type,
                                   display_name=display_name)

        except Exception as e:
            flash(f"Erreur : {str(e)}", "error")

    # Par défaut, afficher la page avec les objets déjà sélectionnés
    return render_template(f"selection_{obj_type}.html",
                           obj_list=obj_list,
                           total_obj=obj_data['total'],
                           selected_obj=selected_obj,
                           obj_type=obj_type,
                           display_name=display_name,
                           missing_obj=missing_obj)

# Fonction générique pour sauvegarder la sélection
def save(obj_type):
    obj_data = data[obj_type]
    column_name = obj_data['column']
    display_name = obj_data['display_name']

    selected_obj = request.form.getlist(f"selected_obj")
    filtered_gdf = obj_data['gdf'][obj_data['gdf'][column_name].isin(selected_obj)]
    output_path = os.path.join(DATA_DIR, f"{obj_type}.geojson")
    filtered_gdf.to_file(output_path, driver="GeoJSON")
    flash(f"Fichier {obj_type}.geojson généré avec {len(selected_obj)} {display_name}.", "success")
    return redirect(url_for(f"selection_{obj_type}"))

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory(DATA_DIR, filename)


# Routes pour chaque type d'objet
@app.route("/selection_epci", methods=["GET", "POST"])
def selection_epci():
    return selection('epci')

@app.route("/selection_region", methods=["GET", "POST"])
def selection_region():
    return selection('region')

@app.route("/selection_pnr", methods=["GET", "POST"])
def selection_pnr():
    return selection('pnr')

@app.route("/selection_departement", methods=["GET", "POST"])
def selection_departement():
    return selection('departement')

# Routes pour sauvegarder
@app.route("/save_epci", methods=["POST"])
def save_epci():
    return save('epci')

@app.route("/save_region", methods=["POST"])
def save_region():
    return save('region')

@app.route("/save_pnr", methods=["POST"])
def save_pnr():
    return save('pnr')

@app.route("/save_departement", methods=["POST"])
def save_departement():
    return save('departement')

# Route principale
@app.route('/')
def index():
    data_dir = 'data'
    geojson_features = load_geojson_features(data_dir)
    m = create_map()
    return render_template('index.html', map=m._repr_html_(), geojson_features=geojson_features, OBJECT_TYPES=OBJECT_TYPES)  # <-- Ajoute OBJECT_TYPES ici)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
