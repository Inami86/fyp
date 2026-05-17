from app.models import Contact


def test_list_contacts(client, login_editor, sample_contact):
    r = client.get('/contacts/')
    assert r.status_code == 200
    assert b'Mario Rossi' in r.data


def test_detail_contact(client, login_editor, sample_contact):
    r = client.get(f'/contacts/{sample_contact.id}')
    assert r.status_code == 200
    assert b'Mario Rossi' in r.data


def test_create_contact(client, login_editor, research):
    r = client.post('/contacts/new',
                    data={'name': 'Luigi Verdi',
                          'contact_type': 'Proprietario',
                          'phone': '3399999999',
                          'email': 'luigi@test.local'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    c = Contact.query.filter_by(name='Luigi Verdi').first()
    assert c is not None
    assert c.contact_type == 'Proprietario'


def test_edit_contact(client, login_editor, sample_contact):
    r = client.post(f'/contacts/{sample_contact.id}/edit',
                    data={'name': 'Mario Bianchi',
                          'contact_type': 'Agente',
                          'phone': '3331234567'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    c = Contact.query.get(sample_contact.id)
    assert c.name == 'Mario Bianchi'


def test_delete_contact(client, login_editor, sample_contact):
    cid = sample_contact.id
    r = client.post(f'/contacts/{cid}/delete', follow_redirects=False)
    assert r.status_code in (302, 303)
    assert Contact.query.get(cid) is None


def test_viewer_cannot_create_contact(client, login_viewer, research):
    r = client.post('/contacts/new',
                    data={'name': 'X', 'contact_type': 'Agente'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    assert Contact.query.filter_by(name='X').first() is None
