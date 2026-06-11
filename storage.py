from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "default_quiz.json"
TEMPLATE_CONFIG_PATH = BASE_DIR / "default_quiz.template.json"
QUIZZES_DIR = BASE_DIR / "quizzes"
ACTIVE_QUIZ_PATH = QUIZZES_DIR / "active_quiz.json"
DEFAULT_QUIZ_FILE = "planfix_crm_challenge.json"
RESULTS_PATH = BASE_DIR / "results.csv"
RESULT_COLUMNS = [
    "timestamp",
    "participant_name",
    "department",
    "score",
    "max_score",
    "percentage",
    "result_category",
    "answers_summary",
]


def load_quiz_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    ensure_quiz_store()
    if path == CONFIG_PATH:
        return load_active_quiz_config()
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_quiz_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    ensure_quiz_store()
    target = get_active_quiz_path() if path == CONFIG_PATH else path
    with target.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def reset_quiz_config(template_path: Path = TEMPLATE_CONFIG_PATH, path: Path = CONFIG_PATH) -> dict[str, Any]:
    template = load_raw_quiz_config(template_path)
    save_quiz_config(template, path)
    return template


def export_config(config: dict[str, Any]) -> str:
    return json.dumps(config, ensure_ascii=False, indent=2)


def load_raw_quiz_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def ensure_quiz_store() -> None:
    QUIZZES_DIR.mkdir(exist_ok=True)
    default_target = QUIZZES_DIR / DEFAULT_QUIZ_FILE
    if not default_target.exists():
        source = CONFIG_PATH if CONFIG_PATH.exists() else TEMPLATE_CONFIG_PATH
        shutil.copyfile(source, default_target)
    if not ACTIVE_QUIZ_PATH.exists():
        set_active_quiz_file(DEFAULT_QUIZ_FILE)
    active = get_active_quiz_file()
    if not (QUIZZES_DIR / active).exists():
        set_active_quiz_file(DEFAULT_QUIZ_FILE)


def list_quiz_files() -> list[str]:
    ensure_quiz_store()
    return sorted(path.name for path in QUIZZES_DIR.glob("*.json") if path.name != ACTIVE_QUIZ_PATH.name)


def get_active_quiz_file() -> str:
    if not ACTIVE_QUIZ_PATH.exists():
        return DEFAULT_QUIZ_FILE
    try:
        data = json.loads(ACTIVE_QUIZ_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_QUIZ_FILE
    filename = sanitize_quiz_filename(str(data.get("active_quiz_file", DEFAULT_QUIZ_FILE)))
    return filename or DEFAULT_QUIZ_FILE


def get_active_quiz_path() -> Path:
    ensure_quiz_store()
    return QUIZZES_DIR / get_active_quiz_file()


def set_active_quiz_file(filename: str) -> None:
    QUIZZES_DIR.mkdir(exist_ok=True)
    safe_name = sanitize_quiz_filename(filename)
    if not safe_name:
        raise ValueError("Quiz filename is required.")
    if not (QUIZZES_DIR / safe_name).exists() and safe_name != DEFAULT_QUIZ_FILE:
        raise FileNotFoundError(safe_name)
    ACTIVE_QUIZ_PATH.write_text(json.dumps({"active_quiz_file": safe_name}, indent=2), encoding="utf-8")


def load_active_quiz_config() -> dict[str, Any]:
    ensure_quiz_store()
    return load_raw_quiz_config(get_active_quiz_path())


def save_active_quiz_config(config: dict[str, Any]) -> None:
    save_quiz_config(config, get_active_quiz_path())


def sanitize_quiz_filename(filename: str) -> str:
    name = Path(filename).name.strip().lower()
    if name.endswith(".json"):
        name = name[:-5]
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie",
        "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l",
        "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "ю": "iu", "я": "ia",
        "ы": "y", "э": "e", "ё": "e", "ъ": "",
    }
    name = "".join(translit.get(char, char) for char in name)
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    if not name:
        name = datetime.now().strftime("quiz_%Y_%m_%d_%H%M")
    return f"{name}.json"


def unique_quiz_filename(filename: str) -> str:
    safe_name = sanitize_quiz_filename(filename)
    stem = Path(safe_name).stem
    suffix = Path(safe_name).suffix
    candidate = safe_name
    counter = 2
    while (QUIZZES_DIR / candidate).exists():
        candidate = f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def merge_quiz_defaults(config: dict[str, Any], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = fallback or load_raw_quiz_config(TEMPLATE_CONFIG_PATH)
    merged = dict(config)
    for key in ["labels", "branding", "security", "live_quiz"]:
        if not isinstance(merged.get(key), dict):
            merged[key] = fallback.get(key, {})
        else:
            base = dict(fallback.get(key, {}))
            base.update(merged[key])
            merged[key] = base
    for key in ["quiz_title", "quiz_subtitle", "intro_text", "final_message"]:
        merged.setdefault(key, fallback.get(key, {"uk": "", "en": ""}))
    return merged


def save_uploaded_quiz(file_bytes: bytes, filename: str) -> str:
    ensure_quiz_store()
    config = json.loads(file_bytes.decode("utf-8-sig"))
    config = merge_quiz_defaults(config)
    safe_name = unique_quiz_filename(filename)
    (QUIZZES_DIR / safe_name).write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    set_active_quiz_file(safe_name)
    return safe_name


def create_quiz_from_current(new_filename: str) -> str:
    ensure_quiz_store()
    safe_name = unique_quiz_filename(new_filename)
    shutil.copyfile(get_active_quiz_path(), QUIZZES_DIR / safe_name)
    set_active_quiz_file(safe_name)
    return safe_name


def create_blank_quiz(new_filename: str) -> str:
    ensure_quiz_store()
    fallback = load_raw_quiz_config(TEMPLATE_CONFIG_PATH)
    blank = merge_quiz_defaults(
        {
            "quiz_title": {"uk": "Новий квіз", "en": "New quiz"},
            "quiz_subtitle": {"uk": "", "en": ""},
            "intro_text": {"uk": "", "en": ""},
            "final_message": {"uk": "", "en": ""},
            "questions": [],
            "results": fallback.get("results", []),
        },
        fallback,
    )
    safe_name = unique_quiz_filename(new_filename)
    (QUIZZES_DIR / safe_name).write_text(json.dumps(blank, ensure_ascii=False, indent=2), encoding="utf-8")
    set_active_quiz_file(safe_name)
    return safe_name


def duplicate_quiz(source_filename: str, new_filename: str) -> str:
    ensure_quiz_store()
    source = QUIZZES_DIR / sanitize_quiz_filename(source_filename)
    if not source.exists():
        raise FileNotFoundError(source.name)
    safe_name = unique_quiz_filename(new_filename)
    shutil.copyfile(source, QUIZZES_DIR / safe_name)
    return safe_name


PROTECTED_QUIZ_FILES = {"active_quiz.json", "default_quiz.json", "default_quiz.template.json"}


def delete_quiz_file(filename: str) -> None:
    ensure_quiz_store()
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("Quiz filename must not include a path.")
    if not filename.lower().endswith(".json"):
        raise ValueError("Only .json quiz files can be deleted.")
    if filename in PROTECTED_QUIZ_FILES:
        raise ValueError("This quiz file is protected and cannot be deleted.")

    files = list_quiz_files()
    if filename not in files:
        raise FileNotFoundError(filename)
    if len(files) <= 1:
        raise ValueError("Cannot delete the last quiz.")
    if filename == get_active_quiz_file():
        raise ValueError("Cannot delete the active quiz.")

    quizzes_root = QUIZZES_DIR.resolve()
    target = (QUIZZES_DIR / filename).resolve()
    try:
        target.relative_to(quizzes_root)
    except ValueError as exc:
        raise ValueError("Quiz file must be inside the quizzes directory.") from exc
    if target.suffix.lower() != ".json":
        raise ValueError("Only .json quiz files can be deleted.")
    if not target.is_file():
        raise FileNotFoundError(filename)
    target.unlink()


def delete_quiz(filename: str) -> None:
    ensure_quiz_store()
    safe_name = sanitize_quiz_filename(filename)
    files = list_quiz_files()
    if safe_name not in files:
        raise FileNotFoundError(safe_name)
    if len(files) <= 1:
        raise ValueError("At least one quiz must remain.")
    (QUIZZES_DIR / safe_name).unlink()
    if get_active_quiz_file() == safe_name:
        remaining = list_quiz_files()
        set_active_quiz_file(remaining[0])


def ensure_results_file(path: Path = RESULTS_PATH) -> None:
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
            writer.writeheader()


def append_result(
    participant_name: str,
    department: str,
    score: int,
    max_score: int,
    percentage: float,
    result_category: str,
    answers_summary: list[dict[str, Any]],
    path: Path = RESULTS_PATH,
) -> None:
    ensure_results_file(path)
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "participant_name": participant_name,
                "department": department,
                "score": score,
                "max_score": max_score,
                "percentage": percentage,
                "result_category": result_category,
                "answers_summary": json.dumps(answers_summary, ensure_ascii=False),
            }
        )


def read_results(path: Path = RESULTS_PATH) -> list[dict[str, str]]:
    ensure_results_file(path)
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def results_as_csv(path: Path = RESULTS_PATH) -> str:
    ensure_results_file(path)
    return path.read_text(encoding="utf-8")


def clear_results(path: Path = RESULTS_PATH) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
