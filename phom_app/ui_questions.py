from datetime import datetime

import streamlit as st

from .paths import ANSWERS_JSONL_PATH, QUESTION_BANK_PATH, ROOT, USER_DATASET_PATH
from .questions import (
    append_answer,
    append_custom_question,
    append_user_dataset_entry,
    load_question_bank,
    load_saved_answers,
)


def render_questions_page(modules: list[dict], module_lookup: dict[str, dict]) -> None:
    st.header("Questions")
    module_ids = [m["id"] for m in modules]
    domains = sorted({(m["id"].split("_")[0] if "_" in m["id"] else m["id"]) for m in modules})
    if st.button("Refresh questions and saved answers"):
        st.rerun()
    question_bank = load_question_bank(modules, ROOT)
    selected_domain = st.selectbox("Select domain", domains, key="q_domain")
    domain_modules = [m for m in module_ids if (m.split("_")[0] if "_" in m else m) == selected_domain]
    selected_module = st.selectbox("Select module", domain_modules, key="q_module")

    with st.expander("Create custom question", expanded=False):
        with st.form("create_custom_question_form", clear_on_submit=True):
            custom_domain = st.text_input("domain", value=selected_domain)
            custom_module_id = st.text_input("module_id", value=selected_module)
            custom_question_text = st.text_area("custom question text", height=120)
            custom_why = st.text_input("why_needed / note (optional)")
            custom_priority = st.selectbox("priority", ["low", "medium", "high"], index=1)
            create_custom = st.form_submit_button("Create custom question")
            if create_custom:
                if not custom_domain.strip() or not custom_module_id.strip() or not custom_question_text.strip():
                    st.warning("Please fill domain, module_id, and custom question text.")
                else:
                    new_q = append_custom_question(question_bank, custom_domain.strip(), custom_module_id.strip(), custom_question_text, custom_why, custom_priority)
                    st.success(f"Custom question created and saved to {QUESTION_BANK_PATH.relative_to(ROOT)}: {new_q['question_id']}")
                    st.rerun()

    filtered = [q for q in question_bank if q.get("domain") == selected_domain and q.get("module_id") == selected_module]
    st.write(f"Loaded {len(filtered)} questions from `10_question_bank/question_bank.json`")
    for q in filtered:
        qid = q["question_id"]
        st.markdown(f"**{qid}** — {q['question']}")
        st.caption(f"why_needed: {q.get('why_needed', '')} | priority: {q.get('priority', '')} | status: {q.get('status', '')}")
        answer_text = st.text_area("Answer", key=f"ans_{qid}", height=100)
        if st.button(f"Save answer: {qid}", key=f"save_{qid}"):
            append_answer({"timestamp": datetime.now().isoformat(timespec="seconds"), "type": "question_answer", "question_id": qid, "domain": selected_domain, "module_id": selected_module, "question": q["question"], "answer": answer_text.strip()})
            st.success(f"Answer saved to {ANSWERS_JSONL_PATH.relative_to(ROOT)}")
            st.rerun()

    st.subheader("Add freeform dataset note")
    manual_text = st.text_area("Add freeform dataset note", key="manual_entry", height=140)
    if st.button("Save freeform note"):
        if manual_text.strip():
            append_user_dataset_entry(selected_domain, selected_module, manual_text)
            append_answer({"timestamp": datetime.now().isoformat(timespec="seconds"), "type": "manual_entry", "question_id": "manual", "domain": selected_domain, "module_id": selected_module, "question": "manual_entry", "answer": manual_text.strip()})
            st.success(f"Manual entry saved to {USER_DATASET_PATH.relative_to(ROOT)} and {ANSWERS_JSONL_PATH.relative_to(ROOT)}")
            st.rerun()
        else:
            st.warning("Please enter content before saving.")

    st.button("Synchronize & optimize dataset", disabled=True, help="Future step: AI maps answers and user data into existing modules or proposes new clusters.")
    st.subheader("Saved answers for selected module")
    saved_answers = load_saved_answers(selected_domain, selected_module)
    st.json(saved_answers) if saved_answers else st.info("No saved answers yet for this domain/module.")
