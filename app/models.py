from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='viewer')

class Research(db.Model):
    __tablename__ = 'research'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    region     = db.Column(db.String(80),  nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResearchUser(db.Model):
    __tablename__ = 'research_user'
    id          = db.Column(db.Integer, primary_key=True)
    research_id = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'),     nullable=False)

class Municipality(db.Model):
    __tablename__   = 'municipality'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(120), nullable=False)
    region          = db.Column(db.String(80),  nullable=False)
    research_status = db.Column(db.String(20),  default='unexplored')
    center_lat      = db.Column(db.Float)
    center_lng      = db.Column(db.Float)

class Property(db.Model):
    __tablename__   = 'property'
    id              = db.Column(db.Integer, primary_key=True)
    research_id     = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)
    municipality_id = db.Column(db.Integer, db.ForeignKey('municipality.id'))
    title           = db.Column(db.String(200), nullable=False)
    property_type   = db.Column(db.String(50))
    status          = db.Column(db.String(50),  default='Da valutare')
    price           = db.Column(db.Float)
    address         = db.Column(db.String(200))
    listing_url     = db.Column(db.String(500))
    notes           = db.Column(db.Text)
    lat             = db.Column(db.Float)
    lng             = db.Column(db.Float)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_to     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # Relationships — usate nelle card e nella scheda dettaglio
    photos       = db.relationship('PropertyPhoto',    backref='property',    lazy=True,
                                    foreign_keys='PropertyPhoto.property_id',
                                    cascade='all, delete-orphan')
    municipality = db.relationship('Municipality',     backref='properties',  lazy=True,
                                    foreign_keys='Property.municipality_id')

class PropertyPhoto(db.Model):
    __tablename__ = 'property_photo'
    id            = db.Column(db.Integer, primary_key=True)
    property_id   = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    file_path     = db.Column(db.String(300))
    external_url  = db.Column(db.String(500))
    uploaded_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    __tablename__  = 'contact'
    id             = db.Column(db.Integer, primary_key=True)
    research_id    = db.Column(db.Integer, db.ForeignKey('research.id'), nullable=False)
    name           = db.Column(db.String(120), nullable=False)
    contact_type   = db.Column(db.String(50))
    phone          = db.Column(db.String(50))
    email          = db.Column(db.String(120))
    agency         = db.Column(db.String(120))
    city           = db.Column(db.String(120))   # ← nuovo v0.1.1
    address        = db.Column(db.String(200))   # ← nuovo v0.1.1
    notes          = db.Column(db.Text)
    lat            = db.Column(db.Float)
    lng            = db.Column(db.Float)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    property_links = db.relationship('PropertyContact', backref='contact', lazy=True,
                                      foreign_keys='PropertyContact.contact_id')

class PropertyContact(db.Model):
    __tablename__ = 'property_contact'
    id            = db.Column(db.Integer, primary_key=True)
    property_id   = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    contact_id    = db.Column(db.Integer, db.ForeignKey('contact.id'),  nullable=False)
    relation_type = db.Column(db.String(30), default='Agente')

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id            = db.Column(db.Integer, primary_key=True)
    research_id   = db.Column(db.Integer, db.ForeignKey('research.id'))
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'))
    action        = db.Column(db.String(50))
    detail        = db.Column(db.String(300))
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comment'
    id          = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'),     nullable=False)
    text        = db.Column(db.Text,    nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class PropertyHistory(db.Model):
    __tablename__ = 'property_history'
    id          = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'),     nullable=False)
    field_name  = db.Column(db.String(60))
    old_value   = db.Column(db.String(500))
    new_value   = db.Column(db.String(500))
    changed_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notification'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message    = db.Column(db.String(300), nullable=False)
    link       = db.Column(db.String(300))
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
