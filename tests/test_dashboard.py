"""Test del helper build_dashboard_data."""
from datetime import datetime, timedelta

from app.services.dashboard import build_dashboard_data
from app.models import Property


def test_empty_research(app, research):
    data = build_dashboard_data(research.id)
    assert data['kpi']['total'] == 0
    assert data['kpi']['avg_price'] is None
    assert data['kpi']['comuni_coperti'] == 0
    assert data['chart_prezzi']['labels'] == []


def test_kpi_counts(app, db, research, municipality):
    db.session.add_all([
        Property(research_id=research.id, municipality_id=municipality.id,
                 title='A', status='Interessante', price=100000),
        Property(research_id=research.id, municipality_id=municipality.id,
                 title='B', status='Interessante', price=200000),
        Property(research_id=research.id, municipality_id=municipality.id,
                 title='C', status='Da valutare', price=300000),
        Property(research_id=research.id, municipality_id=municipality.id,
                 title='D', status='Scartato'),
    ])
    db.session.commit()
    data = build_dashboard_data(research.id)
    kpi = data['kpi']
    assert kpi['total'] == 4
    assert kpi['interessanti'] == 2
    assert kpi['da_valutare'] == 1
    assert kpi['scartati'] == 1
    assert kpi['offerta'] == 0
    # media dei 3 con prezzo: (100k + 200k + 300k) / 3 = 200000
    assert kpi['avg_price'] == 200000
    assert kpi['comuni_coperti'] == 1


def test_chart_stati_structure(app, research, sample_property):
    data = build_dashboard_data(research.id)
    s = data['chart_stati']
    assert s['labels'] == ['Da valutare', 'Interessante', 'Offerta fatta', 'Scartato']
    assert len(s['data']) == 4
    assert len(s['colors']) == 4
    # sample_property è 'Interessante'
    assert s['data'][1] == 1


def test_price_by_mun(app, db, research, municipality):
    db.session.add_all([
        Property(research_id=research.id, municipality_id=municipality.id,
                 title='A', status='Interessante', price=100000),
        Property(research_id=research.id, municipality_id=municipality.id,
                 title='B', status='Interessante', price=200000),
    ])
    db.session.commit()
    data = build_dashboard_data(research.id)
    assert data['chart_prezzi']['labels'] == ['Firenze']
    assert data['chart_prezzi']['data'] == [150000]


def test_isolation_between_researches(app, db, admin, municipality):
    """Properties di una ricerca non devono apparire in un'altra."""
    from app.models import Research
    r1 = Research(name='R1', region='Toscana', created_by=admin.id)
    r2 = Research(name='R2', region='Toscana', created_by=admin.id)
    db.session.add_all([r1, r2])
    db.session.commit()
    db.session.add(Property(research_id=r1.id, municipality_id=municipality.id,
                            title='Solo in R1', status='Interessante'))
    db.session.commit()
    assert build_dashboard_data(r1.id)['kpi']['total'] == 1
    assert build_dashboard_data(r2.id)['kpi']['total'] == 0
