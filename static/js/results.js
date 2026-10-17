// Smart Quiz Platform - Results Dashboard JS

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  await loadResults();
});

// Theme handling
function initTheme() {
  const themeBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');
  const saved = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', saved);
  updateThemeIcon(saved);

  themeBtn?.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
    const target = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', target);
    document.documentElement.setAttribute('data-bs-theme', target);
    updateThemeIcon(target);
  });
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('themeIcon');
  if (icon) {
    icon.className = (theme === 'dark') ? 'bi bi-sun-fill text-warning' : 'bi bi-moon-stars-fill';
  }
}

async function loadResults() {
  try {
    const res = await fetch(`/api/results/${ATTEMPT_ID}`);
    if (!res.ok) {
      alert("Results not found or quiz incomplete.");
      window.location.href = '/';
      return;
    }

    const data = await res.json();
    renderScoreCard(data);
    renderCharts(data);
    renderWeakTopics(data);
  } catch (e) {
    console.error("Failed to load results", e);
    alert("Error loading quiz results: " + e.message);
  }
}

function renderScoreCard(r) {
  // Pass badge
  const passBadge = document.getElementById('passStatusBadge');
  if (r.passed) {
    passBadge.className = 'badge bg-success px-4 py-2 rounded-pill fs-6 fw-bold shadow-sm';
    passBadge.innerHTML = '<i class="bi bi-trophy-fill me-1"></i> PASSED';
  } else {
    passBadge.className = 'badge bg-danger px-4 py-2 rounded-pill fs-6 fw-bold shadow-sm';
    passBadge.innerHTML = '<i class="bi bi-x-octagon-fill me-1"></i> NEEDS PRACTICE';
  }

  // Score & percentage
  document.getElementById('scoreDisplay').innerText = `${r.score} / ${r.total_questions}`;
  document.getElementById('percentageDisplay').innerText = `${r.percentage}% (Passing threshold: ${r.pass_mark}%)`;

  // Feedback message
  const msgEl = document.getElementById('feedbackMessage');
  if (r.percentage >= 85) {
    msgEl.innerText = "Outstanding mastery! You demonstrated comprehensive knowledge across the examined topics.";
  } else if (r.percentage >= r.pass_mark) {
    msgEl.innerText = "Solid achievement! You cleared the passing score. Check the answer review to sharpen any missed topics.";
  } else {
    msgEl.innerText = "Keep going! Review the missed questions below to solidify your understanding of these core concepts.";
  }

  // Stat cards
  document.getElementById('statAttempted').innerText = `${r.attempted} / ${r.total_questions}`;
  document.getElementById('statCorrect').innerText = r.correct;
  document.getElementById('statIncorrect').innerText = r.incorrect;

  // Format time taken
  const secs = r.time_taken_seconds;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  const timeStr = (m > 0) ? `${m}m ${s}s` : `${s}s`;
  document.getElementById('statTimeTaken').innerText = timeStr;

  document.getElementById('accuracyValue').innerText = `${r.accuracy}%`;
}

function renderCharts(r) {
  const isDark = (document.documentElement.getAttribute('data-bs-theme') === 'dark');
  const textColor = isDark ? '#cbd5e1' : '#475569';
  const gridColor = isDark ? '#334155' : '#e2e8f0';

  // 1. Accuracy Doughnut Chart
  const doughnutCtx = document.getElementById('accuracyChart').getContext('2d');
  new Chart(doughnutCtx, {
    type: 'doughnut',
    data: {
      labels: ['Correct', 'Incorrect', 'Unanswered'],
      datasets: [{
        data: [r.correct, r.incorrect, r.unanswered],
        backgroundColor: ['#10b981', '#ef4444', '#94a3b8'],
        borderWidth: 2,
        borderColor: isDark ? '#1e293b' : '#ffffff'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: textColor, padding: 16 }
        }
      },
      cutout: '65%'
    }
  });

  // 2. Bar Chart: Page / Week Performance
  const pageEntries = Object.entries(r.page_performance || {}).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
  const labels = pageEntries.map(e => `Week ${e[0]}`);
  const correctData = pageEntries.map(e => e[1].correct);
  const totalData = pageEntries.map(e => e[1].total);

  const barCtx = document.getElementById('pageBarChart').getContext('2d');
  new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Score (Correct)',
          data: correctData,
          backgroundColor: '#4f46e5',
          borderRadius: 6
        },
        {
          label: 'Total Questions',
          data: totalData,
          backgroundColor: isDark ? '#334155' : '#e2e8f0',
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor }
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: { color: textColor, precision: 0 }
        }
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: textColor }
        }
      }
    }
  });
}

function renderWeakTopics(r) {
  const container = document.getElementById('weakTopicsList');
  const card = document.getElementById('weakAreasCard');

  if (!r.weak_topics || r.weak_topics.length === 0) {
    card.classList.add('d-none');
    return;
  }

  container.innerHTML = r.weak_topics.map(t => {
    return `
      <div class="list-group-item d-flex justify-content-between align-items-center py-3 bg-transparent">
        <div>
          <span class="badge bg-secondary-subtle text-secondary me-2">Page ${t.page} &bull; Q#${t.question_number}</span>
          <span class="text-body">${t.text}</span>
        </div>
        <a href="/review/${r.attempt_id}" class="btn btn-sm btn-outline-danger rounded-pill px-3 ms-2">
          Review <i class="bi bi-chevron-right ms-1"></i>
        </a>
      </div>
    `;
  }).join('');
}
