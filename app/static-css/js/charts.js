
const CHART_COLORS = ["#3b82f6","#ef4444","#f59e0b","#22c55e","#8b5cf6","#f97316","#06b6d4"];
const SEVERITY_PALETTE = { low:"#22c55e", medium:"#f59e0b", high:"#f97316", critical:"#ef4444" };

function emptyMessage(id, msg) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const parent = canvas.parentElement;
  canvas.style.display = "none";
  const div = document.createElement("div");
  div.style.cssText = "display:flex;align-items:center;justify-content:center;height:120px;color:#8892a4;font-size:.875rem;";
  div.textContent = msg;
  parent.appendChild(div);
}

function loadCharts(apiUrl) {
  fetch(apiUrl)
    .then((r) => r.json())
    .then(({ by_type, by_severity, timeline }) => {

      // Events by type
      if (by_type.data.length === 0) {
        emptyMessage("typeChart", "No crisis data yet");
      } else {
        buildDoughnut("typeChart", by_type.labels, by_type.data, CHART_COLORS);
      }

      // Events by severity
      if (by_severity.data.length === 0) {
        emptyMessage("severityChart", "No crisis data yet");
      } else {
        buildDoughnut(
          "severityChart",
          by_severity.labels,
          by_severity.data,
          by_severity.labels.map((l) => SEVERITY_PALETTE[l] || "#888"),
        );
      }

      // 7-day timeline — always show even if all zeros
      buildLine("timelineChart", timeline.labels, timeline.data);
    })
    .catch(console.error);
}

function buildDoughnut(id, labels, data, colors) {
  new Chart(document.getElementById(id), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: "#111827"
      }]
    },
    options: {
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#d1d5db", font: { size: 12 }, padding: 16 }
        }
      },
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
        pointRadius: 4,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
        y: {
          ticks: { color: "#9ca3af", stepSize: 1, precision: 0 },
          grid: { color: "#1f2937" },
          beginAtZero: true,
          min: 0,
        },
      },
    },
  });
}
