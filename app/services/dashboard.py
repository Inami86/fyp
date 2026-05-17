from sqlalchemy import func, extract, cast, String
from app import db
from app.models import Property, Municipality


def build_dashboard_data(research_id):
    """Calcola KPI e dati grafici per una ricerca. Usato da dashboard, Excel e PDF."""
    props  = Property.query.filter_by(research_id=research_id).all()
    prezzi = [p.price for p in props if p.price]

    kpi = dict(
        total          = len(props),
        interessanti   = sum(1 for p in props if p.status == 'Interessante'),
        da_valutare    = sum(1 for p in props if p.status == 'Da valutare'),
        offerta        = sum(1 for p in props if p.status == 'Offerta fatta'),
        scartati       = sum(1 for p in props if p.status == 'Scartato'),
        avg_price      = int(sum(prezzi) / len(prezzi)) if prezzi else None,
        comuni_coperti = len({p.municipality_id for p in props if p.municipality_id}),
    )

    chart_stati = {
        'labels': ['Da valutare', 'Interessante', 'Offerta fatta', 'Scartato'],
        'data':   [kpi['da_valutare'], kpi['interessanti'], kpi['offerta'], kpi['scartati']],
        'colors': ['#b07800', '#437a22', '#01696f', '#a12c7b'],
    }

    price_by_mun = (
        db.session.query(Municipality.name, func.avg(Property.price))
        .join(Property, Property.municipality_id == Municipality.id)
        .filter(Property.research_id == research_id, Property.price.isnot(None))
        .group_by(Municipality.name)
        .order_by(func.avg(Property.price).desc())
        .limit(10).all()
    )
    chart_prezzi = {
        'labels': [r[0] for r in price_by_mun],
        'data':   [round(r[1]) for r in price_by_mun],
    }

    month_expr = func.concat(
        cast(extract('year', Property.created_at), String),
        '-',
        func.lpad(cast(extract('month', Property.created_at), String), 2, '0')
    ).label('month')
    monthly_raw = (
        db.session.query(month_expr, func.count(Property.id))
        .filter(Property.research_id == research_id, Property.created_at.isnot(None))
        .group_by('month').order_by('month').all()
    )
    chart_inserimenti = {
        'labels': [r[0] for r in monthly_raw],
        'data':   [r[1] for r in monthly_raw],
    }

    return dict(
        props=props,
        kpi=kpi,
        chart_stati=chart_stati,
        chart_prezzi=chart_prezzi,
        chart_inserimenti=chart_inserimenti,
        price_by_mun=price_by_mun,
    )
