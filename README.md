# PHOM Build Kit v1

This kit builds Pierre Human Operating Model one module at a time.


## Install directly from your QI System folder

Recommended Mac path:

```bash
cd "/Users/pierrecarlsson/Documents/QI System"
```

Put the zip file there, then unzip manually or run:

```bash
unzip PHOM_Build_Kit_v3_seeded_installer.zip
cd PHOM_Build_Kit_v3_seeded_installer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
open .env
```

After adding your API key:

```bash
python3 scripts/build_module.py L0_01_life_timeline
```

You can also run:

```bash
bash start_phom_seeded.sh
```


## Setup

```bash
cd PHOM_Build_Kit_v1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API key in `.env`.

## Add input data

This v2 package already includes seeded context in:
- `01_input/Pierre_Known_Context_Seed_v1.md`

Optional extra input can be added to:
- `01_input/Pierre_Evidence_Base.md`
- `01_input/Existing_Profiles.md`
- `01_input/Text_Corpus.md`

## Build one module

```bash
python3 scripts/build_module.py L1_01_identity_architecture
```

Dry-run (no API call, useful for validating wiring/output paths):

```bash
python3 scripts/build_module.py L0_01_life_timeline --dry-run
```

## Local control panel (Streamlit)

```bash
streamlit run app.py
```

Safety note: API modes trigger model calls and can incur usage costs. Use `--dry-run` or the dashboard's dry-run mode when testing.

## Build all first-phase modules

```bash
python3 scripts/build_all.py --phase first
```

## Assemble master document

```bash
python3 scripts/assemble_master.py
```

Output:
- individual modules in `03_modules/`
- review questions in `04_review_questions/`
- master document in `05_master/PHOM_Master_v1.md`

## Recommended workflow

1. Use the included seed file as starting evidence.
2. Build one module.
3. Read questions generated for you.
4. Add only high-value clarifications to Evidence Base.
5. Rebuild only if needed.
6. Continue to the next module.

Do not try to perfect all modules at once.
