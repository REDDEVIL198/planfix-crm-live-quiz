from __future__ import annotations

from copy import deepcopy
from typing import Any


def localized(value: Any, language: str = "uk", fallback: str = "uk") -> str:
    if isinstance(value, dict):
        return str(value.get(language) or value.get(fallback) or next(iter(value.values()), ""))
    return "" if value is None else str(value)


def is_correct_answer(question: dict[str, Any], selected_option_id: str | None) -> bool:
    return bool(selected_option_id) and selected_option_id == question.get("correct_option_id")


def max_score(questions: list[dict[str, Any]]) -> int:
    return sum(int(question.get("points", 0)) for question in questions)


def calculate_answers_summary(
    questions: list[dict[str, Any]], answers: dict[str, str]
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for question in questions:
        question_id = str(question.get("id", ""))
        selected_option_id = answers.get(question_id, "")
        correct_option_id = str(question.get("correct_option_id", ""))
        correct = is_correct_answer(question, selected_option_id)
        points = int(question.get("points", 0)) if correct else 0
        summary.append(
            {
                "question_id": question_id,
                "selected_option_id": selected_option_id,
                "correct_option_id": correct_option_id,
                "is_correct": correct,
                "points_awarded": points,
            }
        )
    return summary


def calculate_score(questions: list[dict[str, Any]], answers: dict[str, str]) -> int:
    return sum(item["points_awarded"] for item in calculate_answers_summary(questions, answers))


def percentage(score: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(score / total * 100, 2)


def assign_result_category(results: list[dict[str, Any]], percent: float) -> dict[str, Any]:
    for result in results:
        if float(result.get("min_percentage", 0)) <= percent <= float(result.get("max_percentage", 0)):
            return result
    return results[-1] if results else {}


def validate_questions(questions: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, question in enumerate(questions, start=1):
        question_id = str(question.get("id", "")).strip()
        if not question_id:
            errors.append(f"Question {index}: ID is required.")
        elif question_id in seen_ids:
            errors.append(f"Question {index}: ID '{question_id}' is duplicated.")
        seen_ids.add(question_id)

        if not localized(question.get("question"), "uk").strip():
            errors.append(f"Question {index}: Ukrainian question text is required.")

        options = question.get("options", [])
        if len(options) < 2:
            errors.append(f"Question {index}: at least 2 options are required.")

        option_ids: set[str] = set()
        for option_index, option in enumerate(options, start=1):
            option_id = str(option.get("id", "")).strip()
            if not option_id:
                errors.append(f"Question {index}, option {option_index}: option ID is required.")
            elif option_id in option_ids:
                errors.append(f"Question {index}: option ID '{option_id}' is duplicated.")
            option_ids.add(option_id)
            if not localized(option.get("text"), "uk").strip():
                errors.append(f"Question {index}, option {option_id}: Ukrainian option text is required.")

        correct_option_id = str(question.get("correct_option_id", "")).strip()
        if correct_option_id not in option_ids:
            errors.append(f"Question {index}: correct answer must match one option ID.")

        try:
            points = int(question.get("points", 0))
        except (TypeError, ValueError):
            points = 0
        if points <= 0:
            errors.append(f"Question {index}: points must be an integer greater than 0.")
    return errors


def validate_result_ranges(results: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not results:
        return ["At least one result category is required."]

    normalized: list[tuple[float, float, str]] = []
    for index, result in enumerate(results, start=1):
        title = localized(result.get("title"), "uk").strip()
        if not title:
            errors.append(f"Result {index}: title is required.")
        try:
            min_value = float(result.get("min_percentage"))
            max_value = float(result.get("max_percentage"))
        except (TypeError, ValueError):
            errors.append(f"Result {index}: percentages must be numbers.")
            continue
        if min_value < 0 or max_value > 100:
            errors.append(f"Result {index}: range must stay within 0-100.")
        if min_value > max_value:
            errors.append(f"Result {index}: min percentage must not exceed max percentage.")
        normalized.append((min_value, max_value, title))

    normalized.sort(key=lambda item: item[0])
    if normalized:
        if normalized[0][0] > 0:
            errors.append("Result ranges must start at 0.")
        if normalized[-1][1] < 100:
            errors.append("Result ranges must cover 100.")
        previous_max: float | None = None
        for min_value, max_value, title in normalized:
            if previous_max is not None and min_value <= previous_max:
                errors.append(f"Result range overlaps near '{title}'.")
            if previous_max is not None and min_value > previous_max + 1:
                errors.append(f"Result ranges have a gap before '{title}'.")
            previous_max = max_value
    return errors


def validate_config(config: dict[str, Any]) -> list[str]:
    errors = validate_questions(config.get("questions", []))
    errors.extend(validate_result_ranges(config.get("results", [])))
    return errors


def reset_quiz_session(session_state: Any) -> None:
    for key in ["quiz_started", "current_question", "answers", "participant_name", "department", "result_saved"]:
        if key in session_state:
            del session_state[key]


def move_item(items: list[dict[str, Any]], index: int, direction: int) -> list[dict[str, Any]]:
    new_items = deepcopy(items)
    target = index + direction
    if 0 <= index < len(new_items) and 0 <= target < len(new_items):
        new_items[index], new_items[target] = new_items[target], new_items[index]
    return new_items
