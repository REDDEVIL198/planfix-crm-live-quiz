from __future__ import annotations

import base64
import time
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from admin_editor import render_admin_editor
from live_storage import (
    answer_counts_for_question,
    build_leaderboard,
    count_answers_for_question,
    current_question,
    current_question_index,
    get_answer,
    get_participant,
    get_participants,
    get_state,
    leaderboard_as_csv,
    option_text,
    question_started_timestamp,
    register_participant,
    reset_live_session,
    save_answer,
    set_state,
)
from quiz_engine import localized
from storage import load_active_quiz_config, load_quiz_config


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTION_SECONDS = 10
MIN_QUESTION_SECONDS = 5
MAX_QUESTION_SECONDS = 120
TEXT = {
    "uk": {
        "language": "РњРѕРІР°",
        "mode": "Р РµР¶РёРј",
        "participant": "РЈС‡Р°СЃРЅРёРє",
        "host": "Host",
        "admin": "Admin",
        "results": "Р РµР·СѓР»СЊС‚Р°С‚Рё",
        "name": "Р†Рј'СЏ",
        "department": "Р’С–РґРґС–Р» / РєРѕРјР°РЅРґР°",
        "join": "РџСЂРёС”РґРЅР°С‚РёСЃСЏ",
        "name_required": "Р’РІРµРґС–С‚СЊ С–Рј'СЏ, С‰РѕР± РїСЂРёС”РґРЅР°С‚РёСЃСЏ.",
        "lobby": "Р›РѕР±С–",
        "waiting_lobby": "РћС‡С–РєСѓС”РјРѕ СЃС‚Р°СЂС‚Сѓ РєРІС–Р·Сѓ. РќРµ Р·Р°РєСЂРёРІР°Р№С‚Рµ СЃС‚РѕСЂС–РЅРєСѓ.",
        "waiting_question": "РћС‡С–РєСѓС”РјРѕ РЅР°СЃС‚СѓРїРЅРµ РїРёС‚Р°РЅРЅСЏ.",
        "question": "РџРёС‚Р°РЅРЅСЏ",
        "timer": "РўР°Р№РјРµСЂ",
        "seconds": "СЃРµРє",
        "submit": "РќР°РґС–СЃР»Р°С‚Рё РІС–РґРїРѕРІС–РґСЊ",
        "submitted": "Р’С–РґРїРѕРІС–РґСЊ РїСЂРёР№РЅСЏС‚Р°. РћС‡С–РєСѓС”РјРѕ РїСЂР°РІРёР»СЊРЅСѓ РІС–РґРїРѕРІС–РґСЊ.",
        "expired": "Р§Р°СЃ РІРёР№С€РѕРІ.",
        "expired_waiting": "Р§Р°СЃ РІРёР№С€РѕРІ. РћС‡С–РєСѓС”РјРѕ РїСЂР°РІРёР»СЊРЅСѓ РІС–РґРїРѕРІС–РґСЊ.",
        "time_expired_rejected": "Р§Р°СЃ РІРёР№С€РѕРІ. Р’С–РґРїРѕРІС–РґСЊ РЅРµ Р·Р°СЂР°С…РѕРІР°РЅРѕ.",
        "already_answered": "Р’Рё РІР¶Рµ РІС–РґРїРѕРІС–Р»Рё РЅР° С†Рµ РїРёС‚Р°РЅРЅСЏ.",
        "answer_error": "РќРµ РІРґР°Р»РѕСЃСЏ Р·Р±РµСЂРµРіС‚Рё РІС–РґРїРѕРІС–РґСЊ. РЎРїСЂРѕР±СѓР№С‚Рµ С‰Рµ СЂР°Р·, СЏРєС‰Рѕ С‡Р°СЃ С‰Рµ РЅРµ РІРёР№С€РѕРІ.",
        "select_answer": "РћР±РµСЂС–С‚СЊ РІС–РґРїРѕРІС–РґСЊ.",
        "correct_answer": "РџСЂР°РІРёР»СЊРЅР° РІС–РґРїРѕРІС–РґСЊ",
        "your_answer": "Р’Р°С€Р° РІС–РґРїРѕРІС–РґСЊ",
        "result": "Р РµР·СѓР»СЊС‚Р°С‚",
        "correct": "РџСЂР°РІРёР»СЊРЅРѕ",
        "incorrect": "РќРµРїСЂР°РІРёР»СЊРЅРѕ",
        "points": "Р‘Р°Р»Рё",
        "no_answer": "Р±РµР· РІС–РґРїРѕРІС–РґС–",
        "final": "Р¤С–РЅР°Р»СЊРЅС– СЂРµР·СѓР»СЊС‚Р°С‚Рё",
        "your_result": "Р’Р°С€ СЂРµР·СѓР»СЊС‚Р°С‚",
        "place": "РњС–СЃС†Рµ",
        "score": "Р‘Р°Р»Рё",
        "correct_answers": "РџСЂР°РІРёР»СЊРЅРёС… РІС–РґРїРѕРІС–РґРµР№",
        "percentage": "Р’С–РґСЃРѕС‚РѕРє",
        "top_10": "РўРѕРї 10",
        "participant_count": "РЈС‡Р°СЃРЅРёРєС–РІ",
        "answers_received": "Р’С–РґРїРѕРІС–РґРµР№ РѕС‚СЂРёРјР°РЅРѕ",
        "enter_pin": "Р’РІРµРґС–С‚СЊ PIN",
        "unlock": "РЈРІС–Р№С‚Рё",
        "bad_pin": "РќРµРїСЂР°РІРёР»СЊРЅРёР№ PIN.",
        "session_note": "Р”Р»СЏ С‚РµСЃС‚СѓРІР°РЅРЅСЏ СЏРє СѓС‡Р°СЃРЅРёРє РІС–РґРєСЂРёР№С‚Рµ РєРІС–Р· РІ С–РЅС€РѕРјСѓ Р±СЂР°СѓР·РµСЂС– Р°Р±Рѕ РІ СЂРµР¶РёРјС– С–РЅРєРѕРіРЅС–С‚Рѕ.",
        "change_participant": "Р’РёР№С‚Рё / Р·РјС–РЅРёС‚Рё СѓС‡Р°СЃРЅРёРєР°",
        "host_participant": "РўРµСЃС‚РѕРІРёР№ СѓС‡Р°СЃРЅРёРє / Host participant",
        "join_as_host": "РџСЂРёС”РґРЅР°С‚РёСЃСЏ СЏРє СѓС‡Р°СЃРЅРёРє",
        "answer_as_host": "Р’С–РґРїРѕРІС–СЃС‚Рё СЏРє",
        "host_panel": "Host-РїР°РЅРµР»СЊ",
        "start_quiz": "РџРѕС‡Р°С‚Рё РєРІС–Р·",
        "start_question": "Р—Р°РїСѓСЃС‚РёС‚Рё РїРёС‚Р°РЅРЅСЏ",
        "waiting_answers": "РћС‡С–РєСѓС”РјРѕ РІС–РґРїРѕРІС–РґС–...",
        "reveal": "РџРѕРєР°Р·Р°С‚Рё РїСЂР°РІРёР»СЊРЅСѓ РІС–РґРїРѕРІС–РґСЊ Р·Р°СЂР°Р·",
        "next_question": "РќР°СЃС‚СѓРїРЅРµ РїРёС‚Р°РЅРЅСЏ",
        "show_final": "РџРѕРєР°Р·Р°С‚Рё С„С–РЅР°Р»СЊРЅС– СЂРµР·СѓР»СЊС‚Р°С‚Рё",
        "new_live_session": "РќРѕРІР° live-СЃРµСЃС–СЏ",
        "reset_session": "РЎРєРёРЅСѓС‚Рё live-СЃРµСЃС–СЋ",
        "confirm_reset": "РЇ РїС–РґС‚РІРµСЂРґР¶СѓСЋ СЃРєРёРґР°РЅРЅСЏ live-СЃРµСЃС–С—",
        "download_live_csv": "Р—Р°РІР°РЅС‚Р°Р¶РёС‚Рё live CSV",
        "share_link": "РџРѕСЃРёР»Р°РЅРЅСЏ РґР»СЏ СѓС‡Р°СЃРЅРёРєС–РІ",
        "leaderboard_empty": "РџРѕРєРё РЅРµРјР°С” СѓС‡Р°СЃРЅРёРєС–РІ.",
        "admin_protected": "Admin Mode Р·Р°С…РёС‰РµРЅРѕ PIN.",
        "host_protected": "Host Mode Р·Р°С…РёС‰РµРЅРѕ PIN.",
    },
    "en": {
        "language": "Language",
        "mode": "Mode",
        "participant": "Participant",
        "host": "Host",
        "admin": "Admin",
        "results": "Results",
        "name": "Name",
        "department": "Department / team",
        "join": "Join",
        "name_required": "Enter your name to join.",
        "lobby": "Lobby",
        "waiting_lobby": "Waiting for the host to start the quiz. Keep this page open.",
        "waiting_question": "Waiting for the next question.",
        "question": "Question",
        "timer": "Timer",
        "seconds": "sec",
        "submit": "Submit answer",
        "submitted": "Answer submitted. Waiting for the correct answer.",
        "expired": "Time is up.",
        "expired_waiting": "Time is up. Waiting for the correct answer.",
        "time_expired_rejected": "Time is up. Your answer was not counted.",
        "already_answered": "You already answered this question.",
        "answer_error": "Could not save the answer. Try again if time is still active.",
        "select_answer": "Select an answer.",
        "correct_answer": "Correct answer",
        "your_answer": "Your answer",
        "result": "Result",
        "correct": "Correct",
        "incorrect": "Incorrect",
        "points": "Points",
        "no_answer": "no answer",
        "final": "Final results",
        "your_result": "Your result",
        "place": "Place",
        "score": "Score",
        "correct_answers": "Correct answers",
        "percentage": "Percentage",
        "top_10": "Top 10",
        "participant_count": "Participants",
        "answers_received": "Answers received",
        "enter_pin": "Enter PIN",
        "unlock": "Unlock",
        "bad_pin": "Wrong PIN.",
        "session_note": "To test as a participant, open the quiz in another browser or in incognito mode.",
        "change_participant": "Exit / change participant",
        "host_participant": "Test participant / Host participant",
        "join_as_host": "Join as participant",
        "answer_as_host": "Answer as",
        "host_panel": "Host panel",
        "start_quiz": "Start quiz",
        "start_question": "Start question",
        "waiting_answers": "Waiting for answers...",
        "reveal": "Reveal correct answer now",
        "next_question": "Next question",
        "show_final": "Show final results",
        "new_live_session": "New live session",
        "reset_session": "Reset live session",
        "confirm_reset": "I confirm live session reset",
        "download_live_csv": "Download live CSV",
        "share_link": "Participant link",
        "leaderboard_empty": "No participants yet.",
        "admin_protected": "Admin Mode is PIN-protected.",
        "host_protected": "Host Mode is PIN-protected.",
    },
}


def main() -> None:
    st.set_page_config(page_title="Planfix CRM Live Quiz", page_icon="вњ…", layout="wide")
    config = load_active_quiz_config()
    language = st.sidebar.selectbox(
        TEXT["uk"]["language"],
        ["uk", "en"],
        format_func=lambda item: "РЈРєСЂР°С—РЅСЃСЊРєР°" if item == "uk" else "English",
    )
    labels = TEXT[language]
    apply_branding(config.get("branding", {}))
    logo_path = config.get("branding", {}).get("logo_path")

    mode = st.sidebar.radio(
        labels["mode"],
        [labels["participant"], labels["host"], labels["admin"], labels["results"]],
        key="app_mode",
    )

    if mode == labels["host"]:
        st.sidebar.info(labels["session_note"])
        if require_pin(config, "host_pin", labels, "host"):
            render_host(config, language)
    elif mode == labels["admin"]:
        render_logo(logo_path)
        st.sidebar.info(labels["session_note"])
        if require_pin(config, "admin_pin", labels, "admin"):
            render_admin_editor(config, language)
    elif mode == labels["results"]:
        render_logo(logo_path)
        if require_pin(config, "admin_pin", labels, "results"):
            render_leaderboard(config, language, show_download=True)
    else:
        render_logo(logo_path)
        render_participant(config, language)


def apply_branding(branding: dict[str, str]) -> None:
    css_path = BASE_DIR / "styles" / "custom.css"
    custom_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    variables = f"""
    <style>
    :root {{
      --primary-color: {branding.get("primary_color", "#1F6FEB")};
      --secondary-color: {branding.get("secondary_color", "#F4F7FB")};
      --accent-color: {branding.get("accent_color", "#FFB000")};
      --background-color: {branding.get("background_color", "#FFFFFF")};
      --text-color: {branding.get("text_color", "#1F2937")};
      --font-family: {branding.get("font_family", "Inter, Arial, sans-serif")};
    }}
    {custom_css}
    </style>
    """
    st.markdown(variables, unsafe_allow_html=True)


def render_logo(logo_path: str | None) -> None:
    if not logo_path:
        return
    path = BASE_DIR / logo_path
    if path.exists():
        st.image(str(path), width=120)
    else:
        st.markdown('<div class="logo-placeholder">Planfix CRM</div>', unsafe_allow_html=True)


def auto_refresh(milliseconds: int = 2000) -> None:
    st_autorefresh(interval=milliseconds, key=f"autorefresh_{milliseconds}")


def get_security_pin(config: dict[str, Any], key: str) -> str:
    try:
        value = st.secrets.get("security", {}).get(key)
        if value:
            return str(value)
    except Exception:
        pass
    return str(config.get("security", {}).get(key, ""))


def require_pin(config: dict[str, Any], pin_key: str, labels: dict[str, str], session_key: str) -> bool:
    auth_key = f"{session_key}_authenticated"
    if st.session_state.get(auth_key):
        return True
    st.warning(labels["host_protected"] if pin_key == "host_pin" else labels["admin_protected"])
    with st.form(f"pin_form_{session_key}"):
        pin = st.text_input(labels["enter_pin"], type="password", key=f"pin_{session_key}")
        submitted = st.form_submit_button(labels["unlock"])
    if submitted:
        if pin and pin == get_security_pin(config, pin_key):
            st.session_state[auth_key] = True
            st.rerun()
        else:
            st.error(labels["bad_pin"])
    return False


def render_participant(config: dict[str, Any], language: str) -> None:
    labels = TEXT[language]
    quiz_title = localized(config.get("quiz_title"), language)
    st.title(quiz_title)
    st.caption(localized(config.get("quiz_subtitle"), language))

    participant = get_participant(st.session_state.get("participant_id"))
    if not participant:
        with st.form("join_form"):
            name = st.text_input(labels["name"] + " *")
            department = st.text_input(labels["department"])
            submitted = st.form_submit_button(labels["join"], type="primary")
        if submitted:
            if not name.strip():
                st.error(labels["name_required"])
            else:
                st.session_state["participant_id"] = register_participant(name, department)
                st.rerun()
        return

    state = get_state()
    state = sync_timer_phase(state)
    phase = state.get("phase", "lobby")
    st.success(f"{participant['name']} В· {participant.get('department', '')}".strip(" В·"))
    if st.button(labels["change_participant"], key="change_participant"):
        st.session_state.pop("participant_id", None)
        st.rerun()

    if phase == "lobby":
        st.header(labels["lobby"])
        st.info(labels["waiting_lobby"])
        auto_refresh()
    elif phase == "between_questions":
        st.header(labels["lobby"])
        st.info(labels["waiting_question"])
        auto_refresh()
    elif phase == "question":
        render_participant_question(config, language, participant["id"], state)
        auto_refresh(1000)
    elif phase == "reveal":
        render_participant_reveal(config, language, participant["id"], state)
        auto_refresh()
    elif phase == "final":
        render_participant_final(config, language, participant["id"])
        auto_refresh(5000)


def render_participant_question(config: dict[str, Any], language: str, participant_id: int, state: dict[str, str]) -> None:
    labels = TEXT[language]
    question = current_question(config, state)
    if not question:
        st.info(labels["waiting_question"])
        return

    index = current_question_index(state)
    remaining = remaining_seconds(state, config)
    timer_total = question_timer_seconds(config)
    percent = max(0, min(100, int(remaining / timer_total * 100)))
    existing = get_answer(participant_id, str(question.get("id")))
    title = escape(localized(config.get("quiz_title"), language))
    question_text = escape(localized(question.get("question"), language))
    total_questions = len(config.get("questions", []))
    low_timer_class = " participant-sticky-timer-low" if remaining <= 3 else ""
    st.markdown(
        f"""
        <section class="participant-live">
          <div class="participant-header">
            <div><span class="participant-kicker">LIVE QUIZ</span><h1>{title}</h1></div>
          </div>
          <section class="participant-sticky-timer{low_timer_class}" aria-label="{labels['timer']}">
            <div class="participant-sticky-meta">
              <span>{labels['question']} {index + 1} / {total_questions}</span>
              <strong>{remaining}<em>{labels['seconds']}</em></strong>
            </div>
            <div class="participant-sticky-track"><div style="width:{percent}%"></div></div>
          </section>
          <section class="participant-question-card"><h2>{question_text}</h2></section>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if existing:
        st.success(labels["submitted"])
        return
    if remaining <= 0:
        st.warning(labels["expired_waiting"])
        return

    option_ids = [str(option.get("id", "")) for option in question.get("options", [])]
    with st.form(f"participant_answer_form_{question.get('id')}"):
        st.markdown("<div class='participant-answer-radio-marker'></div>", unsafe_allow_html=True)
        selected_option = st.radio(
            labels["select_answer"],
            option_ids,
            index=None,
            format_func=lambda option_id: option_text(question, option_id, language),
            key=f"participant_selected_{question.get('id')}",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button(labels["submit"], type="primary", use_container_width=True)

    if submitted:
        if not selected_option:
            st.warning(labels["select_answer"])
            return
        result = save_answer(
            participant_id,
            str(question.get("id")),
            str(selected_option),
            state=state,
            current_question_id=str(question.get("id")),
            timer_expired=remaining_seconds(state, config) <= 0,
        )
        if result["saved"]:
            st.success(labels["submitted"])
        else:
            st.warning(answer_rejection_message(labels, result["reason"]))
        st.rerun()


def render_participant_reveal(config: dict[str, Any], language: str, participant_id: int, state: dict[str, str]) -> None:
    labels = TEXT[language]
    question = current_question(config, state)
    if not question:
        return
    answer = get_answer(participant_id, str(question.get("id")))
    selected = answer["selected_option_id"] if answer else labels["no_answer"]
    correct = str(question.get("correct_option_id"))
    is_correct = bool(answer and selected == correct)
    max_points = int(question.get("points", 0))
    points = max_points if is_correct else 0
    question_text = escape(localized(question.get("question"), language))
    selected_text = option_text(question, selected, language) if answer else labels["no_answer"]
    selected_badge = str(selected) if answer else "-"
    correct_text = option_text(question, correct, language)
    result_class = "participant-result-correct" if is_correct else "participant-result-wrong"
    result_text = labels["correct"] if is_correct else labels["incorrect"]
    st.markdown(
        f"""
        <section class="participant-question-card participant-reveal-question"><h2>{question_text}</h2></section>
        <section class="participant-reveal-grid">
          <article class="participant-result-card {result_class}">
            <span>{labels['your_answer']}</span>
            <strong>{escape(selected_badge)}</strong>
            <p>{escape(selected_text)}</p>
          </article>
          <article class="participant-result-card participant-result-correct">
            <span>{labels['correct_answer']}</span>
            <strong>{escape(correct)}</strong>
            <p>{escape(correct_text)}</p>
          </article>
        </section>
        <div class="participant-result-summary">{labels['result']}: <strong>{result_text}</strong> В· {labels['points']}: <strong>{points} / {max_points}</strong></div>
        """,
        unsafe_allow_html=True,
    )
    explanation = localized(question.get("explanation"), language)
    if explanation:
        st.write(explanation)


def render_participant_final(config: dict[str, Any], language: str, participant_id: int) -> None:
    labels = TEXT[language]
    rows = build_leaderboard(config, language)
    current = next((row for row in rows if int(row["participant_id"]) == int(participant_id)), None)
    st.header(labels["your_result"])
    if current:
        st.markdown(
            f"""
            <div class="score-block">
              {labels['name']}: {escape(str(current['name']))}<br>
              {labels['place']}: {current['place']}<br>
              {labels['score']}: {current['score']} / {current['max_score']}<br>
              {labels['correct_answers']}: {current['correct_answers']}<br>
              {labels['percentage']}: {current['percentage']}%
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info(labels["leaderboard_empty"])

    st.subheader(labels["top_10"])
    display_rows = leaderboard_rows(rows[:10])
    if display_rows:
        st.dataframe(display_rows, use_container_width=True, hide_index=True)


def answer_rejection_message(labels: dict[str, str], reason: str) -> str:
    messages = {
        "time_expired": labels["time_expired_rejected"],
        "already_answered": labels["already_answered"],
        "wrong_phase": labels["time_expired_rejected"],
        "wrong_question": labels["answer_error"],
        "database_busy": labels["answer_error"],
    }
    return messages.get(reason, labels["answer_error"])



def render_host(config: dict[str, Any], language: str) -> None:
    labels = TEXT[language]
    state = get_state()
    state = sync_timer_phase(state)
    phase = state.get("phase", "lobby")
    question = current_question(config, state)
    index = current_question_index(state)
    participants = get_participants()
    total_questions = len(config.get("questions", []))
    answers_received = count_answers_for_question(str(question.get("id"))) if question else 0

    render_host_header(config, language, labels, index, total_questions, len(participants), answers_received, phase)

    if phase == "final":
        render_leaderboard(config, language, show_download=True, presentation=True)
    elif phase == "lobby":
        render_host_lobby(labels, participants)
    elif question and phase in {"between_questions", "question", "reveal"}:
        render_host_question_stage(config, language, labels, state, question, index, phase, len(participants), answers_received)
    else:
        st.info(labels["waiting_question"])

    render_host_participant(config, language, labels, state, question)
    render_host_controls(config, labels, phase, index)

    if phase != "final":
        auto_refresh(2000)


def render_host_header(
    config: dict[str, Any],
    language: str,
    labels: dict[str, str],
    index: int,
    total_questions: int,
    participant_count: int,
    answers_received: int,
    phase: str,
) -> None:
    title = escape(localized(config.get("quiz_title"), language))
    logo_path = str(config.get("branding", {}).get("logo_path", ""))
    logo_html = ""
    logo_html = host_logo_html(logo_path)
    st.markdown(
        f"""
        <section class="host-screen"><section class="host-header">
          <div class="host-brand">{logo_html}<div><div class="host-kicker">LIVE QUIZ</div><h1>{title}</h1></div></div>
          <div class="host-stats">
            <div><span>{labels['question']}</span><strong>{index + 1}/{max(total_questions, 1)}</strong></div>
            <div><span>{labels['participant_count']}</span><strong>{participant_count}</strong></div>
            <div><span>{labels['answers_received']}</span><strong>{answers_received}</strong></div>
            <div><span>Phase</span><strong>{escape(phase)}</strong></div>
          </div>
        </section></section>
        """,
        unsafe_allow_html=True,
    )


def host_logo_html(logo_path: str) -> str:
    path = BASE_DIR / logo_path if logo_path else Path()
    if path.exists() and path.is_file():
        suffix = path.suffix.lower().lstrip(".") or "png"
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"<img class='host-logo' src='data:image/{mime};base64,{encoded}' alt='Planfix CRM' />"
    return "<div class='host-logo-fallback'>Planfix CRM</div>"


def render_host_lobby(labels: dict[str, str], participants: list[dict[str, Any]]) -> None:
    st.markdown(
        f"""
        <section class="host-question-card host-lobby-card">
          <div class="host-kicker">{labels['lobby']}</div>
          <h2>{labels['waiting_lobby']}</h2>
          <p>{labels['share_link']}: public Streamlit URL в†’ {labels['participant']}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if participants:
        chips = "".join(
            f"<div class='host-participant-chip'>{escape(str(item['name']))}<span>{escape(str(item.get('department', '')))}</span></div>"
            for item in participants[:30]
        )
        st.markdown(f"<div class='host-participant-grid'>{chips}</div>", unsafe_allow_html=True)
    else:
        st.info(labels["leaderboard_empty"])


def render_host_question_stage(
    config: dict[str, Any],
    language: str,
    labels: dict[str, str],
    state: dict[str, str],
    question: dict[str, Any],
    index: int,
    phase: str,
    participant_count: int,
    answers_received: int,
) -> None:
    if phase == "question":
        render_host_timer(labels, state)
    elif phase == "reveal":
        st.markdown(f"<div class='host-reveal-banner'>{labels['correct_answer']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='host-reveal-banner host-standby'>{labels['waiting_question']}</div>", unsafe_allow_html=True)

    question_text = escape(localized(question.get("question"), language))
    st.markdown(
        f"""
        <section class="host-question-card">
          <div class="host-kicker">{labels['question']} {index + 1}</div>
          <h2>{question_text}</h2>
        </section>
        """,
        unsafe_allow_html=True,
    )
    render_host_answer_cards(question, language, phase, participant_count, answers_received)


def render_host_timer(labels: dict[str, str], state: dict[str, str]) -> None:
    config = load_active_quiz_config()
    timer_total = question_timer_seconds(config)
    remaining = remaining_seconds(state, config)
    percent = max(0, min(100, int(remaining / timer_total * 100)))
    low_class = " host-timer-low" if remaining <= 3 else ""
    st.markdown(
        f"""
        <section class="host-timer{low_class}">
          <div>{labels['timer']}</div>
          <strong>{remaining}</strong>
          <span>{labels['seconds']}</span>
          <div class="host-timer-track"><div style="width:{percent}%"></div></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_host_answer_cards(
    question: dict[str, Any],
    language: str,
    phase: str,
    participant_count: int,
    answers_received: int,
) -> None:
    correct_id = str(question.get("correct_option_id", ""))
    counts = answer_counts_for_question(str(question.get("id"))) if phase == "reveal" else {}
    cards = []
    denominator = max(answers_received, 1)
    for option in question.get("options", []):
        option_id = str(option.get("id", ""))
        text = escape(localized(option.get("text"), language))
        count = counts.get(option_id, 0)
        pct = int(round(count / denominator * 100)) if phase == "reveal" else 0
        class_name = "host-answer-card"
        if phase == "reveal":
            class_name += " host-answer-card-correct correct" if option_id == correct_id else " host-answer-card-wrong wrong"
        result_html = ""
        if phase == "reveal":
            result_html = (
                f"<div class='host-answer-result answer-count'><strong>{count}</strong><span>{pct}%</span></div>"
                f"<div class='host-answer-bar'><div style='width:{pct}%'></div></div>"
            )
        cards.append(
            f"<article class='{class_name}'>"
            f"<div class='host-answer-label'>{escape(option_id)}</div>"
            f"<div class='host-answer-text'>{text}</div>"
            f"{result_html}"
            f"</article>"
        )
    option_count = len(question.get("options", []))
    grid_class = f"host-answer-grid options-{option_count}"
    st.markdown(f"<section class='{grid_class}'>{''.join(cards)}</section>", unsafe_allow_html=True)
    if phase == "reveal":
        explanation = localized(question.get("explanation"), language)
        if explanation:
            st.markdown(f"<div class='host-explanation'>{escape(explanation)}</div>", unsafe_allow_html=True)


def render_host_participant(
    config: dict[str, Any],
    language: str,
    labels: dict[str, str],
    state: dict[str, str],
    question: dict[str, Any] | None,
) -> None:
    with st.expander(labels["host_participant"], expanded=False):
        host_participant = get_participant(st.session_state.get("host_participant_id"))
        if not host_participant:
            with st.form("host_participant_join_form"):
                name = st.text_input(labels["name"], value="Host Test", key="host_participant_name")
                department = st.text_input(labels["department"], key="host_participant_department")
                submitted = st.form_submit_button(labels["join_as_host"])
            if submitted:
                if not name.strip():
                    st.warning(labels["name_required"])
                else:
                    st.session_state["host_participant_id"] = register_participant(name, department)
                    st.rerun()
            return

        st.caption(f"{host_participant['name']} В· {host_participant.get('department', '')}".strip(" В·"))
        phase = state.get("phase", "lobby")
        if phase == "question" and question:
            question_id = str(question.get("id"))
            existing = get_answer(int(host_participant["id"]), question_id)
            if existing:
                st.success(labels["submitted"])
                return
            remaining = remaining_seconds(state, config)
            if remaining <= 0:
                st.warning(labels["expired"])
                return
            with st.form("host_participant_answer_form"):
                selected = st.radio(
                    f"{labels['answer_as_host']} {host_participant['name']}",
                    [option.get("id") for option in question.get("options", [])],
                    index=None,
                    format_func=lambda option_id: f"{option_id}. {option_text(question, option_id, language)}",
                )
                submitted = st.form_submit_button(labels["submit"])
            if submitted:
                if not selected:
                    st.warning(labels["select_answer"])
                else:
                    result = save_answer(
                        int(host_participant["id"]),
                        question_id,
                        str(selected),
                        state=state,
                        current_question_id=question_id,
                        timer_expired=remaining_seconds(state, config) <= 0,
                    )
                    if result["saved"]:
                        st.success(labels["submitted"])
                    else:
                        st.warning(answer_rejection_message(labels, result["reason"]))
                    st.rerun()
        elif phase == "reveal" and question:
            render_participant_reveal(config, language, int(host_participant["id"]), state)
        elif phase == "final":
            render_participant_final(config, language, int(host_participant["id"]))
        else:
            st.info(labels["waiting_question"])


def render_host_controls(config: dict[str, Any], labels: dict[str, str], phase: str, index: int) -> None:
    st.markdown("<div class='host-control-panel'>", unsafe_allow_html=True)
    questions = config.get("questions", [])
    total_questions = len(questions)
    is_last_question = index >= total_questions - 1
    if phase == "lobby" and st.button(labels["start_quiz"], type="primary", key="host_primary_start_quiz"):
        set_state(phase="between_questions", current_question_index=0, question_started_at="", active_question_id="")
        st.rerun()
    elif phase == "between_questions" and st.button(labels["start_question"], type="primary", key="host_primary_start_question"):
        active_question_id = str(questions[index].get("id", "")) if 0 <= index < total_questions else ""
        set_state(phase="question", question_started_at=time.time(), active_question_id=active_question_id)
        st.rerun()
    elif phase == "question":
        st.info(labels["waiting_answers"])
        if st.button(labels["reveal"], key="host_backup_reveal"):
            set_state(phase="reveal")
            st.rerun()
    elif phase == "reveal" and is_last_question:
        if st.button(labels["show_final"], type="primary", key="host_primary_final"):
            set_state(phase="final")
            st.rerun()
    elif phase == "reveal":
        if st.button(labels["next_question"], type="primary", key="host_primary_next"):
            set_state(phase="between_questions", current_question_index=index + 1, question_started_at="", active_question_id="")
            st.rerun()
    elif phase == "final":
        if st.button(labels["new_live_session"], type="primary", key="host_new_live_session"):
            reset_live_session()
            st.rerun()
    confirm_reset = st.checkbox(labels["confirm_reset"], key="host_confirm_reset")
    if st.button(labels["reset_session"], disabled=not confirm_reset, key="host_reset_session"):
        reset_live_session()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_leaderboard(
    config: dict[str, Any], language: str, show_download: bool, presentation: bool = False
) -> None:
    labels = TEXT[language]
    rows = build_leaderboard(config, language)
    st.header(labels["final"])
    if not rows:
        st.info(labels["leaderboard_empty"])
        return
    st.metric(labels["participant_count"], len(rows))

    if presentation:
        top_cards = []
        medals = ["1", "2", "3"]
        for idx, row in enumerate(rows[:3]):
            top_cards.append(
                f"<article class='host-leaderboard-card rank-{idx + 1}'>"
                f"<div class='host-rank'>{medals[idx]}</div>"
                f"<h3>{escape(str(row['name']))}</h3>"
                f"<p>{escape(str(row.get('department', '')))}</p>"
                f"<strong>{row['score']} / {row['max_score']}</strong>"
                f"<span>{row['percentage']}%</span>"
                f"</article>"
            )
        st.markdown(f"<section class='host-leaderboard-top3'>{''.join(top_cards)}</section>", unsafe_allow_html=True)
        remaining = rows[3:]
        if remaining:
            st.markdown("<div class='host-ranked-list'>", unsafe_allow_html=True)
            for row in remaining:
                st.markdown(
                    f"<div><strong>{row['place']}. {escape(str(row['name']))}</strong><span>{row['score']}/{row['max_score']} В· {row['correct_answers']} В· {row['percentage']}%</span></div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        st.dataframe(leaderboard_rows(rows), use_container_width=True, hide_index=True)
    else:
        st.dataframe(leaderboard_rows(rows), use_container_width=True, hide_index=True)

    if show_download:
        st.download_button(
            labels["download_live_csv"],
            data=leaderboard_as_csv(config, language),
            file_name="live_quiz_results.csv",
            mime="text/csv",
        )


def leaderboard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "place": row["place"],
            "name": row["name"],
            "department": row["department"],
            "score": row["score"],
            "max_score": row["max_score"],
            "correct_answers": row["correct_answers"],
            "answered_questions": row["answered_questions"],
            "percentage": row["percentage"],
        }
        for row in rows
    ]


def sync_timer_phase(state: dict[str, str]) -> dict[str, str]:
    config = load_active_quiz_config()
    if state.get("phase") == "question" and remaining_seconds(state, config) <= 0:
        set_state(phase="reveal")
        state = dict(state)
        state["phase"] = "reveal"
    return state


def question_timer_seconds(config: dict[str, Any]) -> int:
    try:
        seconds = int(config.get("live_quiz", {}).get("question_timer_seconds", DEFAULT_QUESTION_SECONDS))
    except (TypeError, ValueError):
        seconds = DEFAULT_QUESTION_SECONDS
    if seconds < MIN_QUESTION_SECONDS or seconds > MAX_QUESTION_SECONDS:
        return DEFAULT_QUESTION_SECONDS
    return seconds


def remaining_seconds(state: dict[str, str], config: dict[str, Any] | None = None) -> int:
    total_seconds = question_timer_seconds(config or load_active_quiz_config())
    started = question_started_timestamp(state)
    if started is None:
        return total_seconds
    elapsed = int(time.time() - started)
    return max(0, total_seconds - elapsed)


if __name__ == "__main__":
    main()


