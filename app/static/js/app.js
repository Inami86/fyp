
/* FyP — app.js v0.0.8 */
'use strict';

function esc(str) {
  const d = document.createElement('div');
  d.textContent = String(str ?? '');
  return d.innerHTML;
}

// ── MAPPA ────────────────────────────────────────────────────────────────────
const mapEl = document.getElementById('map');
if (mapEl) {
  const map = L.map('map', { zoomControl: true });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18
  }).addTo(map);

  const statusColors = {
    explored:   '#3d7c28',
    partial:    '#b07800',
    unexplored: '#c5c2bc'
  };

  const propColors = {
    'Interessante':  '#437a22',
    'Da valutare':   '#b07800',
    'Offerta fatta': '#01696f',
    'Scartato':      '#a12c7b'
  };

  let municipalityLayer = null;
  let municipalityMap   = {};  // id → feature layer
  let allBounds         = null;

  fetch('/api/map-data')
    .then(r => r.json())
    .then(data => {

      // ── 1. GeoJSON comuni con colore per stato ─────────────────────────
      if (data.geojson) {
        municipalityLayer = L.geoJSON(data.geojson, {
          style: feature => ({
            fillColor:   statusColors[feature.properties.status] || '#c5c2bc',
            fillOpacity: 0.45,
            color:       '#ffffff',
            weight:      1
          }),
          onEachFeature: (feature, layer) => {
            const name = feature.properties.name;
            layer.bindTooltip(name, { sticky: true, className: 'map-tooltip' });
            layer.on('click', () => onMunicipalityClick(feature, layer, data));
          }
        }).addTo(map);

        // ── AUTO-FIT sulla regione ────────────────────────────────────────
        try {
          allBounds = municipalityLayer.getBounds();
          if (allBounds.isValid()) {
            map.fitBounds(allBounds, { padding: [20, 20], maxZoom: 10 });
          }
        } catch(e) {
          map.setView([39.3, 16.3], 8);  // fallback Calabria
        }

      } else {
        // Nessun GeoJSON: centra sui marker dei comuni
        if (data.municipalities && data.municipalities.length) {
          const lats = data.municipalities.filter(m => m.center_lat).map(m => m.center_lat);
          const lngs = data.municipalities.filter(m => m.center_lng).map(m => m.center_lng);
          if (lats.length) {
            const bounds = L.latLngBounds(
              [Math.min(...lats), Math.min(...lngs)],
              [Math.max(...lats), Math.max(...lngs)]
            );
            map.fitBounds(bounds, { padding: [30, 30], maxZoom: 10 });
          }
        } else {
          map.setView([41.9, 12.5], 6);  // Italia
        }
      }

      // ── 2. Marker immobili ─────────────────────────────────────────────
      (data.properties || []).forEach(p => {
        if (!p.lat || !p.lng) return;
        const color = propColors[p.status] || '#01696f';
        L.circleMarker([p.lat, p.lng], {
          radius: 8, fillColor: color, color: '#fff',
          weight: 2, fillOpacity: 0.9
        })
        .bindTooltip(`🏠 ${p.title}${p.price ? ' — ' + p.price.toLocaleString('it-IT') + ' €' : ''}`)
        .on('click', () => window.location.href = `/properties/${p.id}`)
        .addTo(map);
      });

      // ── 3. Marker contatti ─────────────────────────────────────────────
      (data.contacts || []).forEach(c => {
        if (!c.lat || !c.lng) return;
        L.marker([c.lat, c.lng], {
          icon: L.divIcon({
            html: '<div style="background:#b07800;color:#fff;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;white-space:nowrap">👤</div>',
            className: '', iconAnchor: [10, 10]
          })
        })
        .bindTooltip(`👤 ${c.name}`)
        .on('click', () => window.location.href = `/contacts/${c.id}`)
        .addTo(map);
      });

      // Mappa comuni per click sidebar
      if (municipalityLayer) {
        municipalityLayer.eachLayer(layer => {
          const name = layer.feature?.properties?.name;
          if (name) municipalityMap[name] = layer;
        });
      }
    })
    .catch(err => console.error('Errore caricamento mappa:', err));

  // ── Click comune → sidebar ───────────────────────────────────────────────
  function onMunicipalityClick(feature, layer, data) {
    const name   = feature.properties.name;
    const status = feature.properties.status;
    const mun    = (data.municipalities || []).find(m => m.name === name);
    const props  = (data.properties || []).filter(p => mun && p.municipality_id === mun.id);

    const placeholder = document.getElementById('municipality-placeholder');
    const content     = document.getElementById('municipality-content');
    if (placeholder) placeholder.style.display = 'none';
    if (!content) return;

    const statusLabels = { explored: 'Esplorato', partial: 'Parziale', unexplored: 'Non esplorato' };
    const statusColors2 = { explored: '#d4edda', partial: '#fff3cd', unexplored: '#f3f0ec' };

    let propsHtml = '';
    if (props.length) {
      propsHtml = props.map(p =>
        `<a href="/properties/${p.id}" style="display:block;padding:8px 10px;border-radius:6px;
          background:var(--surface-2);text-decoration:none;color:var(--text);margin-bottom:6px;font-size:13px">
          <div style="font-weight:700">${esc(p.title)}</div>
          <div style="color:var(--muted);font-size:12px">
            ${esc(p.status)}${p.price ? ' · ' + p.price.toLocaleString('it-IT') + ' €' : ''}
          </div>
        </a>`
      ).join('');
    } else {
      propsHtml = '<p style="font-size:13px;color:var(--muted)">Nessun immobile inserito.</p>';
    }

    let statusBtns = '';
    if (document.body.dataset.userRole === 'admin' || document.body.dataset.userRole === 'editor') {
      const munId = mun?.id ?? null;
      statusBtns = `
        <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
          ${['explored','partial','unexplored'].map(s =>
            `<button data-mun-id="${munId}" data-status="${s}" class="btn btn-sm status-btn"
              style="font-size:11px;padding:4px 10px;background:${statusColors2[s]}">
              ${statusLabels[s]}</button>`
          ).join('')}
        </div>`;
    }

    content.style.display = 'block';
    content.innerHTML = `
      <div style="border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:12px">
        <div style="font-size:16px;font-weight:900">${esc(name)}</div>
        <span style="display:inline-block;margin-top:4px;padding:3px 10px;border-radius:99px;
          font-size:11px;font-weight:700;background:${statusColors2[status]};color:var(--text)">
          ${esc(statusLabels[status] || status)}
        </span>
        ${statusBtns}
      </div>
      <div style="font-size:13px;font-weight:700;margin-bottom:8px">
        🏠 Immobili (${props.length})
      </div>
      ${propsHtml}
      ${mun ? `<a href="/properties/new" style="display:block;margin-top:8px;font-size:13px;
        color:var(--primary);font-weight:600">+ Aggiungi immobile qui</a>` : ''}
    `;
    content.querySelectorAll('.status-btn').forEach(btn => {
      btn.addEventListener('click', () => setStatus(parseInt(btn.dataset.munId), btn.dataset.status));
    });
  }

  // ── Cambio stato comune via API ──────────────────────────────────────────
  window.setStatus = function(munId, status) {
    if (!munId) return;
    fetch(`/api/municipality/${munId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content ?? '' },
      body: JSON.stringify({ status })
    })
    .then(r => r.json())
    .then(res => {
      if (res.ok) {
        // Aggiorna colore layer sulla mappa
        const colors = { explored:'#3d7c28', partial:'#b07800', unexplored:'#c5c2bc' };
        if (municipalityLayer) {
          municipalityLayer.eachLayer(layer => {
            if (layer.feature?.properties?.name) {
              const mun = layer.feature.properties;
              if (mun.id === munId || layer._munId === munId) {
                layer.setStyle({ fillColor: colors[status] });
              }
            }
          });
        }
      }
    })
    .catch(console.error);
  };
}

// ── FLASH AUTO-DISMISS ───────────────────────────────────────────────────────
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .4s';
    el.style.opacity    = '0';
    setTimeout(() => el.remove(), 400);
  }, 3500);
});

// ── MINI-MAP (form inserimento/modifica immobile) ────────────────────────────
const miniMapEl = document.getElementById('mini-map');
if (miniMapEl) {
  const latInput  = document.getElementById('property-lat');
  const lngInput  = document.getElementById('property-lng');
  const addrInput = document.getElementById('property-address');
  const geocodeBtn = document.getElementById('geocode-btn');

  // Coordinate iniziali: usa valori già presenti nei campi o centro Italia
  const initLat = parseFloat(latInput?.value) || 41.9;
  const initLng = parseFloat(lngInput?.value) || 12.5;
  const initZoom = (latInput?.value && lngInput?.value) ? 14 : 6;

  const miniMap = L.map('mini-map').setView([initLat, initLng], initZoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(miniMap);

  // Marker draggabile
  let marker = null;

  function placeMarker(lat, lng) {
    if (marker) miniMap.removeLayer(marker);
    marker = L.marker([lat, lng], { draggable: true }).addTo(miniMap);
    marker.on('dragend', e => {
      const pos = e.target.getLatLng();
      if (latInput) latInput.value = pos.lat.toFixed(6);
      if (lngInput) lngInput.value = pos.lng.toFixed(6);
    });
    if (latInput) latInput.value = lat.toFixed(6);
    if (lngInput) lngInput.value = lng.toFixed(6);
  }

  // Se coordinate già presenti (modifica), metti il marker subito
  if (latInput?.value && lngInput?.value) {
    placeMarker(parseFloat(latInput.value), parseFloat(lngInput.value));
  }

  // Click sulla mappa → posiziona marker
  miniMap.on('click', e => {
    placeMarker(e.latlng.lat, e.latlng.lng);
    miniMap.setView(e.latlng, Math.max(miniMap.getZoom(), 13));
  });

  // Pulsante geocodifica indirizzo → Nominatim
  geocodeBtn?.addEventListener('click', () => {
    const addr = addrInput?.value?.trim();
    if (!addr) return;
    geocodeBtn.textContent = '⏳ Ricerca...';
    geocodeBtn.disabled = true;
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(addr)}&limit=1&countrycodes=it`)
      .then(r => r.json())
      .then(results => {
        if (results.length) {
          const lat = parseFloat(results[0].lat);
          const lng = parseFloat(results[0].lon);
          placeMarker(lat, lng);
          miniMap.setView([lat, lng], 15);
        } else {
          alert('Indirizzo non trovato. Prova con un indirizzo più preciso.');
        }
      })
      .catch(() => alert('Errore di rete durante la geocodifica.'))
      .finally(() => {
        geocodeBtn.textContent = '🎯 Geocodifica';
        geocodeBtn.disabled = false;
      });
  });
}
