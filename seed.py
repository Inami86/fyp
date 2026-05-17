"""seed.py — v0.0.7 — Carica i 404 comuni Calabria dal GeoJSON regionale."""
import json
import os
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

if os.environ.get('FLASK_ENV') == 'production':
    sys.exit('seed.py non può essere eseguito in produzione.')

BASE_DIR = Path(__file__).resolve().parent

def get_centroid(geometry):
    coords = []
    if geometry['type'] == 'MultiPolygon':
        for poly in geometry['coordinates']:
            for ring in poly: coords.extend(ring)
    elif geometry['type'] == 'Polygon':
        for ring in geometry['coordinates']: coords.extend(ring)
    if not coords: return None, None
    return (round(sum(c[1] for c in coords)/len(coords), 5),
            round(sum(c[0] for c in coords)/len(coords), 5))

def load_municipalities_for_region(region, db, Municipality):
    """Carica i comuni di una regione dal GeoJSON regionale.
    Usato sia dal seed che dalla creazione di nuove ricerche."""
    from app.utils import region_to_slug
    slug     = region_to_slug(region)
    geo_path = BASE_DIR / 'app' / 'data' / 'regions' / f'{slug}.geojson'
    if not geo_path.exists():
        print(f"  ⚠️  GeoJSON non trovato per: {region} ({geo_path.name})")
        return 0
    with open(geo_path, encoding='utf-8') as f:
        gj = json.load(f)
    count = 0
    for feat in gj['features']:
        name = feat['properties'].get('name', '').strip()
        if not name: continue
        if Municipality.query.filter_by(name=name, region=region).first():
            continue  # già presente, non duplicare
        lat, lng = get_centroid(feat['geometry'])
        db.session.add(Municipality(
            name=name, region=region,
            research_status='unexplored',
            center_lat=lat, center_lng=lng
        ))
        count += 1
    return count

def run_seed():
    from app import create_app, db
    from app.models import User, Research, ResearchUser, Municipality

    app = create_app('development')
    with app.app_context():
        db.drop_all()
        db.create_all()

        admin  = User(full_name='Admin FyP',  email='admin@fyp.local',  role='admin',
                      password_hash=generate_password_hash('admin123'))
        editor = User(full_name='Editor FyP', email='editor@fyp.local', role='editor',
                      password_hash=generate_password_hash('editor123'))
        viewer = User(full_name='Viewer FyP', email='viewer@fyp.local', role='viewer',
                      password_hash=generate_password_hash('viewer123'))
        db.session.add_all([admin, editor, viewer])
        db.session.flush()

        research = Research(name='Ricerca Calabria', region='Calabria', created_by=admin.id)
        db.session.add(research)
        db.session.flush()

        db.session.add_all([
            ResearchUser(research_id=research.id, user_id=admin.id),
            ResearchUser(research_id=research.id, user_id=editor.id),
            ResearchUser(research_id=research.id, user_id=viewer.id),
        ])

        n = load_municipalities_for_region('Calabria', db, Municipality)
        db.session.commit()

        print(f"\n✅  Seed v0.0.7 completato:")
        print(f"    • 3 utenti  (admin / editor / viewer)")
        print(f"    • 1 ricerca demo: 'Ricerca Calabria'")
        print(f"    • {n} comuni Calabria caricati")
        print(f"\n    Login: admin@fyp.local / admin123")

if __name__ == '__main__':
    run_seed()
