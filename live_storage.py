from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from quiz_engine import localized, percentage


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "live_quiz.db"
STATE_DEFAULTS = {
    "phase": "lobby",
    "current_question_index": "0",
    "question_started_at": "",
    "active_question_id": "",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_live_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS live_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                joined_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS live_answers (
                participant_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                selected_option_id TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                PRIMARY KEY (participant_id, question_id)
            )
            """
        )
        for key, value in STATE_DEFAULTS.items():
            conn.execute("INSERT OR IGNORE INTO live_state(key, value) VALUES (?, ?)", (key, value))


def get_state() -> dict[str, str]:
    init_live_db()
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM live_state").fetchall()
    state = dict(STATE_DEFAULTS)
    state.update({row["key"]: row["value"] for row in rows})
    return state


def set_state(**values: Any) -> None:
    init_live_db()
    with connect() as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO live_state(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )


def reset_live_session() -> None:
    init_live_db()
    with connect() as conn:
        conn.execute("DELETE FROM live_answers")
        conn.execute("DELETE FROM participants")
        conn.execute("DELETE FROM live_state")
        for key, value in STATE_DEFAULTS.items():
            conn.execute("INSERT INTO live_state(key, value) VALUES (?, ?)", (key, value))


def register_participant(name: str, department: str) -> int:
    init_live_db()
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO participants(name, department, joined_at) VALUES (?, ?, ?)",
            (name.strip(), department.strip(), datetime.now().isoformat(timespec="seconds")),
        )
        return int(cursor.lastrowid)


def get_participant(participant_id: int | None) -> dict[str, Any] | None:
    if not participant_id:
        return None
    init_live_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM participants WHERE id = ?", (participant_id,)).fetchone()
    return dict(row) if row else None


def get_participants() -> list[dict[str, Any]]:
    init_live_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM participants ORDER BY joined_at ASC, id ASC").fetchall()
    return [dict(row) for row in rows]


def save_answer(
    participant_id: int,
    question_id: str,
    selected_option_id: str,
    *,
    state: dict[str, str] | None = None,
    current_question_id: str | None = None,
    timer_expired: bool = False,
) -> dict[str, Any]:
    if timer_expired:
        return {"saved": False, "reason": "time_expired"}

    init_live_db()
    try:
        with connect() as conn:
            state_rows = conn.execute("SELECT key, value FROM live_state").fetchall()
            latest_state = dict(STATE_DEFAULTS)
            latest_state.update({row["key"]: row["value"] for row in state_rows})
            if latest_state.get("phase") != "question":
                return {"saved": False, "reason": "wrong_phase"}
            active_question_id = latest_state.get("active_question_id", "")
            expected_question_id = active_question_id or current_question_id
            if expected_question_id is not None and str(question_id) != str(expected_question_id):
                return {"saved": False, "reason": "wrong_question"}
            existing = conn.execute(
                "SELECT 1 FROM live_answers WHERE participant_id = ? AND question_id = ?",
                (participant_id, question_id),
            ).fetchone()
            if existing:
                return {"saved": False, "reason": "already_answered"}
            conn.execute(
                """
                INSERT INTO live_answers(participant_id, question_id, selected_option_id, submitted_at)
                VALUES (?, ?, ?, ?)
                """,
                (participant_id, question_id, selected_option_id, datetime.now().isoformat(timespec="seconds")),
            )
    except sqlite3.OperationalError:
        return {"saved": False, "reason": "database_busy"}
    except sqlite3.IntegrityError:
        return {"saved": False, "reason": "already_answered"}
    return {"saved": True, "reason": "ok"}


def get_answer(participant_id: int, question_id: str) -> dict[str, Any] | None:
    init_live_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM live_answers WHERE participant_id = ? AND question_id = ?",
            (participant_id, question_id),
        ).fetchone()
    return dict(row) if row else None


def count_answers_for_question(question_id: str) -> int:
    init_live_db()
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM live_answers WHERE question_id = ?", (question_id,)).fetchone()
    return int(row["total"])


def answer_counts_for_question(question_id: str) -> dict[str, int]:
    init_live_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT selected_option_id, COUNT(*) AS total
            FROM live_answers
            WHERE question_id = ?
            GROUP BY selected_option_id
            """,
            (question_id,),
        ).fetchall()
    return {str(row["selected_option_id"]): int(row["total"]) for row in rows}


def build_leaderboard(config: dict[str, Any], language: str) -> list[dict[str, Any]]:
    init_live_db()
    questions = config.get("questions", [])
    question_by_id = {str(question.get("id")): question for question in questions}
    max_points = sum(int(question.get("points", 0)) for question in questions)
    participants = get_participants()
    with connect() as conn:
        answer_rows = conn.execute("SELECT * FROM live_answers").fetchall()

    answers_by_participant: dict[int, list[sqlite3.Row]] = {}
    for row in answer_rows:
        answers_by_participant.setdefault(int(row["participant_id"]), []).append(row)

    leaderboard: list[dict[str, Any]] = []
    for participant in participants:
        participant_id = int(participant["id"])
        score = 0
        correct_count = 0
        answered_count = 0
        summary = []
        for answer in answers_by_participant.get(participant_id, []):
            question = question_by_id.get(str(answer["question_id"]))
            if not question:
                continue
            answered_count += 1
            is_correct = answer["selected_option_id"] == question.get("correct_option_id")
            points_awarded = int(question.get("points", 0)) if is_correct else 0
            score += points_awarded
            correct_count += 1 if is_correct else 0
            summary.append(
                {
                    "question_id": answer["question_id"],
                    "selected_option_id": answer["selected_option_id"],
                    "correct_option_id": question.get("correct_option_id"),
                    "is_correct": is_correct,
                    "points_awarded": points_awarded,
                }
            )
        leaderboard.append(
            {
                "participant_id": participant_id,
                "name": participant["name"],
                "department": participant["department"],
                "score": score,
                "max_score": max_points,
                "percentage": percentage(score, max_points),
                "correct_answers": correct_count,
                "answered_questions": answered_count,
                "answers_summary": summary,
            }
        )
    leaderboard.sort(key=lambda item: (-item["score"], -item["correct_answers"], item["name"].lower()))
    for place, row in enumerate(leaderboard, start=1):
        row["place"] = place
        row["display"] = f"{place}. {row['name']} - {row['score']}/{row['max_score']} ({row['percentage']}%)"
    return leaderboard


def leaderboard_as_csv(config: dict[str, Any], language: str) -> str:
    rows = build_leaderboard(config, language)
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "place",
            "name",
            "department",
            "score",
            "max_score",
            "percentage",
            "correct_answers",
            "answered_questions",
            "answers_summary",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "place": row["place"],
                "name": row["name"],
                "department": row["department"],
                "score": row["score"],
                "max_score": row["max_score"],
                "percentage": row["percentage"],
                "correct_answers": row["correct_answers"],
                "answered_questions": row["answered_questions"],
                "answers_summary": json.dumps(row["answers_summary"], ensure_ascii=False),
            }
        )
    return output.getvalue()


def current_question(config: dict[str, Any], state: dict[str, str]) -> dict[str, Any] | None:
    questions = config.get("questions", [])
    try:
        index = int(state.get("current_question_index", "0"))
    except ValueError:
        index = 0
    if 0 <= index < len(questions):
        return questions[index]
    return None


def current_question_index(state: dict[str, str]) -> int:
    try:
        return int(state.get("current_question_index", "0"))
    except ValueError:
        return 0


def question_started_timestamp(state: dict[str, str]) -> float | None:
    value = state.get("question_started_at", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def option_text(question: dict[str, Any], option_id: str, language: str) -> str:
    option = next((item for item in question.get("options", []) if item.get("id") == option_id), {})
    return localized(option.get("text"), language)

