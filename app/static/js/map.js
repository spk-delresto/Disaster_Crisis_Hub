const SEVERITY_COLORS = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
};

function initMap(geojsonUrl) {
  const map = L.map("crisis-map").setView([20, 0], 2);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map);

  fetch(geojsonUrl)
    .then((r) => r.json())
    .then((data) => {
      if (!data.features || data.features.length === 0) {
        // Show a message overlay on empty map
        const msg = document.createElement("div");
        msg.style.cssText = "position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(22,27,39,0.85);color:#8892a4;padding:1rem 2rem;border-radius:8px;font-size:.9rem;z-index:1000;pointer-events:none;";
        msg.textContent = "No active disasters to display";
        document.getElementById("crisis-map").style.position = "relative";
        document.getElementById("crisis-map").appendChild(msg);
        return;
      }

      const layer = L.geoJSON(data, {
        pointToLayer(feature, latlng) {
          const p = feature.properties;
          return L.circleMarker(latlng, {
            radius: Math.max(6, Math.min(20, Math.sqrt(p.affected || 100) * 0.8)),
            fillColor: SEVERITY_COLORS[p.severity] || "#888",
            color: "#fff",
            weight: 1.5,
            fillOpacity: 0.85,
          });
        },
        onEachFeature(feature, layer) {
          const p = feature.properties;
          layer.bindPopup(`
            <strong>${p.title}</strong><br>
            Type: ${p.type}<br>
            Severity: <span style="color:${SEVERITY_COLORS[p.severity]}">${p.severity.toUpperCase()}</span><br>
            Affected: ${(p.affected || 0).toLocaleString()} people<br>
            <a href="/crisis/${p.id}" style="color:#3b82f6">View report →</a>
          `);
        },
      }).addTo(map);

      map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 6 });
    })
    .catch(console.error);
}
