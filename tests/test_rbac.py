"""RBAC: viewer non può modificare; editor/admin sì."""


def test_viewer_cannot_create_property(client, login_viewer, research):
    r = client.post('/properties/new',
                    data={'title': 'X', 'property_type': 'Appartamento',
                          'status': 'Da valutare'},
                    follow_redirects=False)
    # editor_required redirige a main.index
    assert r.status_code in (302, 303)
    assert '/properties' not in r.headers.get('Location', '') or \
           r.headers.get('Location', '').endswith('/')


def test_viewer_cannot_delete_property(client, login_viewer, sample_property):
    r = client.post(f'/properties/{sample_property.id}/delete',
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    # property non eliminata
    from app.models import Property
    assert Property.query.get(sample_property.id) is not None


def test_editor_can_create_property(client, login_editor, research, municipality):
    r = client.post('/properties/new',
                    data={'title': 'Nuova casa',
                          'property_type': 'Appartamento',
                          'status': 'Da valutare',
                          'municipality_id': municipality.id,
                          'price': '200000'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    from app.models import Property
    assert Property.query.filter_by(title='Nuova casa').first() is not None


def test_viewer_can_view_property_list(client, login_viewer, sample_property):
    r = client.get('/properties/')
    assert r.status_code == 200


def test_viewer_can_view_property_detail(client, login_viewer, sample_property):
    r = client.get(f'/properties/{sample_property.id}')
    assert r.status_code == 200


def test_non_admin_cannot_access_admin(client, login_editor):
    r = client.get('/admin/', follow_redirects=False)
    # admin_required redirige a main.index
    assert r.status_code in (302, 303)


def test_admin_can_access_admin(client, login_admin):
    r = client.get('/admin/')
    assert r.status_code == 200
