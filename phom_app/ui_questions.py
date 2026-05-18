from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from .questions import append_answer, append_custom_question, append_user_domain_module, load_json_list


def render_questions_page(root: Path, modules: list[dict]) -> None:
    question_bank_path = root / "10_question_bank" / "question_bank.json"
    user_domains_path = root / "10_question_bank" / "user_domains.json"
    answers_jsonl_path = root / "07_answers" / "answers.jsonl"

    st.header("Questions")
    base_pairs = [((m["id"].split("_")[0] if "_" in m["id"] else m["id"]), m["id"]) for m in modules]
    user_pairs = [(e.get("domain", ""), e.get("module_id", "")) for e in load_json_list(user_domains_path) if isinstance(e, dict)]
    all_pairs = sorted({(d.strip(), mid.strip()) for d, mid in (base_pairs + user_pairs) if d and mid})
    domains = sorted({d for d, _ in all_pairs})

    pending_domain = st.session_state.pop("q_pending_domain", None)
    pending_module = st.session_state.pop("q_pending_module", None)
    if pending_domain and pending_module:
        st.session_state["q_target_mode"] = "Existing domain/module"
        st.session_state["q_domain"] = pending_domain
        st.session_state["q_module"] = pending_module

    mode = st.radio("Choose target type", ["Existing domain/module", "Create new domain/module"], key="q_target_mode")

    selected_domain = ""
    selected_module = ""

    if mode == "Existing domain/module":
        selected_domain = st.selectbox("domain", domains, key="q_domain") if domains else ""
        domain_modules = sorted({mid for d, mid in all_pairs if d == selected_domain})
        selected_module = st.selectbox("module", domain_modules, key="q_module") if domain_modules else ""
    else:
        with st.form("create_domain_module_form", clear_on_submit=True):
            new_domain = st.text_input("new domain")
            new_module = st.text_input("new module/theme")
            create_target = st.form_submit_button("Create domain/module")
            if create_target:
                if not new_domain.strip() or not new_module.strip():
                    st.warning("Please provide both new domain and new module/theme.")
                else:
                    append_user_domain_module(user_domains_path, new_domain.strip(), new_module.strip())
                    st.session_state["q_pending_domain"] = new_domain.strip()
                    st.session_state["q_pending_module"] = new_module.strip()
                    st.success("Created domain/module target.")
                    st.rerun()

    if selected_domain and selected_module:
        with st.expander("Create custom question", expanded=True):
            with st.form("create_custom_question_form", clear_on_submit=True):
                custom_question_text = st.text_area("question", height=120)
                custom_why = st.text_input("why needed (optional)")
                custom_priority = st.selectbox("priority", ["low", "medium", "high"], index=1)
                if st.form_submit_button("Create custom question"):
                    if not custom_question_text.strip():
                        st.warning("Please provide a question.")
                    else:
                        append_custom_question(
                            question_bank_path,
                            selected_domain,
                            selected_module,
                            custom_question_text,
                            custom_why,
                            custom_priority,
                        )
                        st.success("Custom question saved.")
                        st.rerun()

    question_bank = load_json_list(question_bank_path)
    filtered = [q for q in question_bank if q.get("domain") == selected_domain and q.get("module_id") == selected_module]
    st.write(f"Loaded {len(filtered)} questions from `10_question_bank/question_bank.json`")

    for q in filtered:
        qid = q.get("question_id", "")
        st.markdown(f"**{qid}** — {q.get('question', '')}")
        key = f"ans_{qid}"
        answer_text = st.text_area("Answer", key=key, height=100)
        if st.button(f"Save answer: {qid}", key=f"save_{qid}"):
            append_answer(answers_jsonl_path, {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "type": "question_answer",
                "question_id": qid,
                "domain": selected_domain,
                "module_id": selected_module,
                "question": q.get("question", ""),
                "answer": answer_text.strip(),
            })
            st.success("Answer saved.")
            st.rerun()
