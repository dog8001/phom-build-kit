from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_LIST_PATH = ROOT / "00_architecture" / "PHOM_Module_List_v1.json"
COMPARISON_RUNS_PATH = ROOT / "comparison_runs"
QUESTIONS_DIR = ROOT / "04_review_questions"
QUESTION_BANK_DIR = ROOT / "10_question_bank"
QUESTION_BANK_PATH = QUESTION_BANK_DIR / "question_bank.json"
ANSWERS_DIR = ROOT / "07_answers"
ANSWERS_JSONL_PATH = ANSWERS_DIR / "answers.jsonl"
USER_DATASET_DIR = ROOT / "11_user_dataset"
USER_DATASET_PATH = USER_DATASET_DIR / "user_dataset.md"
RUN_OVERRIDES_DIR = ROOT / "08_run_overrides"
EVIDENCE_FILE = ROOT / "01_input" / "Pierre_Evidence_Base.md"
MASTER_DIR = ROOT / "05_master"
