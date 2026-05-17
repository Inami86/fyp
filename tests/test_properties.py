from app.models import Property, Comment, PropertyContact


def test_list_properties(client, login_editor, sample_property):
    r = client.get('/properties/')
    assert r.status_code == 200
    assert b'Casa di Test' in r.data


def test_detail_property(client, login_editor, sample_property):
    r = client.get(f'/properties/{sample_property.id}')
    assert r.status_code == 200
    assert b'Casa di Test' in r.data


def test_detail_404_unknown(client, login_editor):
    r = client.get('/properties/99999')
    assert r.status_code == 404


def test_create_property(client, login_editor, research, municipality):
    r = client.post('/properties/new',
                    data={'title': 'Casa Nuova',
                          'property_type': 'Casa indipendente',
                          'status': 'Interessante',
                          'municipality_id': municipality.id,
                          'price': '180000',
                          'address': 'Via Roma 5'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    p = Property.query.filter_by(title='Casa Nuova').first()
    assert p is not None
    assert p.price == 180000.0
    assert p.status == 'Interessante'


def test_edit_property(client, login_editor, sample_property):
    r = client.post(f'/properties/{sample_property.id}/edit',
                    data={'title': 'Casa Modificata',
                          'property_type': 'Appartamento',
                          'status': 'Offerta fatta',
                          'price': '175000'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    p = Property.query.get(sample_property.id)
    assert p.title == 'Casa Modificata'
    assert p.status == 'Offerta fatta'


def test_delete_property(client, login_editor, sample_property):
    pid = sample_property.id
    r = client.post(f'/properties/{pid}/delete', follow_redirects=False)
    assert r.status_code in (302, 303)
    assert Property.query.get(pid) is None


def test_add_comment(client, login_editor, sample_property):
    r = client.post(f'/properties/{sample_property.id}/comment',
                    data={'text': 'Commento di test'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    assert Comment.query.filter_by(property_id=sample_property.id).count() == 1


def test_add_empty_comment_ignored(client, login_editor, sample_property):
    client.post(f'/properties/{sample_property.id}/comment',
                data={'text': '   '})
    assert Comment.query.filter_by(property_id=sample_property.id).count() == 0


def test_viewer_can_comment(client, login_viewer, sample_property):
    """Per design, anche i viewer possono commentare."""
    r = client.post(f'/properties/{sample_property.id}/comment',
                    data={'text': 'Da viewer'})
    assert r.status_code in (302, 303)
    assert Comment.query.filter_by(property_id=sample_property.id).count() == 1


def test_link_contact(client, login_editor, sample_property, sample_contact):
    r = client.post(f'/properties/{sample_property.id}/link-contact',
                    data={'contact_id': sample_contact.id,
                          'relation_type': 'Agente'})
    assert r.status_code in (302, 303)
    link = PropertyContact.query.filter_by(
        property_id=sample_property.id, contact_id=sample_contact.id).first()
    assert link is not None
    assert link.relation_type == 'Agente'


def test_link_contact_idempotent(client, login_editor, sample_property, sample_contact):
    """Linkare due volte non crea duplicati."""
    for _ in range(2):
        client.post(f'/properties/{sample_property.id}/link-contact',
                    data={'contact_id': sample_contact.id, 'relation_type': 'Agente'})
    count = PropertyContact.query.filter_by(
        property_id=sample_property.id, contact_id=sample_contact.id).count()
    assert count == 1


def test_filter_by_status(client, login_editor, sample_property):
    r = client.get('/properties/?status=Interessante')
    assert r.status_code == 200
    assert b'Casa di Test' in r.data
    r2 = client.get('/properties/?status=Scartato')
    assert b'Casa di Test' not in r2.data


def test_filter_price_range(client, login_editor, sample_property):
    # property ha prezzo 150000
    r = client.get('/properties/?price_min=100000&price_max=200000')
    assert b'Casa di Test' in r.data
    r2 = client.get('/properties/?price_min=300000')
    assert b'Casa di Test' not in r2.data
