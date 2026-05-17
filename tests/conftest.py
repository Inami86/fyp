import pytest
from sqlalchemy import event
from werkzeug.security import generate_password_hash

from app import create_app, db as _db
from app.models import (User, Research, ResearchUser, Municipality,
                        Property, Contact)


def _register_sqlite_funcs(dbapi_conn, _):
    """SQLite non ha lpad/concat: ne registriamo equivalenti per i test."""
    dbapi_conn.create_function('lpad', 3,
        lambda s, n, fill: str(s).rjust(int(n), fill) if s is not None else None)
    dbapi_conn.create_function('concat', -1,
        lambda *args: ''.join('' if a is None else str(a) for a in args))


@pytest.fixture(scope='function')
def app():
    app = create_app('testing')
    with app.app_context():
        event.listen(_db.engine, 'connect', _register_sqlite_funcs)
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
        event.remove(_db.engine, 'connect', _register_sqlite_funcs)


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(db, email, role, full_name=None, password='testpass123'):
    u = User(
        email=email,
        full_name=full_name or email.split('@')[0],
        role=role,
        password_hash=generate_password_hash(password),
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin(db):
    return _make_user(db, 'admin@test.local', 'admin', 'Admin User')


@pytest.fixture
def editor(db):
    return _make_user(db, 'editor@test.local', 'editor', 'Editor User')


@pytest.fixture
def viewer(db):
    return _make_user(db, 'viewer@test.local', 'viewer', 'Viewer User')


@pytest.fixture
def research(db, admin, editor, viewer):
    r = Research(name='Test Ricerca', region='Toscana', created_by=admin.id)
    db.session.add(r)
    db.session.commit()
    for u in (admin, editor, viewer):
        db.session.add(ResearchUser(research_id=r.id, user_id=u.id))
    db.session.commit()
    return r


@pytest.fixture
def municipality(db, research):
    m = Municipality(name='Firenze', region=research.region,
                     research_status='explored',
                     center_lat=43.77, center_lng=11.25)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def sample_property(db, research, municipality, editor):
    p = Property(
        research_id=research.id, municipality_id=municipality.id,
        title='Casa di Test', property_type='Appartamento',
        status='Interessante', price=150000.0,
        address='Via Test 1', assigned_to=editor.id,
    )
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def sample_contact(db, research):
    c = Contact(research_id=research.id, name='Mario Rossi',
                contact_type='Agente', phone='3331234567',
                email='mario@test.local', agency='Test Agency')
    db.session.add(c)
    db.session.commit()
    return c


def _login(client, user, research, password='testpass123'):
    client.post('/login',
                data={'email': user.email, 'password': password},
                follow_redirects=False)
    # Forza l'active_research_id in sessione (il context_processor non scatta sulle redirect)
    with client.session_transaction() as sess:
        sess['active_research_id'] = research.id


@pytest.fixture
def login_admin(client, admin, research):
    _login(client, admin, research)
    return admin


@pytest.fixture
def login_editor(client, editor, research):
    _login(client, editor, research)
    return editor


@pytest.fixture
def login_viewer(client, viewer, research):
    _login(client, viewer, research)
    return viewer
