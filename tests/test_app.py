import json
import unittest
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app import app, QUESTIONS_DATA, MASTER_ANSWER_KEY, ATTEMPTS


class SmartQuizPlatformTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True

    def test_01_question_data_integrity(self):
        """Verify that all 180 questions and 12 pages are properly loaded with options."""
        meta = QUESTIONS_DATA["metadata"]
        questions = QUESTIONS_DATA["questions"]

        self.assertEqual(meta["total_pages"], 12)
        self.assertEqual(meta["total_questions"], 180)
        self.assertEqual(len(questions), 180)

        # Check page distribution: exactly 15 questions per page
        page_counts = {}
        for q in questions:
            p = q["page_number"]
            page_counts[p] = page_counts.get(p, 0) + 1
            self.assertIn("question_text", q)
            self.assertTrue(len(q["question_text"]) > 5)
            self.assertIn("options", q)
            self.assertTrue(len(q["options"]) >= 2)
            for opt in q["options"]:
                self.assertIn("id", opt)
                self.assertIn("text", opt)

        self.assertEqual(len(page_counts), 12)
        for p in range(1, 13):
            self.assertEqual(page_counts[p], 15, f"Page {p} should have exactly 15 questions")

    def test_02_answer_key_integrity(self):
        """Verify that master answer key covers all 180 questions and references existing options."""
        questions = QUESTIONS_DATA["questions"]
        self.assertEqual(len(MASTER_ANSWER_KEY), 180)

        for q in questions:
            qid = q["id"]
            self.assertIn(qid, MASTER_ANSWER_KEY)
            key_entry = MASTER_ANSWER_KEY[qid]
            correct_letter = key_entry["correct_answer"]
            self.assertIn(correct_letter, ["A", "B", "C", "D"])
            # Ensure correct option actually exists in question options
            option_ids = [o["id"] for o in q["options"]]
            self.assertIn(correct_letter, option_ids)

    def test_03_diagram_preserved(self):
        """Verify diagram is preserved for Page 1 Question 11."""
        q11 = next(q for q in QUESTIONS_DATA["questions"] if q["page_number"] == 1 and q["original_question_number"] == 11)
        self.assertTrue(q11["has_diagram"])
        self.assertIsNotNone(q11["diagram_url"])
        self.assertIn("diagram", q11["diagram_url"])

    def test_04_api_meta(self):
        """Test GET /api/meta endpoint."""
        res = self.client.get("/api/meta")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_questions"], 180)
        self.assertEqual(data["total_pages"], 12)

    def test_05_start_quiz_configurations(self):
        """Test starting quiz with various counts, filters, and shuffle options."""
        # 1. 15 questions
        res = self.client.post("/api/start", json={"question_count": 15, "mode": "test"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_questions"], 15)

        # 2. Page filter (Page 1 only -> 15 questions)
        res = self.client.post("/api/start", json={"page_filter": "1", "question_count": "all"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_questions"], 15)

        # 3. Page range filter (Pages 1-4 -> 60 questions)
        res = self.client.post("/api/start", json={"page_filter": "1-4", "question_count": "all"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_questions"], 60)

    def test_06_answer_key_privacy(self):
        """CRITICAL: Ensure correct answers and explanations are NEVER leaked through /api/quiz."""
        res = self.client.post("/api/start", json={"question_count": 10, "mode": "test"})
        attempt_id = res.get_json()["attempt_id"]

        quiz_res = self.client.get(f"/api/quiz/{attempt_id}")
        self.assertEqual(quiz_res.status_code, 200)
        quiz_data = quiz_res.get_json()

        for q in quiz_data["questions"]:
            self.assertNotIn("correct_answer", q)
            self.assertNotIn("explanation", q)
            self.assertNotIn("accepted_answer_raw", q)
            self.assertNotIn("private_keys", q)

    def test_07_review_privacy_before_submission(self):
        """Ensure /api/review returns 403 Forbidden before submission."""
        res = self.client.post("/api/start", json={"question_count": 5})
        attempt_id = res.get_json()["attempt_id"]

        rev_res = self.client.get(f"/api/review/{attempt_id}")
        self.assertEqual(rev_res.status_code, 403)

    def test_08_scoring_accuracy(self):
        """Test server-side answer evaluation and score calculations."""
        res = self.client.post("/api/start", json={"question_count": 5, "option_order": "original", "mode": "test"})
        attempt_id = res.get_json()["attempt_id"]

        quiz_res = self.client.get(f"/api/quiz/{attempt_id}")
        questions = quiz_res.get_json()["questions"]
        q0 = questions[0]["id"]
        q1 = questions[1]["id"]
        q2 = questions[2]["id"]

        ans0 = MASTER_ANSWER_KEY[q0]["correct_answer"]
        ans1 = MASTER_ANSWER_KEY[q1]["correct_answer"]
        wrong_ans2 = "A" if MASTER_ANSWER_KEY[q2]["correct_answer"] != "A" else "B"

        submit_payload = {
            "answers": {
                q0: ans0,
                q1: ans1,
                q2: wrong_ans2
            }
        }
        sub_res = self.client.post(f"/api/submit/{attempt_id}", json=submit_payload)
        self.assertEqual(sub_res.status_code, 200)
        result = sub_res.get_json()["result"]

        self.assertEqual(result["total_questions"], 5)
        self.assertEqual(result["attempted"], 3)
        self.assertEqual(result["correct"], 2)
        self.assertEqual(result["incorrect"], 1)
        self.assertEqual(result["unanswered"], 2)
        self.assertEqual(result["score"], 2)
        self.assertEqual(result["percentage"], 40.0)
        self.assertEqual(result["accuracy"], 66.67)

    def test_09_shuffled_options_scoring(self):
        """Verify that when options are shuffled, scoring still maps to the correct text."""
        res = self.client.post("/api/start", json={"question_count": 5, "option_order": "shuffle", "mode": "test"})
        attempt_id = res.get_json()["attempt_id"]

        attempt = ATTEMPTS[attempt_id]
        q0 = attempt["questions"][0]
        qid = q0["id"]

        assigned_letter = attempt["private_keys"][qid]["correct_answer"]
        selected_opt = next(o for o in q0["options"] if o["id"] == assigned_letter)
        master_text = MASTER_ANSWER_KEY[qid]["correct_option_text"]
        self.assertEqual(selected_opt["text"], master_text)

        sub_res = self.client.post(f"/api/submit/{attempt_id}", json={"answers": {qid: assigned_letter}})
        self.assertEqual(sub_res.status_code, 200)
        result = sub_res.get_json()["result"]
        self.assertEqual(result["correct"], 1)

    def test_10_csv_export(self):
        """Test CSV export after submission."""
        res = self.client.post("/api/start", json={"question_count": 5})
        attempt_id = res.get_json()["attempt_id"]
        self.client.post(f"/api/submit/{attempt_id}", json={"answers": {}})

        exp_res = self.client.get(f"/api/export/{attempt_id}")
        self.assertEqual(exp_res.status_code, 200)
        self.assertIn("text/csv", exp_res.headers.get("Content-Type", ""))
        csv_text = exp_res.get_data(as_text=True)
        self.assertIn("Question ID", csv_text)
        self.assertIn("Original Page", csv_text)
        self.assertIn("Status", csv_text)

    def test_11_autosave_and_persistence(self):
        """Test background saving of answers and marked review state."""
        res = self.client.post("/api/start", json={"question_count": 5})
        attempt_id = res.get_json()["attempt_id"]

        # Fetch questions
        quiz_res = self.client.get(f"/api/quiz/{attempt_id}")
        questions = quiz_res.get_json()["questions"]
        q0 = questions[0]["id"]
        q1 = questions[1]["id"]

        # Save answers in progress
        save_res = self.client.post(f"/api/save/{attempt_id}", json={
            "answers": {q0: "B", q1: "C"},
            "marked_review": [q1]
        })
        self.assertEqual(save_res.status_code, 200)
        save_data = save_res.get_json()
        self.assertEqual(save_data["saved_count"], 2)
        self.assertEqual(save_data["marked_count"], 1)

        # Check that GET /api/quiz returns the saved answers
        quiz_res2 = self.client.get(f"/api/quiz/{attempt_id}")
        data2 = quiz_res2.get_json()
        self.assertEqual(data2["answers"].get(q0), "B")
        self.assertEqual(data2["answers"].get(q1), "C")
        self.assertIn(q1, data2["marked_review"])

    def test_12_practice_mode_immediate_feedback(self):
        """Test immediate check in practice mode vs denial in test mode."""
        # 1. Practice mode: allowed
        res = self.client.post("/api/start", json={"question_count": 5, "mode": "practice"})
        attempt_id = res.get_json()["attempt_id"]
        q0 = ATTEMPTS[attempt_id]["questions"][0]["id"]
        correct_ans = ATTEMPTS[attempt_id]["private_keys"][q0]["correct_answer"]

        chk_res = self.client.post(f"/api/check_answer/{attempt_id}", json={
            "question_id": q0,
            "selected_option": correct_ans
        })
        self.assertEqual(chk_res.status_code, 200)
        chk_data = chk_res.get_json()
        self.assertTrue(chk_data["is_correct"])
        self.assertEqual(chk_data["correct_answer"], correct_ans)
        self.assertIn("explanation", chk_data)

        # 2. Test mode: forbidden
        res2 = self.client.post("/api/start", json={"question_count": 5, "mode": "test"})
        attempt_id2 = res2.get_json()["attempt_id"]
        q0_2 = ATTEMPTS[attempt_id2]["questions"][0]["id"]

        chk_res2 = self.client.post(f"/api/check_answer/{attempt_id2}", json={
            "question_id": q0_2,
            "selected_option": "A"
        })
        self.assertEqual(chk_res2.status_code, 403)

    def test_13_submission_idempotency(self):
        """Ensure repeated submissions do not modify an already finalized score."""
        res = self.client.post("/api/start", json={"question_count": 5})
        attempt_id = res.get_json()["attempt_id"]
        q0 = ATTEMPTS[attempt_id]["questions"][0]["id"]
        correct_ans = ATTEMPTS[attempt_id]["private_keys"][q0]["correct_answer"]

        # First submit
        sub1 = self.client.post(f"/api/submit/{attempt_id}", json={"answers": {q0: correct_ans}})
        self.assertEqual(sub1.status_code, 200)
        score1 = sub1.get_json()["result"]["score"]
        self.assertEqual(score1, 1)

        # Second submit with different answers should return existing result, not overwrite
        sub2 = self.client.post(f"/api/submit/{attempt_id}", json={"answers": {}})
        self.assertEqual(sub2.status_code, 200)
        score2 = sub2.get_json()["result"]["score"]
        self.assertEqual(score2, 1)

    def test_14_recent_history_api(self):
        """Test GET /api/history returns completed tests."""
        hist_res = self.client.get("/api/history")
        self.assertEqual(hist_res.status_code, 200)
        history = hist_res.get_json()
        self.assertIsInstance(history, list)
        self.assertTrue(len(history) >= 1)
        self.assertIn("score", history[0])
        self.assertIn("percentage", history[0])


if __name__ == "__main__":
    unittest.main()
