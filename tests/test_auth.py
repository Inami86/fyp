def test_login_page_renders(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert b'password' in r.data.lower() or b'email' in r.data.lower()


def test_login_success(client, admin):
    r = client.post('/login',
                    data={'email': admin.email, 'password': 'testpass123'},
                    follow_redirects=False)
    assert r.status_code in (302, 303)


def test_login_wrong_password(client, admin):
    r = client.post('/login',
                    data={'email': admin.email, 'password': 'wrongpass'},
                    follow_redirects=True)
    assert r.status_code == 200
    # rimaniamo sulla pagina di login dopo errore
    assert b'login' in r.data.lower() or b'password' in r.data.lower()


def test_login_unknown_email(client):
    r = client.post('/login',
                    data={'email': 'nobody@test.local', 'password': 'x'},
                    follow_redirects=True)
    assert r.status_code == 200


def test_protected_route_redirects_when_anonymous(client):
    r = client.get('/', follow_redirects=False)
    # Flask-Login redirige a /login
    assert r.status_code in (302, 303)
    assert '/login' in r.headers.get('Location', '')


def test_logout(client, admin, research):
    client.post('/login', data={'email': admin.email, 'password': 'testpass123'})
    r = client.get('/logout', follow_redirects=False)
    assert r.status_code in (302, 303)
    # dopo logout, una route protetta deve tornare a login
    r2 = client.get('/', follow_redirects=False)
    assert '/login' in r2.headers.get('Location', '')
