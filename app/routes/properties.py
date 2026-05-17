import os
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app, make_response)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db, limiter
from app.models import (Property, PropertyPhoto, PropertyContact, Contact,
                         Research, ActivityLog,
                         Comment, PropertyHistory, Notification, User)
from app.utils import editor_required, notify_team, get_research_municipalities, get_research_members

properties_bp = Blueprint('properties', __name__, url_prefix='/properties')
ALLOWED_EXT   = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
PER_PAGE      = 20

def allowed_file(f):
    return '.' in f.filename and f.filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

def track_change(prop_id, user_id, field, old_val, new_val):
    old = str(old_val or '').strip()
    new = str(new_val or '').strip()
    if old != new:
        db.session.add(PropertyHistory(
            property_id=prop_id, user_id=user_id,
            field_name=field, old_value=old or '—', new_value=new or '—'
        ))

# ── LISTA con paginazione ─────────────────────────────────────────────────────
@properties_bp.route('/')
@login_required
def list_properties():
    research_id = session.get('active_research_id')
    research    = Research.query.get(research_id) if research_id else None

    # Parametri filtro — nomi allineati al template
    search_q      = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    type_filter   = request.args.get('type', '')
    comune_filter = request.args.get('comune', '')
    price_min     = request.args.get('price_min', '')
    price_max     = request.args.get('price_max', '')
    sort_by       = request.args.get('sort', 'newest')
    assigned_f    = request.args.get('assigned', '')
    page          = request.args.get('page', 1, type=int)

    q = Property.query.filter_by(research_id=research_id)
    if search_q:      q = q.filter(Property.title.ilike(f'%{search_q}%'))
    if status_filter: q = q.filter_by(status=status_filter)
    if type_filter:   q = q.filter_by(property_type=type_filter)
    try:
        if comune_filter: q = q.filter_by(municipality_id=int(comune_filter))
        if price_min:     q = q.filter(Property.price >= float(price_min))
        if price_max:     q = q.filter(Property.price <= float(price_max))
        if assigned_f:    q = q.filter_by(assigned_to=int(assigned_f))
    except (ValueError, TypeError):
        pass

    if sort_by == 'price_asc':  q = q.order_by(Property.price.asc())
    elif sort_by == 'price_desc': q = q.order_by(Property.price.desc())
    else:                         q = q.order_by(Property.created_at.desc())

    pagination = q.paginate(page=page, per_page=PER_PAGE, error_out=False)
    properties = pagination.items

    muns    = get_research_municipalities(research)
    members = get_research_members(research_id)

    return render_template('properties.html',
        properties=properties, municipalities=muns, members=members,
        pagination=pagination,
        search_q=search_q, status_filter=status_filter, type_filter=type_filter,
        comune_filter=comune_filter, price_min=price_min, price_max=price_max,
        sort_by=sort_by, assigned_f=assigned_f)

# ── DETTAGLIO ─────────────────────────────────────────────────────────────────
@properties_bp.route('/<int:prop_id>')
@login_required
def detail_property(prop_id):
    prop     = Property.query.get_or_404(prop_id)
    links    = PropertyContact.query.filter_by(property_id=prop_id).all()
    contacts = [(Contact.query.get(l.contact_id), l.relation_type) for l in links]
    contacts = [(c, r) for c, r in contacts if c]
    linked_ids         = {l.contact_id for l in links}
    all_contacts       = Contact.query.filter_by(research_id=prop.research_id).all()
    available_contacts = [c for c in all_contacts if c.id not in linked_ids]
    comments = Comment.query.filter_by(property_id=prop_id)\
                      .order_by(Comment.created_at.asc()).all()
    history  = PropertyHistory.query.filter_by(property_id=prop_id)\
                      .order_by(PropertyHistory.changed_at.desc()).limit(50).all()
    user_ids = set([c.user_id for c in comments] + [h.user_id for h in history])
    if prop.assigned_to: user_ids.add(prop.assigned_to)
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    members   = get_research_members(prop.research_id)
    return render_template('property_detail.html',
        prop=prop, mun=prop.municipality, photos=prop.photos,
        contacts=contacts, available_contacts=available_contacts,
        comments=comments, history=history, users_map=users_map, members=members)

# ── NUOVO ─────────────────────────────────────────────────────────────────────
@properties_bp.route('/new', methods=['GET', 'POST'])
@login_required
@editor_required
@limiter.limit("60 per minute", methods=["POST"])
def new_property():
    research_id = session.get('active_research_id')
    research    = Research.query.get(research_id) if research_id else None
    muns    = get_research_municipalities(research)
    members = get_research_members(research_id)
    if request.method == 'POST':
        assigned_raw = request.form.get('assigned_to')
        p = Property(
            research_id     = research_id,
            municipality_id = request.form.get('municipality_id') or None,
            title           = request.form.get('title'),
            property_type   = request.form.get('property_type'),
            status          = request.form.get('status', 'Da valutare'),
            price           = float(request.form.get('price')) if request.form.get('price') else None,
            address         = request.form.get('address'),
            listing_url     = request.form.get('listing_url'),
            notes           = request.form.get('notes'),
            lat             = float(request.form.get('lat')) if request.form.get('lat') else None,
            lng             = float(request.form.get('lng')) if request.form.get('lng') else None,
            assigned_to     = int(assigned_raw) if assigned_raw else None,
            created_at      = datetime.utcnow()
        )
        db.session.add(p); db.session.flush()
        _save_photos(p.id, request)
        db.session.add(ActivityLog(research_id=research_id, user_id=current_user.id,
                                    action='create_property', detail=f'Creato: {p.title}'))
        notify_team(research_id, current_user.id,
                    f'🏠 {current_user.full_name} ha aggiunto "{p.title}"',
                    url_for('properties.detail_property', prop_id=p.id))
        db.session.commit()
        flash('Immobile salvato.', 'success')
        return redirect(url_for('properties.detail_property', prop_id=p.id))
    return render_template('property_form.html', prop=None, municipalities=muns, members=members)

# ── MODIFICA ─────────────────────────────────────────────────────────────────
@properties_bp.route('/<int:prop_id>/edit', methods=['GET', 'POST'])
@login_required
@editor_required
def edit_property(prop_id):
    prop     = Property.query.get_or_404(prop_id)
    research = Research.query.get(prop.research_id)
    muns     = get_research_municipalities(research)
    members  = get_research_members(prop.research_id)
    if request.method == 'POST':
        assigned_raw  = request.form.get('assigned_to')
        new_assigned  = int(assigned_raw) if assigned_raw else None
        new_price     = float(request.form.get('price')) if request.form.get('price') else None
        _old_user  = User.query.get(prop.assigned_to) if prop.assigned_to else None
        old_a_name = _old_user.full_name if _old_user else '—'
        _new_user  = User.query.get(new_assigned) if new_assigned else None
        new_a_name = _new_user.full_name if _new_user else '—'
        for field, old, new in [
            ('title',        prop.title,         request.form.get('title')),
            ('status',       prop.status,        request.form.get('status')),
            ('price',        prop.price,         new_price),
            ('property_type',prop.property_type, request.form.get('property_type')),
            ('address',      prop.address,       request.form.get('address')),
            ('listing_url',  prop.listing_url,   request.form.get('listing_url')),
            ('notes',        prop.notes,         request.form.get('notes')),
            ('assigned_to',  old_a_name,         new_a_name),
        ]:
            track_change(prop.id, current_user.id, field, old, new)
        prop.title           = request.form.get('title')
        prop.property_type   = request.form.get('property_type')
        prop.status          = request.form.get('status')
        prop.price           = new_price
        prop.address         = request.form.get('address')
        prop.listing_url     = request.form.get('listing_url')
        prop.notes           = request.form.get('notes')
        prop.lat             = float(request.form.get('lat')) if request.form.get('lat') else prop.lat
        prop.lng             = float(request.form.get('lng')) if request.form.get('lng') else prop.lng
        prop.municipality_id = request.form.get('municipality_id') or prop.municipality_id
        prop.assigned_to     = new_assigned
        _save_photos(prop.id, request)
        db.session.add(ActivityLog(research_id=prop.research_id, user_id=current_user.id,
                                    action='edit_property', detail=f'Modificato: {prop.title}'))
        notify_team(prop.research_id, current_user.id,
                    f'✏️ {current_user.full_name} ha modificato "{prop.title}"',
                    url_for('properties.detail_property', prop_id=prop.id))
        db.session.commit()
        flash('Immobile aggiornato.', 'success')
        return redirect(url_for('properties.detail_property', prop_id=prop.id))
    return render_template('property_form.html', prop=prop, municipalities=muns, members=members)

# ── ELIMINA ──────────────────────────────────────────────────────────────────
@properties_bp.route('/<int:prop_id>/delete', methods=['POST'])
@login_required
@editor_required
@limiter.limit("30 per minute")
def delete_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    research_id, title = prop.research_id, prop.title
    PropertyContact.query.filter_by(property_id=prop_id).delete()
    Comment.query.filter_by(property_id=prop_id).delete()
    PropertyHistory.query.filter_by(property_id=prop_id).delete()
    db.session.delete(prop)  # cascade elimina le foto
    db.session.add(ActivityLog(research_id=research_id, user_id=current_user.id,
                                action='delete_property', detail=f'Eliminato: {title}'))
    db.session.commit()
    flash('Immobile eliminato.', 'success')
    return redirect(url_for('properties.list_properties'))

# ── COMMENTI ──────────────────────────────────────────────────────────────────
@properties_bp.route('/<int:prop_id>/comment', methods=['POST'])
@login_required
def add_comment(prop_id):
    prop = Property.query.get_or_404(prop_id)
    text = request.form.get('text', '').strip()
    if text:
        db.session.add(Comment(property_id=prop_id, user_id=current_user.id, text=text))
        notify_team(prop.research_id, current_user.id,
                    f'💬 {current_user.full_name} ha commentato "{prop.title}"',
                    url_for('properties.detail_property', prop_id=prop_id))
        db.session.commit()
    return redirect(url_for('properties.detail_property', prop_id=prop_id) + '#comments')

@properties_bp.route('/<int:prop_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(prop_id, comment_id):
    c = Comment.query.get_or_404(comment_id)
    if c.user_id == current_user.id or current_user.role == 'admin':
        db.session.delete(c); db.session.commit()
    return redirect(url_for('properties.detail_property', prop_id=prop_id) + '#comments')

# ── ASSEGNAZIONE RAPIDA ───────────────────────────────────────────────────────
@properties_bp.route('/<int:prop_id>/assign', methods=['POST'])
@login_required
@editor_required
def assign_property(prop_id):
    prop         = Property.query.get_or_404(prop_id)
    assigned_raw = request.form.get('assigned_to')
    prop.assigned_to = int(assigned_raw) if assigned_raw else None
    db.session.commit()
    _u = User.query.get(prop.assigned_to) if prop.assigned_to else None
    name = _u.full_name if _u else 'nessuno'
    flash(f'Immobile assegnato a {name}.', 'success')
    return redirect(url_for('properties.detail_property', prop_id=prop_id))

# ── COLLEGA / SCOLLEGA CONTATTO ──────────────────────────────────────────────
@properties_bp.route('/<int:prop_id>/link-contact', methods=['POST'])
@login_required
@editor_required
def link_contact(prop_id):
    prop       = Property.query.get_or_404(prop_id)
    contact_id = request.form.get('contact_id', type=int)
    rel_type   = request.form.get('relation_type', 'Agente')
    if contact_id and not PropertyContact.query.filter_by(
            property_id=prop_id, contact_id=contact_id).first():
        db.session.add(PropertyContact(
            property_id=prop_id, contact_id=contact_id, relation_type=rel_type))
        db.session.commit()
    return redirect(url_for('properties.detail_property', prop_id=prop_id) + '#contacts')

@properties_bp.route('/<int:prop_id>/unlink-contact/<int:contact_id>', methods=['POST'])
@login_required
@editor_required
def unlink_contact(prop_id, contact_id):
    PropertyContact.query.filter_by(
        property_id=prop_id, contact_id=contact_id).delete()
    db.session.commit()
    return redirect(url_for('properties.detail_property', prop_id=prop_id) + '#contacts')

@properties_bp.route('/<int:prop_id>/pdf')
@login_required
def property_pdf(prop_id):
    from weasyprint import HTML
    prop    = Property.query.get_or_404(prop_id)
    mun     = prop.municipality
    research = Research.query.get(prop.research_id)

    # Prima foto disponibile
    photo_url = None
    if prop.photos:
        ph = prop.photos[0]
        if ph.external_url:
            photo_url = ph.external_url
        elif ph.file_path:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', '')
            photo_path = os.path.join(upload_folder, ph.file_path)
            if os.path.exists(photo_path):
                photo_url = f'file:///{photo_path.replace(os.sep, "/")}'

    # Contatti collegati
    links = PropertyContact.query.filter_by(property_id=prop_id).all()
    contacts_data = []
    for link in links:
        c = Contact.query.get(link.contact_id)
        if c:
            contacts_data.append({'contact': c, 'relation': link.relation_type})

    # Storico ultime 10 modifiche
    history = (PropertyHistory.query.filter_by(property_id=prop_id)
               .order_by(PropertyHistory.changed_at.desc()).limit(10).all())

    html_str = render_template('property_print.html',
        prop=prop, mun=mun, research=research,
        photo_url=photo_url, contacts=contacts_data,
        history=history,
        now=datetime.utcnow().strftime('%d/%m/%Y %H:%M'))

    pdf = HTML(string=html_str, base_url=current_app.root_path).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=immobile-{prop_id}.pdf'
    return response


def _save_photos(prop_id, req):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    os.makedirs(upload_folder, exist_ok=True)
    for f in req.files.getlist('photos'):
        if f and f.filename and allowed_file(f):
            fname = secure_filename(f.filename)
            f.save(os.path.join(upload_folder, fname))
            db.session.add(PropertyPhoto(property_id=prop_id, file_path=fname))
    url = req.form.get('photo_url', '').strip()
    if url:
        db.session.add(PropertyPhoto(property_id=prop_id, external_url=url))
