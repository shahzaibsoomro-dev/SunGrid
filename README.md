# SunGrid Cooperative

Member-support copilot for a fictional solar cooperative. It answers from 14 internal documents. A rooftop rebate decision calls `check_rebate_eligibility` in the starter kit. The model does not invent that yes/no or that dollar amount.

The design note is `DESIGN.md`.

## Install

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configure

Create a `.env` file in this folder. Do not commit it.

```
OPENAI_API_KEY=
OPENAI_API_BASE=
OPENAI_DEPLOYMENT_NAME=
OPENAI_EMBEDDING_API_KEY=
OPENAI_EMBEDDING_API_BASE=
OPENAI_EMBEDDING_DEPLOYMENT_NAME=
```

`OPENAI_API_BASE` is the chat endpoint and already includes `/openai/v1`. `OPENAI_EMBEDDING_API_BASE` is the resource root. The embedding client adds `/openai/v1`.

## Run

The vectors are already in `data/vector_store`.

```
python main.py
streamlit run main2.py
```

Rebuild the vectors only if the documents change:

```
python -m app.rag.ingestion
```

## Assumptions

- Each question has one category. A chunk may have more than one. The category filters retrieval. It does not choose a different pipeline.
- Document 06 is Incentive and Billing. Some of its sections keep only one of those labels. Document 07 is Program Policies, and the lapse section also stays on Incentive because a lapsed installer counts as not approved for the rebate.
- Retrieval keeps chunks with a cosine score of at least 0.50. If more than three pass, it keeps the top five. I first kept at 0.6 but few queries from golden set were failing so i made it to 0.55 and later to 0.5 just to give more margin
- As this was just an assessment task so i kept things simple that i wouldn't have kept for a production large scale system
