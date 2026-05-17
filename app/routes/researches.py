import json
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
from app.models import Research, ResearchUser, Municipality
from app.utils import admin_required, region_to_slug

researches_bp = Blueprint('researches', __name__, url_prefix='/researches')

# Lista regioni con slug GeoJSON disponibile
DATA_DIR = Path(__file__).resolve().parents[1] / 'data' / 'regions'

def available_regions():
    """Restituisce le regioni per cui esiste un GeoJSON."""
    slugs = {f.stem for f in DATA_DIR.glob('*.geojson')}
    region_map = {
        'Abruzzo': 'Abruzzo', 'Basilicata': 'Basilicata', 'Calabria': 'Calabria',
        'Campania': 'Campania', 'Emilia-Romagna': 'Emilia-Romagna',
        'Friuli-Venezia Giulia': 'Friuli-Venezia_Giulia',
        'Lazio': 'Lazio', 'Liguria': 'Liguria', 'Lombardia': 'Lombardia',
        'Marche': 'Marche', 'Molise': 'Molise', 'Piemonte': 'Piemonte',
        'Puglia': 'Puglia', 'Sardegna': 'Sardegna', 'Sicilia': 'Sicilia',
        'Toscana': 'Toscana',
        'Trentino-Alto Adige': 'Trentino-Alto_Adige_Sudtirol',
        'Umbria': 'Umbria',
        "Valle d'Aosta": 'Valle_dAosta_Vallee_dAoste',
        'Veneto': 'Veneto'
    }
    return [r for r, slug in region_map.items() if slug in slugs or region_to_slug(r) in slugs]

def load_municipalities(region):
    slug     = region_to_slug(region)
    geo_path = DATA_DIR / f'{slug}.geojson'
    if not geo_path.exists():
        return 0
    try:
        with open(geo_path, encoding='utf-8') as f:
            gj = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0

    # Carica TUTTI i comuni della regione in UNA query (evita N+1)
    existing_names = {m.name for m in Municipality.query.filter_by(region=region).all()}

    count = 0
    for feat in gj['features']:
        name = feat['properties'].get('name', '').strip()
        if not name or name in existing_names: continue
        coords = []
        g = feat['geometry']
        if g['type'] == 'MultiPolygon':
            for poly in g['coordinates']:
                for ring in poly: coords.extend(ring)
        elif g['type'] == 'Polygon':
            for ring in g['coordinates']: coords.extend(ring)
        lat = round(sum(c[1] for c in coords)/len(coords), 5) if coords else None
        lng = round(sum(c[0] for c in coords)/len(coords), 5) if coords else None
        db.session.add(Municipality(name=name, region=region,
                                     research_status='unexplored',
                                     center_lat=lat, center_lng=lng))
        count += 1
    db.session.commit()
    return count

@researches_bp.route('/')
@login_required
def list_researches():
    memberships = ResearchUser.query.filter_by(user_id=current_user.id).all()
    research_ids = [m.research_id for m in memberships]
    researches = Research.query.filter(Research.id.in_(research_ids)).all() \
                 if current_user.role != 'admin' else Research.query.all()
    return render_template('researches.html', researches=researches)

@researches_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_research():
    regions = sorted(available_regions())
    if request.method == 'POST':
        region = request.form.get('region')
        r = Research(name=request.form.get('name'), region=region,
                     created_by=current_user.id)
        db.session.add(r)
        db.session.flush()
        db.session.add(ResearchUser(research_id=r.id, user_id=current_user.id))

        # Carica comuni della regione selezionata
        n = load_municipalities(region)
        db.session.commit()

        flash(f'Ricerca "{r.name}" creata con {n} comuni caricati.', 'success')
        session['active_research_id'] = r.id
        return redirect(url_for('main.index'))
    return render_template('research_form.html', regions=regions)

@researches_bp.route('/<int:research_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_research(research_id):
    r = Research.query.get_or_404(research_id)
    ResearchUser.query.filter_by(research_id=research_id).delete()
    db.session.delete(r)
    db.session.commit()
    flash('Ricerca eliminata.', 'success')
    return redirect(url_for('researches.list_researches'))
