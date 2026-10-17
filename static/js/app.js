// Smart Quiz Platform - Home Page JS

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadRecentAttempts();
  bindConfigForm();
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

function setQuickMode(mode) {
  if (mode === 'practice') {
    document.getElementById('modePractice').checked = true;
    document.getElementById('selectTimeLimit').value = '0'; // default untimed for practice
    document.getElementById('selectQuestionCount').value = '15';
  } else {
    document.getElementById('modeTest').checked = true;
    document.getElementById('selectTimeLimit').value = '60';
    document.getElementById('selectQuestionCount').value = 'all';
  }
}

function startPageQuiz(pageNum) {
  // Open config modal with page preselected
  const modalEl = document.getElementById('configModal');
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  document.getElementById('selectPageFilter').value = String(pageNum);
  document.getElementById('selectQuestionCount').value = 'all';
  modal.show();
}

function bindConfigForm() {
  const form = document.getElementById('quizConfigForm');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('btnLaunchQuiz');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Preparing Quiz...';

    const mode = document.querySelector('input[name="quizMode"]:checked').value;
    const question_count = document.getElementById('selectQuestionCount').value;
    const page_filter = document.getElementById('selectPageFilter').value;
    const time_limit = parseInt(document.getElementById('selectTimeLimit').value, 10);
    const pass_mark = parseFloat(document.getElementById('selectPassMark').value);
    const question_order = document.getElementById('selectQuestionOrder').value;
    const option_order = document.getElementById('selectOptionOrder').value;

    try {
      const res = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          question_count,
          page_filter,
          time_limit,
          pass_mark,
          question_order,
          option_order
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to start quiz');
      }

      // Redirect to quiz runner
      window.location.href = `/quiz?attempt_id=${data.attempt_id}`;
    } catch (err) {
      alert('Error launching quiz: ' + err.message);
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="bi bi-rocket-takeoff me-1"></i> Start Quiz Now';
    }
  });
}

async function loadRecentAttempts() {
  const listEl = document.getElementById('recentAttemptsList');
  const countBadge = document.getElementById('historyCount');
  if (!listEl) return;

  try {
    const res = await fetch('/api/history');
    if (!res.ok) return;
    const history = await res.json();

    countBadge.innerText = history.length;
    if (history.length === 0) {
      listEl.innerHTML = '<em>No previous quiz attempts recorded.</em>';
      return;
    }

    listEl.innerHTML = history.slice(0, 5).map(item => {
      const date = new Date(item.completed_at * 1000).toLocaleDateString([], {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
      const badgeClass = item.passed ? 'bg-success' : 'bg-danger';
      const statusText = item.passed ? 'PASSED' : 'FAILED';

      return `
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
          <div>
            <div class="fw-semibold text-body">${item.mode.toUpperCase()} &bull; ${item.score}/${item.total_questions} (${item.percentage}%)</div>
            <div class="small text-muted">${date}</div>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="badge ${badgeClass} rounded-pill">${statusText}</span>
            <a href="/results/${item.attempt_id}" class="btn btn-sm btn-outline-primary rounded-pill py-0 px-2">View</a>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error('Failed to load history', e);
  }
}
