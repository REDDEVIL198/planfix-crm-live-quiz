from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import streamlit as st

from quiz_engine import localized, move_item, validate_config, validate_questions, validate_result_ranges
from live_storage import reset_live_session
from storage import (
    clear_results,
    create_blank_quiz,
    create_quiz_from_current,
    delete_quiz,
    duplicate_quiz,
    export_config,
    get_active_quiz_file,
    list_quiz_files,
    load_active_quiz_config,
    reset_quiz_config,
    results_as_csv,
    save_quiz_config,
    save_uploaded_quiz,
    set_active_quiz_file,
)


TEXT = {
    "uk": {
        "quizzes": "Квізи",
        "settings": "Налаштування",
        "questions": "Питання",
        "results": "Результати",
        "branding": "Брендинг",
        "data": "Дані",
        "save": "Зберегти зміни",
        "saved": "Зміни збережено.",
        "errors": "Виправте помилки перед збереженням.",
        "edit_hint": "Відкрийте потрібне питання, змініть текст, варіанти або бали і натисніть 'Зберегти зміни' внизу сторінки.",
        "active_quiz": "Активний квіз",
        "switch_quiz_warning": "Зміна активного квізу скине поточну live-сесію. Підтвердити?",
        "upload_quiz": "Імпорт готового quiz JSON",
        "download_active_quiz": "Завантажити активний квіз JSON",
        "create_from_current": "Створити новий з поточного",
        "create_blank": "Створити порожній квіз",
        "duplicate_quiz": "Дублювати квіз",
        "delete_quiz": "Видалити квіз",
        "quiz_filename": "Назва файлу квізу",
        "quiz_saved_active": "Квіз збережено і зроблено активним.",
        "quiz_switched": "Активний квіз змінено.",
        "quiz_deleted": "Квіз видалено.",
        "answer_duration": "Тривалість відповіді, секунд",
        "add_question": "Додати питання",
        "delete": "Видалити",
        "move_up": "Вгору",
        "move_down": "Вниз",
        "add_option": "Додати варіант",
        "add_result": "Додати категорію результату",
        "download_json": "Завантажити JSON",
        "upload_json": "Завантажити конфіг JSON",
        "download_results": "Завантажити CSV результатів",
        "clear_results": "Очистити результати",
        "reset_config": "Скинути квіз до шаблону",
        "confirm": "Я підтверджую дію",
        "invalid_json": "JSON має помилку або неправильну структуру.",
        "results_cleared": "Результати очищено.",
        "config_reset": "Квіз скинуто до шаблону.",
    },
    "en": {
        "quizzes": "Quizzes",
        "settings": "Settings",
        "questions": "Questions",
        "results": "Results",
        "branding": "Branding",
        "data": "Data",
        "save": "Save changes",
        "saved": "Changes saved.",
        "errors": "Fix validation errors before saving.",
        "edit_hint": "Open a question, edit text, options or points and click 'Save changes' at the bottom of the page.",
        "active_quiz": "Active quiz",
        "switch_quiz_warning": "Changing the active quiz resets the current live session. Confirm?",
        "upload_quiz": "Import ready quiz JSON",
        "download_active_quiz": "Download active quiz JSON",
        "create_from_current": "Create new from current",
        "create_blank": "Create blank quiz",
        "duplicate_quiz": "Duplicate quiz",
        "delete_quiz": "Delete quiz",
        "quiz_filename": "Quiz filename",
        "quiz_saved_active": "Quiz saved and made active.",
        "quiz_switched": "Active quiz changed.",
        "quiz_deleted": "Quiz deleted.",
        "answer_duration": "Answer duration, seconds",
        "add_question": "Add question",
        "delete": "Delete",
        "move_up": "Move up",
        "move_down": "Move down",
        "add_option": "Add option",
        "add_result": "Add result category",
        "download_json": "Download JSON",
        "upload_json": "Upload config JSON",
        "download_results": "Download results CSV",
        "clear_results": "Clear results",
        "reset_config": "Reset quiz to template",
        "confirm": "I confirm this action",
        "invalid_json": "JSON has an error or invalid structure.",
        "results_cleared": "Results cleared.",
        "config_reset": "Quiz reset to template.",
    },
}

ADMIN_CONFIG_KEY = "admin_working_config"
ADMIN_SOURCE_KEY = "admin_source_config_json"
ADMIN_ACTIVE_FILE_KEY = "admin_active_quiz_file"


def render_admin_editor(config: dict[str, Any], language: str) -> dict[str, Any]:
    labels = TEXT[language]
    active_file = get_active_quiz_file()
    source_config = export_config(config)
    if (
        ADMIN_CONFIG_KEY not in st.session_state
        or st.session_state.get(ADMIN_SOURCE_KEY) != source_config
        or st.session_state.get(ADMIN_ACTIVE_FILE_KEY) != active_file
    ):
        st.session_state[ADMIN_CONFIG_KEY] = deepcopy(config)
        st.session_state[ADMIN_SOURCE_KEY] = source_config
        st.session_state[ADMIN_ACTIVE_FILE_KEY] = active_file

    working_config = st.session_state[ADMIN_CONFIG_KEY]
    st.info(labels["edit_hint"])
    tabs = st.tabs([labels["quizzes"], labels["settings"], labels["questions"], labels["results"], labels["branding"], labels["data"]])

    with tabs[0]:
        replacement_config = _render_quiz_manager(working_config, language)
        if replacement_config is not None:
            st.session_state[ADMIN_CONFIG_KEY] = replacement_config
            st.session_state[ADMIN_SOURCE_KEY] = export_config(replacement_config)
            st.session_state[ADMIN_ACTIVE_FILE_KEY] = get_active_quiz_file()
            return replacement_config
    with tabs[1]:
        _render_settings(working_config, language)
    with tabs[2]:
        _render_questions(working_config, language)
    with tabs[3]:
        _render_results(working_config, language)
    with tabs[4]:
        _render_branding(working_config)
    with tabs[5]:
        uploaded_config = _render_data_tools(working_config, language)
        if uploaded_config is not None:
            return uploaded_config

    errors = validate_config(working_config)
    if errors:
        st.warning(labels["errors"])
        for error in errors:
            st.caption(error)

    if st.button(labels["save"], type="primary", disabled=bool(errors), key="save_admin_config"):
        save_quiz_config(working_config)
        st.session_state[ADMIN_SOURCE_KEY] = export_config(working_config)
        st.session_state[ADMIN_ACTIVE_FILE_KEY] = get_active_quiz_file()
        st.success(labels["saved"])
        st.rerun()

    return working_config



def _render_quiz_manager(config: dict[str, Any], language: str) -> dict[str, Any] | None:
    labels = TEXT[language]
    quiz_files = list_quiz_files()
    active_file = get_active_quiz_file()
    st.subheader(labels["active_quiz"])
    if quiz_files:
        selected = st.selectbox(
            labels["active_quiz"],
            quiz_files,
            index=quiz_files.index(active_file) if active_file in quiz_files else 0,
            key="active_quiz_select",
        )
        confirm_switch = st.checkbox(labels["switch_quiz_warning"], key="confirm_switch_quiz")
        if st.button(labels["active_quiz"], disabled=selected == active_file or not confirm_switch, key="switch_active_quiz"):
            set_active_quiz_file(selected)
            reset_live_session()
            st.success(labels["quiz_switched"])
            st.rerun()

    title = config.setdefault("quiz_title", {"uk": "", "en": ""})
    title[language] = st.text_input("Display name / quiz title", value=localized(title, language), key="quiz_manager_title")

    st.download_button(
        labels["download_active_quiz"],
        data=export_config(config),
        file_name=active_file,
        mime="application/json",
        key="download_active_quiz",
    )

    st.divider()
    new_name = st.text_input(labels["quiz_filename"], value="new_quiz.json", key="new_quiz_filename")
    col1, col2, col3 = st.columns(3)
    if col1.button(labels["create_from_current"], key="create_from_current"):
        create_quiz_from_current(new_name)
        reset_live_session()
        st.success(labels["quiz_saved_active"])
        st.rerun()
    if col2.button(labels["create_blank"], key="create_blank"):
        create_blank_quiz(new_name)
        reset_live_session()
        st.success(labels["quiz_saved_active"])
        st.rerun()
    if col3.button(labels["duplicate_quiz"], key="duplicate_quiz"):
        duplicate_quiz(active_file, new_name)
        st.success(labels["saved"])
        st.rerun()

    st.divider()
    uploaded = st.file_uploader(labels["upload_quiz"], type=["json"], key="upload_ready_quiz")
    upload_name = st.text_input(labels["quiz_filename"], value=uploaded.name if uploaded else "uploaded_quiz.json", key="upload_quiz_filename")
    if uploaded is not None and st.button(labels["upload_quiz"], key="save_uploaded_quiz"):
        try:
            filename = save_uploaded_quiz(uploaded.read(), upload_name)
            uploaded_config = load_active_quiz_config()
            from quiz_engine import validate_config
            errors = validate_config(uploaded_config)
            if not uploaded_config.get("questions") or not uploaded_config.get("results") or errors:
                delete_quiz(filename)
                st.error(labels["invalid_json"])
                for error in errors:
                    st.caption(error)
            else:
                reset_live_session()
                st.success(labels["quiz_saved_active"])
                st.rerun()
        except Exception as exc:
            st.error(f"{labels['invalid_json']} {exc}")

    st.divider()
    confirm_delete = st.checkbox(labels["confirm"], key="confirm_delete_quiz")
    if st.button(labels["delete_quiz"], disabled=not confirm_delete, key="delete_active_quiz"):
        try:
            delete_quiz(active_file)
            reset_live_session()
            st.success(labels["quiz_deleted"])
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    return None

def _localized_text_input(label: str, value: Any, language: str, key: str) -> dict[str, str]:
    current = deepcopy(value) if isinstance(value, dict) else {"uk": str(value or ""), "en": str(value or "")}
    current[language] = st.text_input(label, value=current.get(language, ""), key=key)
    current.setdefault("uk", current.get(language, ""))
    current.setdefault("en", current.get(language, ""))
    return current


def _localized_text_area(label: str, value: Any, language: str, key: str, height: int = 120) -> dict[str, str]:
    current = deepcopy(value) if isinstance(value, dict) else {"uk": str(value or ""), "en": str(value or "")}
    current[language] = st.text_area(label, value=current.get(language, ""), key=key, height=height)
    current.setdefault("uk", current.get(language, ""))
    current.setdefault("en", current.get(language, ""))
    return current


def _render_settings(config: dict[str, Any], language: str) -> None:
    config["quiz_title"] = _localized_text_input("Назва квізу / Quiz title", config.get("quiz_title"), language, "quiz_title")
    config["quiz_subtitle"] = _localized_text_area("Підзаголовок / Subtitle", config.get("quiz_subtitle"), language, "quiz_subtitle")
    config["intro_text"] = _localized_text_area("Вступний текст / Intro text", config.get("intro_text"), language, "intro_text")
    config["final_message"] = _localized_text_area("Фінальне повідомлення / Final message", config.get("final_message"), language, "final_message")
    live_quiz = config.setdefault("live_quiz", {})
    try:
        current_timer = int(live_quiz.get("question_timer_seconds", 10))
    except (TypeError, ValueError):
        current_timer = 10
    if current_timer < 5 or current_timer > 120:
        current_timer = 10
    st.markdown("<div class='admin-live-settings'>", unsafe_allow_html=True)
    st.subheader("Live quiz")
    live_quiz["question_timer_seconds"] = int(
        st.number_input(
            TEXT[language]["answer_duration"],
            min_value=5,
            max_value=120,
            step=1,
            value=current_timer,
            key="live_question_timer_seconds",
        )
    )
    st.markdown("</div>", unsafe_allow_html=True)
    live_quiz["auto_reveal"] = bool(live_quiz.get("auto_reveal", True))
    labels = config.setdefault("labels", {})
    for label_key in ["start_button", "next_button", "restart_button"]:
        labels[label_key] = _localized_text_input(label_key, labels.get(label_key), language, f"label_{label_key}")
    config["show_answer_review"] = st.checkbox(
        "Показувати перегляд відповідей / Show answer review",
        value=bool(config.get("show_answer_review", True)),
        key="show_answer_review",
    )


def _render_questions(config: dict[str, Any], language: str) -> None:
    questions = config.setdefault("questions", [])
    if st.button(TEXT[language]["add_question"], key="add_question"):
        next_number = len(questions) + 1
        questions.append(
            {
                "id": f"q{next_number}",
                "question": {"uk": "Нове питання", "en": "New question"},
                "options": [
                    {"id": "A", "text": {"uk": "Варіант A", "en": "Option A"}},
                    {"id": "B", "text": {"uk": "Варіант B", "en": "Option B"}},
                ],
                "correct_option_id": "A",
                "points": 1,
                "explanation": {"uk": "", "en": ""},
            }
        )
        st.rerun()

    for index, question in enumerate(list(questions)):
        title = localized(question.get("question"), language) or question.get("id", f"q{index + 1}")
        with st.expander(f"{index + 1}. {title}", expanded=False):
            question["id"] = st.text_input("ID", value=str(question.get("id", "")), key=f"q_id_{index}")
            question["question"] = _localized_text_area(
                "Текст питання / Question text", question.get("question"), language, f"q_text_{index}", height=90
            )
            question["points"] = int(
                st.number_input(
                    "Бали / Points", min_value=1, step=1, value=int(question.get("points", 1)), key=f"q_points_{index}"
                )
            )
            options = question.setdefault("options", [])
            option_ids = [str(option.get("id", "")) for option in options]
            selected_index = option_ids.index(question.get("correct_option_id")) if question.get("correct_option_id") in option_ids else 0
            question["correct_option_id"] = st.selectbox(
                "Правильна відповідь / Correct answer",
                options=option_ids,
                index=selected_index if option_ids else None,
                key=f"q_correct_{index}",
            )
            question["explanation"] = _localized_text_area(
                "Пояснення / Explanation", question.get("explanation"), language, f"q_expl_{index}", height=80
            )

            st.markdown("**Варіанти відповідей / Answer options**")
            for option_index, option in enumerate(list(options)):
                columns = st.columns([1, 5, 1])
                option["id"] = columns[0].text_input("ID", value=str(option.get("id", "")), key=f"opt_id_{index}_{option_index}")
                option["text"] = _localized_text_input(
                    "Текст варіанта / Option text", option.get("text"), language, f"opt_text_{index}_{option_index}"
                )
                if columns[2].button(TEXT[language]["delete"], key=f"del_opt_{index}_{option_index}"):
                    options.pop(option_index)
                    st.rerun()

            if st.button(TEXT[language]["add_option"], key=f"add_opt_{index}"):
                next_id = chr(ord("A") + len(options))
                options.append({"id": next_id, "text": {"uk": "Новий варіант", "en": "New option"}})
                st.rerun()

            controls = st.columns(3)
            if controls[0].button(TEXT[language]["move_up"], key=f"up_{index}", disabled=index == 0):
                config["questions"] = move_item(questions, index, -1)
                st.rerun()
            if controls[1].button(TEXT[language]["move_down"], key=f"down_{index}", disabled=index == len(questions) - 1):
                config["questions"] = move_item(questions, index, 1)
                st.rerun()
            if controls[2].button(TEXT[language]["delete"], key=f"del_q_{index}"):
                questions.pop(index)
                st.rerun()

    errors = validate_questions(questions)
    for error in errors:
        st.caption(error)


def _render_results(config: dict[str, Any], language: str) -> None:
    results = config.setdefault("results", [])
    if st.button(TEXT[language]["add_result"], key="add_result"):
        results.append(
            {
                "id": f"result_{len(results) + 1}",
                "title": {"uk": "Новий результат", "en": "New result"},
                "min_percentage": 0,
                "max_percentage": 100,
                "description": {"uk": "", "en": ""},
            }
        )
        st.rerun()
    for index, result in enumerate(list(results)):
        with st.expander(localized(result.get("title"), language) or f"Result {index + 1}"):
            result["id"] = st.text_input("ID", value=str(result.get("id", "")), key=f"res_id_{index}")
            result["title"] = _localized_text_input("Назва / Title", result.get("title"), language, f"res_title_{index}")
            result["min_percentage"] = int(st.number_input("Min %", min_value=0, max_value=100, value=int(result.get("min_percentage", 0)), key=f"res_min_{index}"))
            result["max_percentage"] = int(st.number_input("Max %", min_value=0, max_value=100, value=int(result.get("max_percentage", 100)), key=f"res_max_{index}"))
            result["description"] = _localized_text_area("Опис / Description", result.get("description"), language, f"res_desc_{index}", height=100)
            if st.button(TEXT[language]["delete"], key=f"del_res_{index}"):
                results.pop(index)
                st.rerun()
    for error in validate_result_ranges(results):
        st.caption(error)


def _render_branding(config: dict[str, Any]) -> None:
    branding = config.setdefault("branding", {})
    branding["logo_path"] = st.text_input("Logo path", value=branding.get("logo_path", "assets/logo.png"), key="brand_logo_path")
    branding["primary_color"] = st.color_picker("Primary color", value=branding.get("primary_color", "#1F6FEB"), key="brand_primary")
    branding["secondary_color"] = st.color_picker("Secondary color", value=branding.get("secondary_color", "#F4F7FB"), key="brand_secondary")
    branding["accent_color"] = st.color_picker("Accent color", value=branding.get("accent_color", "#FFB000"), key="brand_accent")
    branding["background_color"] = st.color_picker("Background color", value=branding.get("background_color", "#FFFFFF"), key="brand_background")
    branding["text_color"] = st.color_picker("Text color", value=branding.get("text_color", "#1F2937"), key="brand_text")
    branding["font_family"] = st.text_input("Font family", value=branding.get("font_family", "Inter, Arial, sans-serif"), key="brand_font")
    st.markdown(
        """
        <div class="preview-card">
          <strong>Preview</strong>
          <p>Planfix CRM Quiz</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_data_tools(config: dict[str, Any], language: str) -> dict[str, Any] | None:
    labels = TEXT[language]
    st.download_button(labels["download_json"], data=export_config(config), file_name="planfix_crm_quiz_config.json", mime="application/json")
    uploaded = st.file_uploader(labels["upload_json"], type=["json"])
    if uploaded is not None:
        try:
            uploaded_config = json.loads(uploaded.read().decode("utf-8"))
            errors = validate_config(uploaded_config)
            if errors:
                st.error(labels["invalid_json"])
                for error in errors:
                    st.caption(error)
            else:
                save_quiz_config(uploaded_config)
                st.session_state[ADMIN_CONFIG_KEY] = uploaded_config
                st.session_state[ADMIN_SOURCE_KEY] = export_config(uploaded_config)
                st.success(labels["saved"])
                st.rerun()
                return uploaded_config
        except (UnicodeDecodeError, json.JSONDecodeError):
            st.error(labels["invalid_json"])

    st.download_button(labels["download_results"], data=results_as_csv(), file_name="planfix_crm_quiz_results.csv", mime="text/csv")
    confirm_clear = st.checkbox(labels["confirm"], key="confirm_clear_results")
    if st.button(labels["clear_results"], disabled=not confirm_clear):
        clear_results()
        st.success(labels["results_cleared"])
    confirm_reset = st.checkbox(labels["confirm"], key="confirm_reset_config")
    if st.button(labels["reset_config"], disabled=not confirm_reset):
        reset_config = reset_quiz_config()
        st.session_state[ADMIN_CONFIG_KEY] = reset_config
        st.session_state[ADMIN_SOURCE_KEY] = export_config(reset_config)
        st.success(labels["config_reset"])
        st.rerun()
    return None
