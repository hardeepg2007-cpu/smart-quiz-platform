// Smart Quiz Platform - Quiz Runner JS

let quizState = {
  attemptId: null,
  mode: 'test',
  questions: [],
  currentIndex: 0,
  answers: {},
  markedReview: new Set(),
  timeRemaining: null,
  timerInterval: null,
  saveTimeout: null,
  paletteFilter: 'all',
  warned5Min: false,
  warned1Min: false,
  isSubmitting: false
};

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  initShortcuts();
  await loadQuizData();
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

async function loadQuizData() {
  try {
    const res = await fetch(`/api/quiz/${ATTEMPT_ID}`);
    if (!res.ok) {
      alert("Unable to load quiz session. Returning to home.");
      window.location.href = '/';
      return;
    }

    const data = await res.json();
    if (data.completed) {
      window.location.href = `/results/${ATTEMPT_ID}`;
      return;
    }

    quizState.attemptId = data.attempt_id;
    quizState.mode = data.mode;
    quizState.questions = data.questions;
    quizState.answers = data.answers || {};
    quizState.markedReview = new Set(data.marked_review || []);

    // Mode badge
    const modeBadge = document.getElementById('modeBadge');
    if (quizState.mode === 'practice') {
      modeBadge.className = 'badge bg-info-subtle text-info border border-info-subtle px-2 py-1 rounded-pill';
      modeBadge.innerHTML = '<i class="bi bi-lightbulb me-1"></i> Practice Mode';
      document.getElementById('btnCheckAnswer').classList.remove('d-none');
    }

    // Timer setup
    if (data.time_limit_seconds > 0) {
      document.getElementById('timerContainer').classList.remove('d-none');
      quizState.timeRemaining = data.time_remaining_seconds;
      startTimer();
    }

    renderPalette();
    renderCurrentQuestion();
    updateCounters();
  } catch (err) {
    console.error(err);
    alert("Error loading quiz: " + err.message);
  }
}

function startTimer() {
  updateTimerDisplay();
  quizState.timerInterval = setInterval(() => {
    if (quizState.timeRemaining <= 0) {
      clearInterval(quizState.timerInterval);
      handleTimeExpired();
      return;
    }
    quizState.timeRemaining--;
    updateTimerDisplay();
  }, 1000);
}

function updateTimerDisplay() {
  const s = quizState.timeRemaining;
  if (s === null || s < 0) return;

  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;

  const display = `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  const el = document.getElementById('timerDisplay');
  const badge = document.getElementById('timerBadge');
  if (el) el.innerText = display;

  // Warning thresholds
  if (s <= 60) {
    badge.className = 'timer-badge timer-danger';
    if (!quizState.warned1Min) {
      quizState.warned1Min = true;
      showTimerWarning("1 minute");
    }
  } else if (s <= 300) {
    badge.className = 'timer-badge timer-warning';
    if (!quizState.warned5Min) {
      quizState.warned5Min = true;
      showTimerWarning("5 minutes");
    }
  }
}

function showTimerWarning(timeStr) {
  const banner = document.getElementById('timerWarningBanner');
  const textEl = document.getElementById('timeWarningText');
  if (banner && textEl) {
    textEl.innerText = timeStr;
    banner.classList.remove('d-none');
  }
}

function dismissTimerWarning() {
  document.getElementById('timerWarningBanner')?.classList.add('d-none');
}

function handleTimeExpired() {
  alert("Time has expired! Your quiz will now be submitted automatically.");
  confirmSubmitQuiz(true);
}

function renderCurrentQuestion() {
  const q = quizState.questions[quizState.currentIndex];
  if (!q) return;

  // Progress bar
  const total = quizState.questions.length;
  const progressPct = ((quizState.currentIndex + 1) / total) * 100;
  document.getElementById('quizProgressBar').style.width = `${progressPct}%`;

  // Question header badges
  document.getElementById('questionNumberBadge').innerText = `Question ${quizState.currentIndex + 1} of ${total}`;
  document.getElementById('pageOriginBadge').innerText = `Page ${q.page_number} • Assignment Q#${q.original_question_number}`;

  const reviewNotice = document.getElementById('reviewNoticeBadge');
  if (q.needs_review) {
    reviewNotice.classList.remove('d-none');
    reviewNotice.title = q.review_note || "Flagged for source review";
  } else {
    reviewNotice.classList.add('d-none');
  }

  // Mark for review button state
  const isMarked = quizState.markedReview.has(q.id);
  const markBtn = document.getElementById('btnMarkReview');
  const markIcon = document.getElementById('markIcon');
  const markText = document.getElementById('markText');
  if (isMarked) {
    markBtn.className = 'btn btn-sm btn-warning text-dark rounded-pill px-3';
    markIcon.className = 'bi bi-bookmark-fill me-1';
    markText.innerText = 'Marked';
  } else {
    markBtn.className = 'btn btn-sm btn-outline-warning rounded-pill px-3';
    markIcon.className = 'bi bi-bookmark me-1';
    markText.innerText = 'Mark for Review';
  }

  // Question text
  document.getElementById('questionText').innerText = q.question_text;

  // Diagram
  const diagContainer = document.getElementById('diagramContainer');
  const diagImg = document.getElementById('questionDiagram');
  if (q.has_diagram && q.diagram_url) {
    diagImg.src = q.diagram_url;
    diagContainer.classList.remove('d-none');
  } else {
    diagContainer.classList.add('d-none');
  }

  // Options
  const optionsContainer = document.getElementById('optionsContainer');
  const selected = quizState.answers[q.id];

  optionsContainer.innerHTML = q.options.map(opt => {
    const isSelected = (selected === opt.id);
    return `
      <div class="option-card ${isSelected ? 'selected' : ''}" onclick="selectOption('${opt.id}')" id="optCard_${opt.id}">
        <span class="option-badge">${opt.id}</span>
        <span class="option-text">${opt.text}</span>
      </div>
    `;
  }).join('');

  // Hide practice feedback on question change
  document.getElementById('practiceFeedbackBox').classList.add('d-none');

  // Nav buttons
  document.getElementById('btnPrev').disabled = (quizState.currentIndex === 0);
  const nextBtn = document.getElementById('btnNext');
  if (quizState.currentIndex === total - 1) {
    nextBtn.innerHTML = '<i class="bi bi-send-check me-1"></i> Review & Submit';
    nextBtn.onclick = showSubmitModal;
  } else {
    nextBtn.innerHTML = 'Next <i class="bi bi-arrow-right ms-1"></i>';
    nextBtn.onclick = () => navigateQuestion(1);
  }

  updatePaletteCurrent();
}

function selectOption(letter) {
  const q = quizState.questions[quizState.currentIndex];
  if (!q) return;

  quizState.answers[q.id] = letter;

  // Update option styling
  document.querySelectorAll('.option-card').forEach(card => card.classList.remove('selected'));
  document.getElementById(`optCard_${letter}`)?.classList.add('selected');

  updateCounters();
  updatePaletteCurrent();
  scheduleAutoSave();

  // If in practice mode, auto-check answer
  if (quizState.mode === 'practice') {
    checkCurrentAnswer();
  }
}

function clearCurrentAnswer() {
  const q = quizState.questions[quizState.currentIndex];
  if (!q) return;

  delete quizState.answers[q.id];
  document.querySelectorAll('.option-card').forEach(card => card.classList.remove('selected'));
  document.getElementById('practiceFeedbackBox').classList.add('d-none');

  updateCounters();
  updatePaletteCurrent();
  scheduleAutoSave();
}

function toggleMarkForReview() {
  const q = quizState.questions[quizState.currentIndex];
  if (!q) return;

  if (quizState.markedReview.has(q.id)) {
    quizState.markedReview.delete(q.id);
  } else {
    quizState.markedReview.add(q.id);
  }

  renderCurrentQuestion();
  updateCounters();
  scheduleAutoSave();
}

function navigateQuestion(delta) {
  const newIndex = quizState.currentIndex + delta;
  if (newIndex >= 0 && newIndex < quizState.questions.length) {
    quizState.currentIndex = newIndex;
    renderCurrentQuestion();
  }
}

function jumpToQuestion(index) {
  if (index >= 0 && index < quizState.questions.length) {
    quizState.currentIndex = index;
    renderCurrentQuestion();
  }
}

// Practice mode instant verification
async function checkCurrentAnswer() {
  const q = quizState.questions[quizState.currentIndex];
  const selected = quizState.answers[q.id];
  if (!q || !selected) return;

  try {
    const res = await fetch(`/api/check_answer/${quizState.attemptId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: q.id,
        selected_option: selected
      })
    });

    if (!res.ok) return;
    const feedback = await res.json();

    const box = document.getElementById('practiceFeedbackBox');
    const title = document.getElementById('feedbackTitle');
    const exp = document.getElementById('feedbackExplanation');

    box.classList.remove('d-none', 'feedback-correct', 'feedback-incorrect');
    if (feedback.is_correct) {
      box.classList.add('feedback-correct');
      title.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Correct Answer!';
      title.className = 'd-flex align-items-center gap-2 fw-bold mb-1 text-success';
    } else {
      box.classList.add('feedback-incorrect');
      title.innerHTML = `<i class="bi bi-x-circle-fill me-1"></i> Incorrect. Correct answer is (${feedback.correct_answer}): ${feedback.correct_option_text}`;
      title.className = 'd-flex align-items-center gap-2 fw-bold mb-1 text-danger';
    }

    exp.innerHTML = feedback.explanation ? `<div>${feedback.explanation}</div>` : '';
  } catch (e) {
    console.error('Check answer error', e);
  }
}

// Background autosave
function scheduleAutoSave() {
  if (quizState.saveTimeout) clearTimeout(quizState.saveTimeout);
  quizState.saveTimeout = setTimeout(async () => {
    try {
      await fetch(`/api/save/${quizState.attemptId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answers: quizState.answers,
          marked_review: Array.from(quizState.markedReview)
        })
      });
    } catch (e) {
      console.warn("Autosave failed", e);
    }
  }, 400);
}

// Palette rendering
function renderPalette() {
  const grid = document.getElementById('paletteGrid');
  if (!grid) return;

  const total = quizState.questions.length;
  grid.innerHTML = quizState.questions.map((q, idx) => {
    return `<button class="palette-btn unanswered" id="palBtn_${idx}" onclick="jumpToQuestion(${idx})">${idx + 1}</button>`;
  }).join('');

  updatePaletteCurrent();
}

function updatePaletteCurrent() {
  quizState.questions.forEach((q, idx) => {
    const btn = document.getElementById(`palBtn_${idx}`);
    if (!btn) return;

    const isCurrent = (idx === quizState.currentIndex);
    const isAnswered = Boolean(quizState.answers[q.id]);
    const isMarked = quizState.markedReview.has(q.id);

    // Apply filter visibility
    let visible = true;
    if (quizState.paletteFilter === 'answered' && !isAnswered) visible = false;
    if (quizState.paletteFilter === 'unanswered' && isAnswered) visible = false;
    if (quizState.paletteFilter === 'marked' && !isMarked) visible = false;
    btn.style.display = visible ? 'flex' : 'none';

    // Classes
    btn.className = 'palette-btn';
    if (isAnswered) btn.classList.add('answered');
    else btn.classList.add('unanswered');

    if (isMarked) {
      btn.classList.add('marked');
      if (!btn.querySelector('.marked-dot')) {
        const dot = document.createElement('span');
        dot.className = 'marked-dot';
        btn.appendChild(dot);
      }
    } else {
      const dot = btn.querySelector('.marked-dot');
      if (dot) dot.remove();
    }

    if (isCurrent) {
      btn.classList.add('current');
    }
  });

  const total = quizState.questions.length;
  const answered = Object.keys(quizState.answers).length;
  document.getElementById('paletteProgressText').innerText = `${answered} / ${total}`;
}

function filterPalette(filter) {
  quizState.paletteFilter = filter;
  updatePaletteCurrent();
}

function updateCounters() {
  const total = quizState.questions.length;
  const answered = Object.keys(quizState.answers).length;
  const unanswered = total - answered;
  const marked = quizState.markedReview.size;

  document.getElementById('answeredCountBadge').innerText = `${answered} Answered`;
  document.getElementById('unansweredCountBadge').innerText = `${unanswered} Unanswered`;
  document.getElementById('markedCountBadge').innerText = `${marked} Marked`;
}

// Submission modal and logic
function showSubmitModal() {
  const total = quizState.questions.length;
  const answered = Object.keys(quizState.answers).length;
  const unanswered = total - answered;
  const marked = quizState.markedReview.size;

  document.getElementById('modalAnsweredCount').innerText = answered;
  document.getElementById('modalUnansweredCount').innerText = unanswered;
  document.getElementById('modalMarkedCount').innerText = marked;

  const warnEl = document.getElementById('unansweredWarning');
  if (unanswered > 0 || marked > 0) {
    warnEl.classList.remove('d-none');
  } else {
    warnEl.classList.add('d-none');
  }

  const modalEl = document.getElementById('submitConfirmModal');
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

async function confirmSubmitQuiz(force = false) {
  if (quizState.isSubmitting) return;
  quizState.isSubmitting = true;

  const btn = document.getElementById('btnConfirmSubmit');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Submitting...';
  }

  try {
    const res = await fetch(`/api/submit/${quizState.attemptId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers: quizState.answers })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Submission failed');

    if (quizState.timerInterval) clearInterval(quizState.timerInterval);
    window.location.href = `/results/${quizState.attemptId}`;
  } catch (err) {
    alert('Submission error: ' + err.message);
    quizState.isSubmitting = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = 'Confirm & Submit';
    }
  }
}

// Confirmation if leaving page
function confirmExit() {
  return confirm("Are you sure you want to leave? Your quiz will remain saved in its current state.");
}

// Keyboard shortcuts
function initShortcuts() {
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      navigateQuestion(-1);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      navigateQuestion(1);
    } else if (['1', '2', '3', '4'].includes(e.key)) {
      const letters = ['A', 'B', 'C', 'D'];
      const q = quizState.questions[quizState.currentIndex];
      const idx = parseInt(e.key) - 1;
      if (q && q.options[idx]) {
        selectOption(q.options[idx].id);
      }
    } else if (e.key.toLowerCase() === 'm') {
      toggleMarkForReview();
    } else if (e.key.toLowerCase() === 'c') {
      clearCurrentAnswer();
    }
  });
}
