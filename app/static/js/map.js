
const SEVERITY_COLORS = {
  low: "#22c55e", medium: "#f59e0b", high: "#f97316", critical: "#ef4444",
};

function initMap(geojsonUrl) {
  const map = L.map("crisis-map", { zoomControl: true }).setView([20, 0], 2);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: "© OpenStreetMap © CARTO",
    maxZoom: 18,
  }).addTo(map);

  fetch(geojsonUrl)
    .then(r => r.json())
    .then(data => {
      if (!data.features || data.features.length === 0) {
        const msg = document.createElement("div");
        msg.style.cssText = "position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(255,255,255,0.9);color:#64748b;padding:1rem 2rem;border-radius:10px;font-size:.875rem;z-index:1000;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.1);";
        msg.innerHTML = "📍 No active disasters to display";
        document.getElementById("crisis-map").style.position = "relative";
        document.getElementById("crisis-map").appendChild(msg);
        return;
      }

      const layer = L.geoJSON(data, {
        pointToLayer(feature, latlng) {
          const p = feature.properties;
          const color = SEVERITY_COLORS[p.severity] || "#888";
          return L.circleMarker(latlng, {
            radius: Math.max(8, Math.min(22, Math.sqrt(p.affected || 100) * 0.9)),
            fillColor: color,
            color: "#fff",
            weight: 2.5,
            fillOpacity: 0.88,
          });
        },
        onEachFeature(feature, layer) {
          const p = feature.properties;
          layer.bindPopup(`
            <div style="font-family:system-ui;min-width:200px;">
              <div style="font-weight:800;font-size:.95rem;color:#0f172a;margin-bottom:.5rem;">${p.title}</div>
              <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.5rem;">
                <span style="background:#f1f5f9;color:#475569;padding:.15rem .5rem;border-radius:4px;font-size:.72rem;font-weight:700;text-transform:capitalize;">${p.type}</span>
                <span style="background:${SEVERITY_COLORS[p.severity]}22;color:${SEVERITY_COLORS[p.severity]};padding:.15rem .5rem;border-radius:4px;font-size:.72rem;font-weight:700;text-transform:uppercase;">${p.severity}</span>
              </div>
              <div style="font-size:.8rem;color:#64748b;">👥 ${(p.affected||0).toLocaleString()} affected</div>
              <a href="/crisis/${p.id}" style="display:block;margin-top:.75rem;color:#1d4ed8;font-size:.8rem;font-weight:700;">View report →</a>
            </div>
          `);
        },
      }).addTo(map);

      if (data.features.length > 0) {
        map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 7 });
      }
    })
    .catch(console.error);
}
