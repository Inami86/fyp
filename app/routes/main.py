import json, csv, io
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   session, jsonify, request, Response)
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import (Research, ResearchUser, Municipality, Property,
                         Contact, ActivityLog, User)
from app import db
from pathlib import Path
from app.utils import region_to_slug

main_bp  = Blueprint('main', __name__)
DATA_DIR = Path(__file__).resolve().parents[1] / 'data'

def get_active_research():
    research_id = session.get('active_research_id')
    if research_id:
        r = Research.query.get(research_id)
        if r: return r
    m = ResearchUser.query.filter_by(user_id=current_user.id).first()
    if m:
        session['active_research_id'] = m.research_id
        return Research.query.get(m.research_id)
    return None

@main_bp.route('/')
@login_required
def index():
    research = get_active_research()
    if not research:
        return redirect(url_for('researches.list_researches'))

    rid   = research.id
    props = Property.query.filter_by(research_id=rid).all()
    prezzi = [p.price for p in props if p.price]
    muns   = Municipality.query.filter_by(region=research.region).all()

    # Comuni con almeno un immobile inserito
    mun_ids_con_props = {p.municipality_id for p in props if p.municipality_id}

    kpi = dict(
        total          = len(props),
        interessanti   = sum(1 for p in props if p.status == 'Interessante'),
        da_valutare    = sum(1 for p in props if p.status == 'Da valutare'),
        offerta        = sum(1 for p in props if p.status == 'Offerta fatta'),
        scartati       = sum(1 for p in props if p.status == 'Scartato'),
        avg_price      = int(sum(prezzi) / len(prezzi)) if prezzi else None,
        muns_explored  = sum(1 for m in muns if m.research_status == 'explored'),
        total_muns     = len(muns),
        comuni_coperti = len(mun_ids_con_props),
    )

    # ── Grafico 1: donut stati ────────────────────────────────────────────
    chart_stati = {
        'labels': ['Da valutare', 'Interessante', 'Offerta fatta', 'Scartato'],
        'data':   [kpi['da_valutare'], kpi['interessanti'], kpi['offerta'], kpi['scartati']],
        'colors': ['#b07800', '#437a22', '#01696f', '#a12c7b'],
    }

    # ── Grafico 2: barre — prezzo medio per comune ────────────────────────
    price_by_mun = (db.session.query(Municipality.name, func.avg(Property.price))
                    .join(Property, Property.municipality_id == Municipality.id)
                    .filter(Property.research_id == rid, Property.price.isnot(None))
                    .group_by(Municipality.name)
                    .order_by(func.avg(Property.price).desc())
                    .limit(10).all())
    chart_prezzi = {
        'labels': [r[0] for r in price_by_mun],
        'data':   [round(r[1]) for r in price_by_mun],
    }

    # ── Grafico 3: linea — inserimenti nel tempo (per mese) ───────────────
    monthly_raw = (db.session.query(
                        func.strftime('%Y-%m', Property.created_at).label('month'),
                        func.count(Property.id))
                   .filter(Property.research_id == rid,
                           Property.created_at.isnot(None))
                   .group_by('month')
                   .order_by('month').all())
    chart_inserimenti = {
        'labels': [r[0] for r in monthly_raw],  # '2026-04'
        'data':   [r[1] for r in monthly_raw],
    }

    # ── Feed attività (20 eventi) ─────────────────────────────────────────
    logs = (ActivityLog.query.filter_by(research_id=rid)
            .order_by(ActivityLog.timestamp.desc()).limit(20).all())
    user_ids  = {l.user_id for l in logs if l.user_id}
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}

    contacts = Contact.query.filter_by(research_id=rid).all()

    return render_template('index.html',
        research=research, municipalities=muns,
        properties=props, contacts=contacts,
        logs=logs, users_map=users_map,
        kpi=kpi,
        chart_stati=chart_stati,
        chart_prezzi=chart_prezzi,
        chart_inserimenti=chart_inserimenti)


@main_bp.route('/activity')
@login_required
def activity_log():
    research      = get_active_research()
    action_filter = request.args.get('action', '')
    q = ActivityLog.query.filter_by(research_id=research.id if research else -1)
    if action_filter: q = q.filter_by(action=action_filter)
    logs    = q.order_by(ActivityLog.timestamp.desc()).limit(200).all()
    actions = db.session.query(ActivityLog.action).filter_by(
        research_id=research.id if research else -1).distinct().all()
    user_ids  = {l.user_id for l in logs if l.user_id}
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    return render_template('activity_log.html', logs=logs,
                           action_filter=action_filter,
                           actions=[a[0] for a in actions],
                           users_map=users_map)


@main_bp.route('/properties/export-csv')
@login_required
def export_properties_csv():
    from app.models import PropertyPhoto, PropertyContact as PC
    research = get_active_research()
    props    = Property.query.filter_by(research_id=research.id if research else -1).all()
    output   = io.StringIO()
    w        = csv.writer(output)
    w.writerow(['ID','Titolo','Comune','Tipologia','Stato','Prezzo','Indirizzo',
                'URL annuncio','Foto','Contatti','Note','Data aggiunta'])
    for p in props:
        mun       = Municipality.query.get(p.municipality_id)
        photos    = PropertyPhoto.query.filter_by(property_id=p.id).all()
        photo_urls = ' | '.join(
            ph.external_url if ph.external_url else f'/uploads/{ph.file_path}' for ph in photos)
        links    = PC.query.filter_by(property_id=p.id).all()
        cont_ids = [l.contact_id for l in links]
        contacts = Contact.query.filter(Contact.id.in_(cont_ids)).all() if cont_ids else []
        w.writerow([p.id, p.title, mun.name if mun else '', p.property_type,
                    p.status, p.price or '', p.address or '', p.listing_url or '',
                    photo_urls, ' | '.join(c.name for c in contacts),
                    (p.notes or '').replace('\n', ' '),
                    p.created_at.strftime('%d/%m/%Y %H:%M') if p.created_at else ''])
    return Response(output.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition':
            f'attachment; filename=immobili-{research.name if research else "fyp"}.csv'})


@main_bp.route('/api/map-data')
@login_required
def map_data():
    research = get_active_research()
    if not research: return jsonify({'error': 'no_research'}), 400
    muns   = Municipality.query.filter_by(region=research.region).all()
    props  = Property.query.filter_by(research_id=research.id).all()
    conts  = Contact.query.filter_by(research_id=research.id).all()
    mun_status = {m.name: m.research_status for m in muns}
    slug      = region_to_slug(research.region)
    geo_path  = DATA_DIR / 'regions' / f'{slug}.geojson'
    if not geo_path.exists():
        geo_path = DATA_DIR / 'calabria_comuni.geojson'
    geojson = None
    if geo_path.exists():
        with open(geo_path, encoding='utf-8') as f:
            geojson = json.load(f)
        for feature in geojson['features']:
            name = feature['properties'].get('name', '')
            feature['properties']['status'] = mun_status.get(name, 'unexplored')
    return jsonify({
        'research':       {'id': research.id, 'name': research.name, 'region': research.region},
        'municipalities': [{'id': m.id, 'name': m.name, 'status': m.research_status,
                             'center_lat': m.center_lat, 'center_lng': m.center_lng} for m in muns],
        'properties':    [{'id': p.id, 'title': p.title, 'price': p.price,
                            'status': p.status, 'lat': p.lat, 'lng': p.lng,
                            'address': p.address, 'municipality_id': p.municipality_id} for p in props],
        'contacts':      [{'id': c.id, 'name': c.name, 'type': c.contact_type,
                            'phone': c.phone, 'lat': c.lat, 'lng': c.lng} for c in conts],
        'geojson':       geojson,
        'has_geojson':   geojson is not None
    })


@main_bp.route('/api/municipality/<int:mun_id>/status', methods=['POST'])
@login_required
def set_municipality_status(mun_id):
    if current_user.role not in ['admin', 'editor']:
        return jsonify({'error': 'forbidden'}), 403
    mun = Municipality.query.get_or_404(mun_id)
    new_status = request.json.get('status')
    if new_status in ['explored', 'partial', 'unexplored']:
        mun.research_status = new_status; db.session.commit()
        return jsonify({'ok': True, 'status': new_status})
    return jsonify({'error': 'invalid_status'}), 400


@main_bp.route('/switch-research/<int:research_id>')
@login_required
def switch_research(research_id):
    session['active_research_id'] = research_id
    return redirect(url_for('main.index'))
