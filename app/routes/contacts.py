from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
from app.models import Contact, ActivityLog, PropertyContact, Property, Municipality
from app.utils import editor_required
from datetime import datetime


def _parse_coord(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')

RELATION_TYPES = ['Agente', 'Proprietario', 'Riferimento', 'Altro']

@contacts_bp.route('/')
@login_required
def list_contacts():
    research_id = session.get('active_research_id')
    contacts    = Contact.query.filter_by(research_id=research_id).order_by(Contact.name).all()
    # Conta immobili per contatto (per badge)
    counts = {}
    for c in contacts:
        counts[c.id] = PropertyContact.query.filter_by(contact_id=c.id).count()
    return render_template('contacts.html', contacts=contacts, counts=counts)

@contacts_bp.route('/<int:contact_id>')
@login_required
def detail_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    links   = PropertyContact.query.filter_by(contact_id=contact_id).all()
    # Immobili collegati con dettagli
    linked_props = []
    for link in links:
        prop = Property.query.get(link.property_id)
        if prop:
            mun = Municipality.query.get(prop.municipality_id)
            linked_props.append({'prop': prop, 'mun': mun, 'relation': link.relation_type})
    # Tutti gli immobili della ricerca per il form di collegamento rapido
    all_props = Property.query.filter_by(research_id=contact.research_id).order_by(Property.title).all()
    return render_template('contact_detail.html', contact=contact,
                           linked_props=linked_props, relation_types=RELATION_TYPES,
                           all_props=all_props)

@contacts_bp.route('/new', methods=['GET', 'POST'])
@login_required
@editor_required
def new_contact():
    research_id = session.get('active_research_id')
    properties  = Property.query.filter_by(research_id=research_id).order_by(Property.title).all()
    if request.method == 'POST':
        c = Contact(
            research_id=research_id,
            name=request.form.get('name'),
            contact_type=request.form.get('contact_type'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            agency=request.form.get('agency'),
            city=request.form.get('city'),
            address=request.form.get('address'),
            notes=request.form.get('notes'),
            lat=_parse_coord(request.form.get('lat')),
            lng=_parse_coord(request.form.get('lng')),
            created_at=datetime.utcnow()
        )
        db.session.add(c)
        db.session.flush()
        prop_id  = request.form.get('property_id', type=int)
        rel_type = request.form.get('relation_type', 'Agente')
        if prop_id:
            db.session.add(PropertyContact(
                property_id=prop_id, contact_id=c.id, relation_type=rel_type))
        db.session.add(ActivityLog(research_id=research_id, user_id=current_user.id,
                                    action='create_contact', detail=f'Creato: {c.name}'))
        db.session.commit()
        flash('Contatto creato.', 'success')
        return redirect(url_for('contacts.detail_contact', contact_id=c.id))
    return render_template('contact_form.html', contact=None,
                           properties=properties, relation_types=RELATION_TYPES)

@contacts_bp.route('/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
@editor_required
def edit_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if request.method == 'POST':
        contact.name         = request.form.get('name')
        contact.contact_type = request.form.get('contact_type')
        contact.phone        = request.form.get('phone')
        contact.email        = request.form.get('email')
        contact.agency       = request.form.get('agency')
        contact.city         = request.form.get('city')
        contact.address      = request.form.get('address')
        contact.notes        = request.form.get('notes')
        contact.lat          = _parse_coord(request.form.get('lat'))
        contact.lng          = _parse_coord(request.form.get('lng'))
        db.session.add(ActivityLog(research_id=contact.research_id, user_id=current_user.id,
                                    action='edit_contact', detail=f'Modificato: {contact.name}'))
        db.session.commit()
        flash('Contatto aggiornato.', 'success')
        return redirect(url_for('contacts.detail_contact', contact_id=contact_id))
    return render_template('contact_form.html', contact=contact)

@contacts_bp.route('/<int:contact_id>/delete', methods=['POST'])
@login_required
@editor_required
def delete_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    research_id, name = contact.research_id, contact.name
    PropertyContact.query.filter_by(contact_id=contact_id).delete()
    db.session.delete(contact)
    db.session.add(ActivityLog(research_id=research_id, user_id=current_user.id,
                                action='delete_contact', detail=f'Eliminato: {name}'))
    db.session.commit()
    flash('Contatto eliminato.', 'success')
    return redirect(url_for('contacts.list_contacts'))

# ── Collega immobile da scheda contatto ──────────────────────────────────────
@contacts_bp.route('/<int:contact_id>/link_property', methods=['POST'])
@login_required
@editor_required
def link_property(contact_id):
    prop_id  = request.form.get('property_id')
    rel_type = request.form.get('relation_type', 'Agente')
    if not PropertyContact.query.filter_by(property_id=prop_id, contact_id=contact_id).first():
        db.session.add(PropertyContact(property_id=prop_id, contact_id=contact_id,
                                        relation_type=rel_type))
        db.session.commit()
        flash('Immobile collegato.', 'success')
    return redirect(url_for('contacts.detail_contact', contact_id=contact_id))

@contacts_bp.route('/<int:contact_id>/unlink_property/<int:prop_id>', methods=['POST'])
@login_required
@editor_required
def unlink_property(contact_id, prop_id):
    link = PropertyContact.query.filter_by(property_id=prop_id, contact_id=contact_id).first()
    if link:
        db.session.delete(link); db.session.commit()
        flash('Immobile scollegato.', 'success')
    return redirect(url_for('contacts.detail_contact', contact_id=contact_id))
