import json
import os
import random
import time
import uuid
from io import StringIO
from pathlib import Path
from flask import Flask, jsonify, render_template, request, Response, redirect, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "smart-quiz-platform-secret-2026")

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
ANSWER_KEY_FILE = BASE_DIR / "answer_key.json"
DATA_DIR = BASE_DIR / "data"
ATTEMPTS_FILE = DATA_DIR / "attempts.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# In-memory store backed by file
ATTEMPTS = {}


def load_data():
    if not QUESTIONS_FILE.exists() or not ANSWER_KEY_FILE.exists():
        raise RuntimeError("questions.json or answer_key.json not found!")
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        q_data = json.load(f)
    with open(ANSWER_KEY_FILE, "r", encoding="utf-8") as f:
        ak_data = json.load(f)
    return q_data, ak_data


QUESTIONS_DATA, MASTER_ANSWER_KEY = load_data()


def save_attempts():
    try:
        with open(ATTEMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(ATTEMPTS, f, indent=2)
    except Exception as e:
        app.logger.error(f"Failed to save attempts: {e}")


def load_saved_attempts():
    global ATTEMPTS
    if ATTEMPTS_FILE.exists():
        try:
            with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
                ATTEMPTS = json.load(f)
        except Exception:
            ATTEMPTS = {}


load_saved_attempts()


# --- HTML PAGE ROUTES ---

@app.route("/")
def index():
    meta = QUESTIONS_DATA["metadata"]
    return render_template("index.html", meta=meta)


@app.route("/quiz")
def quiz():
    attempt_id = request.args.get("attempt_id")
    if not attempt_id or attempt_id not in ATTEMPTS:
        return redirect(url_for("index"))
    return render_template("quiz.html", attempt_id=attempt_id)


@app.route("/results/<attempt_id>")
def results(attempt_id):
    if attempt_id not in ATTEMPTS:
        return redirect(url_for("index"))
    attempt = ATTEMPTS[attempt_id]
    if not attempt.get("completed"):
        return redirect(url_for("quiz", attempt_id=attempt_id))
    return render_template("results.html", attempt_id=attempt_id)


@app.route("/review/<attempt_id>")
def review(attempt_id):
    if attempt_id not in ATTEMPTS:
        return redirect(url_for("index"))
    attempt = ATTEMPTS[attempt_id]
    if not attempt.get("completed"):
        return redirect(url_for("quiz", attempt_id=attempt_id))
    return render_template("review.html", attempt_id=attempt_id)


# --- REST API ROUTES ---

@app.route("/api/meta", methods=["GET"])
def api_meta():
    return jsonify(QUESTIONS_DATA["metadata"])


@app.route("/api/start", methods=["POST"])
def api_start():
    req = request.get_json() or {}
    
    question_count = req.get("question_count", "all")
    time_limit = int(req.get("time_limit", 0))  # in minutes; 0 = no limit
    question_order = req.get("question_order", "original")  # 'original' or 'random'
    option_order = req.get("option_order", "original")  # 'original' or 'shuffle'
    page_filter = req.get("page_filter", "all")  # 'all' or '1'..'12' or '1-6'
    mode = req.get("mode", "test")  # 'test' or 'practice'
    pass_mark = float(req.get("pass_mark", 50.0))
    
    all_qs = list(QUESTIONS_DATA["questions"])
    
    # Filter by page if requested
    if page_filter != "all":
        try:
            if "-" in str(page_filter):
                p_start, p_end = map(int, page_filter.split("-"))
                all_qs = [q for q in all_qs if p_start <= q["page_number"] <= p_end]
            else:
                p_num = int(page_filter)
                all_qs = [q for q in all_qs if q["page_number"] == p_num]
        except ValueError:
            pass  # fallback to all
            
    if not all_qs:
        return jsonify({"error": "No questions matched the selected filter"}), 400
        
    # Question ordering
    if question_order == "random":
        random.shuffle(all_qs)
        
    # Limit question count
    if question_count != "all":
        try:
            count = int(question_count)
            all_qs = all_qs[:min(count, len(all_qs))]
        except ValueError:
            pass
            
    attempt_id = str(uuid.uuid4())
    
    # Prepare public question payload and private server-side key mapping
    public_questions = []
    private_keys = {}
    
    for q in all_qs:
        qid = q["id"]
        opts = list(q["options"])
        
        # Original correct answer letter (e.g. 'B')
        orig_master = MASTER_ANSWER_KEY.get(qid, {})
        orig_correct_letter = orig_master.get("correct_answer")
        orig_correct_text = orig_master.get("correct_option_text")
        
        if option_order == "shuffle":
            shuffled_opts = list(opts)
            random.shuffle(shuffled_opts)
            # Re-label option IDs A, B, C, D in their new display order
            display_opts = []
            shuffled_correct_letter = None
            for idx, opt in enumerate(shuffled_opts):
                new_letter = chr(ord('A') + idx)
                display_opts.append({
                    "id": new_letter,
                    "text": opt["text"],
                    "original_id": opt["id"]
                })
                if opt["id"] == orig_correct_letter:
                    shuffled_correct_letter = new_letter
            public_opts = [{"id": o["id"], "text": o["text"]} for o in display_opts]
            assigned_correct_letter = shuffled_correct_letter
        else:
            public_opts = [{"id": o["id"], "text": o["text"]} for o in opts]
            assigned_correct_letter = orig_correct_letter
            
        public_questions.append({
            "id": qid,
            "page_number": q["page_number"],
            "original_question_number": q["original_question_number"],
            "question_text": q["question_text"],
            "options": public_opts,
            "has_diagram": q.get("has_diagram", False),
            "diagram_url": q.get("diagram_url"),
            "needs_review": q.get("needs_review", False),
            "review_note": q.get("review_note")
        })
        
        private_keys[qid] = {
            "correct_answer": assigned_correct_letter,
            "correct_option_text": orig_correct_text,
            "explanation": orig_master.get("explanation", ""),
            "accepted_answer_raw": orig_master.get("accepted_answer_raw", "")
        }
        
    attempt_record = {
        "id": attempt_id,
        "mode": mode,
        "pass_mark": pass_mark,
        "created_at": time.time(),
        "time_limit_minutes": time_limit,
        "time_limit_seconds": time_limit * 60 if time_limit > 0 else 0,
        "questions": public_questions,
        "private_keys": private_keys,
        "answers": {},
        "marked_review": [],
        "completed": False,
        "result": None
    }
    
    ATTEMPTS[attempt_id] = attempt_record
    save_attempts()
    
    return jsonify({
        "status": "success",
        "attempt_id": attempt_id,
        "total_questions": len(public_questions),
        "time_limit_minutes": time_limit,
        "time_limit_seconds": attempt_record["time_limit_seconds"],
        "mode": mode
    })


@app.route("/api/quiz/<attempt_id>", methods=["GET"])
def api_quiz(attempt_id):
    if attempt_id not in ATTEMPTS:
        return jsonify({"error": "Attempt not found"}), 404
        
    attempt = ATTEMPTS[attempt_id]
    
    # Calculate time remaining if timer enabled
    time_remaining = None
    if attempt["time_limit_seconds"] > 0:
        elapsed = time.time() - attempt["created_at"]
        time_remaining = max(0, int(attempt["time_limit_seconds"] - elapsed))
        
    return jsonify({
        "attempt_id": attempt_id,
        "mode": attempt["mode"],
        "pass_mark": attempt["pass_mark"],
        "total_questions": len(attempt["questions"]),
        "time_limit_seconds": attempt["time_limit_seconds"],
        "time_remaining_seconds": time_remaining,
        "questions": attempt["questions"],
        "answers": attempt["answers"],
        "marked_review": attempt["marked_review"],
        "completed": attempt["completed"]
    })


@app.route("/api/save/<attempt_id>", methods=["POST"])
def api_save(attempt_id):
    if attempt_id not in ATTEMPTS:
        return jsonify({"error": "Attempt not found"}), 404
        
    attempt = ATTEMPTS[attempt_id]
    if attempt["completed"]:
        return jsonify({"error": "Attempt already completed"}), 400
        
    req = request.get_json() or {}
    new_answers = req.get("answers", {})
    marked = req.get("marked_review", [])
    
    # Validate question ids
    valid_qids = {q["id"] for q in attempt["questions"]}
    for qid, ans in new_answers.items():
        if qid in valid_qids:
            attempt["answers"][qid] = str(ans)
            
    attempt["marked_review"] = [qid for qid in marked if qid in valid_qids]
    save_attempts()
    
    return jsonify({
        "status": "saved",
        "saved_count": len(attempt["answers"]),
        "marked_count": len(attempt["marked_review"])
    })


@app.route("/api/check_answer/<attempt_id>", methods=["POST"])
def api_check_answer(attempt_id):
    if attempt_id not in ATTEMPTS:
        return jsonify({"error": "Attempt not found"}), 404
        
    attempt = ATTEMPTS[attempt_id]
    if attempt["mode"] != "practice":
        return jsonify({"error": "Immediate answer check only available in Practice Mode"}), 403
        
    req = request.get_json() or {}
    qid = req.get("question_id")
    selected_option = req.get("selected_option")
    
    if not qid or qid not in attempt["private_keys"]:
        return jsonify({"error": "Invalid question ID"}), 400
        
    key_info = attempt["private_keys"][qid]
    correct_letter = key_info["correct_answer"]
    is_correct = (selected_option == correct_letter)
    
    # Record answer in attempt
    if selected_option:
        attempt["answers"][qid] = selected_option
        save_attempts()
        
    return jsonify({
        "question_id": qid,
        "selected_option": selected_option,
        "is_correct": is_correct,
        "correct_answer": correct_letter,
        "correct_option_text": key_info["correct_option_text"],
        "explanation": key_info["explanation"]
    })


@app.route("/api/submit/<attempt_id>", methods=["POST"])
def api_submit(attempt_id):
    if attempt_id not in ATTEMPTS:
        return jsonify({"error": "Attempt not found"}), 404
        
    attempt = ATTEMPTS[attempt_id]
    
    # If already completed, return existing result (idempotency)
    if attempt["completed"] and attempt.get("result"):
        return jsonify({"status": "already_submitted", "result": attempt["result"]})
        
    req = request.get_json() or {}
    if "answers" in req and isinstance(req["answers"], dict):
        valid_qids = {q["id"] for q in attempt["questions"]}
        for qid, ans in req["answers"].items():
            if qid in valid_qids:
                attempt["answers"][qid] = str(ans)
                
    time_taken = int(time.time() - attempt["created_at"])
    if attempt["time_limit_seconds"] > 0:
        time_taken = min(time_taken, attempt["time_limit_seconds"])
        
    total_questions = len(attempt["questions"])
    correct = 0
    incorrect = 0
    unanswered = 0
    
    page_stats = {}
    weak_topics = []
    
    for q in attempt["questions"]:
        qid = q["id"]
        p = q["page_number"]
        if p not in page_stats:
            page_stats[p] = {"total": 0, "correct": 0, "incorrect": 0, "unanswered": 0}
        page_stats[p]["total"] += 1
        
        user_ans = attempt["answers"].get(qid)
        correct_ans = attempt["private_keys"][qid]["correct_answer"]
        
        if not user_ans:
            unanswered += 1
            page_stats[p]["unanswered"] += 1
        elif user_ans == correct_ans:
            correct += 1
            page_stats[p]["correct"] += 1
        else:
            incorrect += 1
            page_stats[p]["incorrect"] += 1
            weak_topics.append({
                "question_id": qid,
                "page": p,
                "question_number": q["original_question_number"],
                "text": q["question_text"][:90] + ("..." if len(q["question_text"]) > 90 else "")
            })
            
    attempted = correct + incorrect
    percentage = round((correct / total_questions) * 100, 2) if total_questions > 0 else 0.0
    accuracy = round((correct / attempted) * 100, 2) if attempted > 0 else 0.0
    passed = percentage >= attempt["pass_mark"]
    
    result = {
        "attempt_id": attempt_id,
        "total_questions": total_questions,
        "attempted": attempted,
        "unanswered": unanswered,
        "correct": correct,
        "incorrect": incorrect,
        "score": correct,
        "percentage": percentage,
        "accuracy": accuracy,
        "time_taken_seconds": time_taken,
        "pass_mark": attempt["pass_mark"],
        "passed": passed,
        "completed_at": time.time(),
        "page_performance": page_stats,
        "weak_topics": weak_topics[:10]
    }
    
    attempt["completed"] = True
    attempt["result"] = result
    save_attempts()
    
    return jsonify({"status": "success", "result": result})


@app.route("/api/results/<attempt_id>", methods=["GET"])
def api_results(attempt_id):
    if attempt_id not in ATTEMPTS:
        return jsonify({"error": "Attempt not found"}), 404
    attempt = ATTEMPTS[attempt_id]
    if not attempt.get("completed"):
        return jsonify({"error": "Quiz not yet submitted"}), 400
    return jsonify(attempt["result"])


@app.route("/api/review/<attempt_id>", methods=["GET"])
def api_review(attempt_id):
    if attempt_id not in ATTEMPTS:
        return jsonify({"error": "Attempt not found"}), 404
        
    attempt = ATTEMPTS[attempt_id]
    if not attempt.get("completed"):
        return jsonify({"error": "Review available only after submission"}), 403
        
    review_data = []
    for q in attempt["questions"]:
        qid = q["id"]
        key_info = attempt["private_keys"][qid]
        correct_letter = key_info["correct_answer"]
        user_choice = attempt["answers"].get(qid)
        is_unanswered = (user_choice is None or user_choice == "")
        is_correct = (user_choice == correct_letter) if not is_unanswered else False
        
        # Find option texts
        selected_text = None
        correct_text = None
        for o in q["options"]:
            if o["id"] == user_choice:
                selected_text = o["text"]
            if o["id"] == correct_letter:
                correct_text = o["text"]
                
        review_data.append({
            "id": qid,
            "page_number": q["page_number"],
            "original_question_number": q["original_question_number"],
            "question_text": q["question_text"],
            "has_diagram": q.get("has_diagram", False),
            "diagram_url": q.get("diagram_url"),
            "options": q["options"],
            "selected_option": user_choice,
            "selected_text": selected_text,
            "correct_option": correct_letter,
            "correct_text": correct_text,
            "is_correct": is_correct,
            "is_unanswered": is_unanswered,
            "marked_for_review": qid in attempt.get("marked_review", []),
            "explanation": key_info["explanation"],
            "accepted_answer_raw": key_info["accepted_answer_raw"],
            "needs_review": q.get("needs_review", False),
            "review_note": q.get("review_note")
        })
        
    return jsonify({
        "attempt_id": attempt_id,
        "result": attempt["result"],
        "review": review_data
    })


@app.route("/api/export/<attempt_id>", methods=["GET"])
def api_export(attempt_id):
    if attempt_id not in ATTEMPTS:
        return "Attempt not found", 404
    attempt = ATTEMPTS[attempt_id]
    if not attempt.get("completed"):
        return "Attempt not completed yet", 400
        
    import csv
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Question ID", "Original Page", "Original Question #", "Question Text",
        "Your Selected Answer", "Correct Answer", "Status", "Score"
    ])
    
    for q in attempt["questions"]:
        qid = q["id"]
        key_info = attempt["private_keys"][qid]
        correct_letter = key_info["correct_answer"]
        user_choice = attempt["answers"].get(qid, "")
        
        if not user_choice:
            status = "Unanswered"
            score = 0
        elif user_choice == correct_letter:
            status = "Correct"
            score = 1
        else:
            status = "Incorrect"
            score = 0
            
        writer.writerow([
            qid,
            q["page_number"],
            q["original_question_number"],
            q["question_text"],
            user_choice,
            correct_letter,
            status,
            score
        ])
        
    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=quiz_results_{attempt_id[:8]}.csv"}
    )


@app.route("/api/history", methods=["GET"])
def api_history():
    history = []
    for aid, att in ATTEMPTS.items():
        if att.get("completed") and att.get("result"):
            history.append({
                "attempt_id": aid,
                "mode": att.get("mode"),
                "total_questions": att["result"]["total_questions"],
                "score": att["result"]["score"],
                "percentage": att["result"]["percentage"],
                "passed": att["result"]["passed"],
                "completed_at": att["result"].get("completed_at", att.get("created_at"))
            })
    # Sort descending by date
    history.sort(key=lambda x: x["completed_at"], reverse=True)
    return jsonify(history[:10])


if __name__ == "__main__":
    print("Starting Smart Quiz Platform...")
    print(f"Total verified questions loaded: {QUESTIONS_DATA['metadata']['total_questions']}")
    app.run(host="127.0.0.1", port=5000, debug=True)
