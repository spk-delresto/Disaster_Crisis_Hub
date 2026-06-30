/* static/js/charts.js — Chart.js dashboard visualisations */

const CHART_COLORS = ["#3b82f6","#ef4444","#f59e0b","#22c55e","#8b5cf6","#f97316","#06b6d4"];
const SEVERITY_PALETTE = { low:"#22c55e", medium:"#f59e0b", high:"#f97316", critical:"#ef4444" };

function loadCharts(apiUrl) {
  fetch(apiUrl)
    .then((r) => r.json())
    .then(({ by_type, by_severity, timeline }) => {
      buildDoughnut("typeChart", by_type.labels, by_type.data, CHART_COLORS);
      buildDoughnut(
        "severityChart",
        by_severity.labels,
        by_severity.data,
        by_severity.labels.map((l) => SEVERITY_PALETTE[l] || "#888"),
      );
      buildLine("timelineChart", timeline.labels, timeline.data);
    })
    .catch(console.error);
}

function buildDoughnut(id, labels, data, colors) {
  new Chart(document.getElementById(id), {
    type: "doughnut",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 2, borderColor: "#111827" }] },
    options: {
      plugins: { legend: { position: "right", labels: { color: "#d1d5db", font: { size: 12 } } } },
      cutout: "60%",
    },
  });
}

function buildLine(id, labels, data) {
  new Chart(document.getElementById(id), {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "New reports",
        data,
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.15)",
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointBackgroundColor: "#3b82f6",
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
        y: { ticks: { color: "#9ca3af", stepSize: 1 }, grid: { color: "#1f2937" }, beginAtZero: true },
      },
    },
  });
}
