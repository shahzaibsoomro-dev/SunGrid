# SunGrid Copilot — discussion prep

Read this before the follow-up conversation. It is a study note for you, not a design doc to submit.

Status: the task is understood. The solution is not built yet. Section 8 is the plan we should agree on before coding. Section 9 is what actually exists in this folder today.

---

## 1. Who they are, and why this task looks like this

Ahya (ahya.ai) builds AI software for companies trying to reach net zero. Main products:

- **AhyaOS** — carbon accounting. Measure, analyze, reduce, and report greenhouse-gas emissions (Scope 1, 2, and 3), aligned with the GHG Protocol and PCAF.
- **AhyaAI** — the intelligence layer on top of that: data capture, emission-factor search, a copilot, anomaly detection, forecasting, reduction planning.
- **Tawazun** — a marketplace to buy, sell, trade, and retire verified carbon offsets.

The job is applied AI engineering: retrieval over messy internal documents, plus agents that call real services (eligibility, emission factors, registries) instead of guessing.

This assessment is a small version of that job. SunGrid is fictional. The pattern is not: answer from documents when the documents are enough, and call a downstream service when a number or a yes/no must come from a system of record.

---

## 2. What we are solving

SunGrid Cooperative is a made-up solar co-op. Members ask a support team about policies, rebates, bills, installation, and company news. The team answers from a 14-document internal knowledge base.

They want a prototype copilot that:

1. Answers normal member questions from those documents, with the right document behind the answer.
2. For rooftop-rebate eligibility, does **not** do the math itself. It calls their eligibility service and treats a failed check as final.

The hard part is not “chat with a PDF.” The hard part is:

- Documents point at each other, and one of them belongs to two topics at once.
- Some facts are policy (answer from text). Some facts are a live decision (answer from the tool).
- A wrong category filter, or a model that “helpfully” estimates a rebate after a failed check, is a wrong system even if the sentence sounds fluent.

---

## 3. What the task actually requires

Time box they set: about 4–5 days, roughly 10–14 hours. Python is required. If something does not fit the time box, say so in the design doc. Do not skip it quietly.

You bring your own model API (OpenAI, Anthropic, Cohere, Google, or an open model). Keys stay in environment variables.

If the brief is ambiguous, pick a reasonable assumption, write it down, and continue.

### Part A — Ingestion, classification, retrieval

- Chunk the 14 documents, embed them, store them in a vector index you choose.
- Classify **each user question** into one primary category:
  - Program Policies
  - Incentive & Rebate Programs
  - Billing & Account
  - Technical / Installation Guidance
  - Company Updates
  - `non_relevant`
- Use that category as a **filter on retrieval**.
- Do not use it as a router that swaps out the whole pipeline (“if billing, run pipeline B”).

One document (the rebate refund / billing adjustment notice) does not fit one category. They want your reasoning written down. There is no secret correct label.

### Part B — Agent and tool use

- A small agent with **at least two steps**.
- If the question is about rooftop rebate eligibility, call `check_rebate_eligibility`. Do not answer that yes/no or that dollar amount from retrieved text.
- If the question is general knowledge, retrieve and write the answer as in Part A.
- The tool call is its own step. It is not buried inside the retriever.
- **Hard gate:** if any eligibility check fails, the answer must not offer a partial rebate, a hypothetical amount, or an estimate that ignores the failure.
- `stub_tools.py` is someone else’s service. Call it. Do not reimplement it and do not change its signature or return shape.

### Part C — Design note (1–2 pages, no code)

Answer these four questions:

1. How would you evaluate this before shipping (offline tests and/or live monitoring)?
2. What breaks first at 10× documents or 100× queries, and what would you change?
3. If they add a new document category next month, what changes and what stays?
4. One non-obvious trade-off you made, and why.

### What you submit

- Public GitHub repo, clean layout, `requirements.txt`, no API keys.
- README: install, configure, run end to end, plus assumptions.
- Design doc in the repo (Markdown or PDF).
- Then a short demo and Q&A. It is a conversation, not a slide deck. They will ask why you chose things, and they will poke edge cases.

---

## 4. The knowledge base

Five categories are named in the brief. The 14 files are not pre-labeled. This mapping is our working assumption.

| File | Working category | What a member would ask |
|---|---|---|
| `01_program_policies.md` | Program Policies | Tiers, grievances, privacy, tier changes, meetings |
| `02_incentive_rebate_programs.md` | Incentive & Rebate | Rooftop rebate rules, commercial incentive, appeals, funding, paperwork |
| `03_billing_faqs.md` | Billing & Account | Fees, due dates, late payment, true-up overview, billing disputes |
| `04_technical_installation_guidance.md` | Technical / Installation | Shading, inverters, interconnection, fault codes, roof life |
| `05_company_updates.md` | Company Updates | Newsletter, new tier rumor, second community array |
| `06_ambiguous_rebate_billing_adjustments.md` | **Both** Incentive and Billing | Rebate taken back after it was already paid |
| `07_installer_certification.md` | Program Policies (installer rules) | License, annual renewal, lapse |
| `08_governance_voting.md` | Program Policies | Votes, board elections, proxy, quorum |
| `09_battery_storage_incentive.md` | Incentive & Rebate | Extra battery rebate, and the rooftop-rebate dependency |
| `10_low_income_bill_credit.md` | Incentive & Rebate | $25/month credit, separate from the rooftop rebate |
| `11_net_metering_trueup.md` | Billing & Account | March true-up math, prorating |
| `12_autopay_failure_policy.md` | Billing & Account | Failed card, retries, late-payment clock |
| `13_battery_storage_installation.md` | Technical / Installation | Coupling, fire clearance, sizing, commissioning |
| `14_annual_impact_report.md` | Company Updates | Member counts, megawatts, emissions, rebate uptake |

`07` could also be argued as Technical. Prefer Program Policies because it governs who is allowed to install, which decides rebate eligibility. Technical docs describe how equipment is installed.

`14` is a year-end report, not a policy. Company Updates is the least-wrong bucket. Do not treat its statistics as program rules.

### Document 06 is the classification question

A rebate was approved and paid, then later found invalid (bad installer, or income over the line). SunGrid claws the money back over up to 6 monthly bills.

- The Incentive Program committee decides the reversal.
- The Billing team spreads it across bills.
- The member appeals through the **rebate appeals** process, not the general grievance process.
- Written notice at least 30 days before the first adjusted bill.
- Autopay: the adjustment is taken automatically.
- Manual pay: the member must acknowledge the new amount in the portal before the next cycle.

The file itself says it does not belong only to Incentive or only to Billing.

**Assumption to defend:** a question has one category; a chunk may have more than one. Index document 06 under both Incentive and Billing, so a filter for either category can still find it. The query classifier stays single-label, which is what Part A asks for. Write this in the design doc. They said they want the reasoning, not a magic label.

### Facts that are easy to mix up

These are the ones a reviewer will ask about. If you only remember one section, remember this one.

**Two different “income” programs**

- Rooftop rebate: income must be under the annual threshold. The policy text does not give the dollar number. The stub uses **$120,000**. At or above that, not eligible.
- Low-income bill credit: income under **200% of a different** low-income threshold. The dollar threshold is not in the kit. Credit is a flat **$25/month**, all tiers, no solar required. Missed recertification **pauses** the credit. Missed months are not paid back.

Do not treat $120,000 as the low-income line. Do not invent the low-income dollar amount.

**Two different battery topics**

- Incentive (`09`): $0.15 per watt-hour of usable storage, cap **$1,500**. Does not count toward the $4,000 rooftop cap. Only if the rooftop rebate was already approved. Not for a battery with no solar.
- Installation (`13`): micro-inverters need an AC-coupled battery; string inverters can be AC- or DC-coupled. 3-foot clearance. Size suggestion is 50–100% of average daily use. Above 150% is allowed, but there is no extra incentive past the $1,500 cap. “No extra incentive” does not mean the battery rebate is refused.

**Appeals vs grievances**

- Grievance (service, billing, installer conduct): board reviews within 15 business days. Does **not** cover rebate eligibility.
- Billing dispute that is not about a rebate: file within 60 days of the charge.
- Rebate eligibility appeal: within 30 days, Incentive Program committee.
- A reversed rebate is appealed the same way, not as a grievance.

**Installer: three different ways to lose approval**

- Never certified, or certification lapsed: jobs during the lapse count as non-approved, even if they used to be certified.
- Two or more safety violations in 12 months: removed, even if the certificate is current. Renewal and the violation process are separate.
- Non-approved installer means **no rooftop rebate**, no matter how good the other facts are. If the rebate was already paid, document 06 is the clawback.

**True-up**

- Once a year, cycle ending in March, for Household and Community.
- Extra generation becomes a bill credit at the tier’s net-metering rate.
- Net usage is billed at the **standard** rate, which is not the net-metering rate.
- The standard rate is **not written down**. Do not invent one.
- Household net-metering figure in the FAQ is **$0.07/kWh credit**. Community is **$0.09/kWh** (the table does not call it a credit). Commercial is negotiated.
- Mid-year enrollment is prorated.
- The result lands on the next normal bill, not a separate payment.
- Statement within 10 business days of the March cycle close.

**Autopay vs late payment**

- Bills on the 1st, due in 21 days. Autopay charges on the 15th.
- Failed autopay: two more tries over the next 5 business days, then that cycle is manual-pay.
- The 45-day review and 90-day disconnection clocks start from the **original due date**, not from the failed charge.
- Community members are not cut off from the shared array over a billing dispute. Disconnection is for non-payment past 90 days.
- Document 06 points at “the autopay-failure process in the Billing FAQs.” That process is **not** in the FAQ. It is in `12_autopay_failure_policy.md`. The corpus has a bad cross-reference. Say that out loud in the demo. It is the “imperfect documents” point of the exercise.

**Company news is not policy**

- A fourth tier for multi-family housing is planned and **not finalized**. Do not answer eligibility from the newsletter.
- Q2 newsletter: 4,200 household installations, community array full.
- Year-end report: just over 5,000 members (was about 3,600), 38 MW, about 21,000 tonnes CO2e, about 60% of eligible household installs got a rebate.
- Those numbers describe different things (installations vs members, mid-year vs year-end). Do not “correct” one with the other.

**Voting nuance**

- Policies say voting weight varies by tier.
- Governance says Household, Commercial, and Community each get one vote per account.
- Board seats are elected by household-tier members. Candidates need 12 months in good standing.
- “Good standing” is not defined. Do not invent a definition. Say the documents do not define it.

**Technical answers that should stay soft**

- More than 20% annual shading: generally not recommended, not a ban. Micro-inverters may be offered.
- Roof with under 10 years of life left: generally not approved unless there is a signed waiver. Removing panels later for a new roof is not covered.
- Do not energize until the utility approves interconnection (often 10–20 business days).
- Fault codes go to the installer. SunGrid does not diagnose hardware. Output far below the seasonal estimate for **two months in a row** (more than 20% low) goes through the monitoring dashboard, not the same path as a single fault code.
- E01 grid voltage, E07 ground fault (stop and call installer), E12 communications (often a gateway reset).

**Paperwork and money timing that is not eligibility**

- Rooftop application needs proof of installer approval, the utility interconnection application, and a signed income attestation.
- Incomplete applications sit for 15 business days, then close. The member must reapply.
- If the annual rebate budget is used up, new applications **waitlist**. That is not the same as “not eligible.”
- Commercial incentive is a different product: systems above 25 kW, paid quarterly on metered output, Carbon Markets desk. The stub does not apply to it.

---

## 5. The eligibility tool

Function: `check_rebate_eligibility` in `stub_tools.py`.

Inputs:

- `household_zip` (string)
- `annual_income_usd` (number)
- `system_size_kw` (number)
- `installer_approved` (true/false)

Output:

- `eligible` (true/false)
- `reason` (string)
- `estimated_rebate_usd` (number)

Checks, in this order. First failure wins. Later checks are not reported.

1. Installer must be approved. Else rebate $0.
2. ZIP must be one of `94101`, `94102`, `94103`, `94104`, `94105`. Else $0.
3. Income must be **below** $120,000. $120,000 exactly fails. Else $0.
4. System size must be from **3.0 to 10.0 kW inclusive**. Else $0.
5. If all pass: `min(system_size_kw * 1000 * 0.40, 4000)`, rounded to cents.

Examples you should be able to do in your head:

| Case | Result |
|---|---|
| Approved installer, 94103, income $80,000, 5 kW | Eligible, **$2,000** |
| Same, but 10 kW | Eligible, **$4,000** (the cap, not $4,000+) |
| Same, but 8 kW and income $120,000 | Not eligible, income reason, **$0** |
| Same, but installer not approved | Not eligible, installer reason, **$0**. Do not mention a dollar figure they “would have” received. |
| 2.9 kW or 10.1 kW | Not eligible, size reason |
| ZIP 94110 | Not eligible, outside the region |
| Commercial 30 kW question | **Do not call this tool.** It will fail the 3–10 kW check and sound like a rooftop denial. Commercial is a different program. |

The ZIP list and the $120,000 line are **not** in the policy markdown. The policy says “see the ZIP appendix” and “threshold published annually.” Assumption: for this prototype, the stub is the system of record for those two values. The model must not pretend it read them in a policy document.

### When to call the tool

Call it only for a **specific rooftop-rebate eligibility** question where all four inputs are known.

Do not call it for:

- “What is the rebate rate?” (policy: $0.40/watt, cap $4,000)
- “How do I appeal?”
- Battery incentive math
- Low-income $25 credit
- Commercial incentive
- A question that is missing zip, income, size, or installer status

If inputs are missing, ask for them. Do not fill them in. A made-up ZIP that happens to pass is a serious failure in the demo.

### What the hard gate means in the answer

Bad answer after a failed income check: “You’re over the income limit, but an 8 kW system would have been about $3,200.”

Good answer: “Not eligible. The service rejected it because household income is over the threshold. Estimated rebate is $0.” You may still explain, briefly, that the program uses hard checks and that failing one ends the calculation. You may not invent the other checks’ outcomes or a counterfactual amount.

The dollar amount on a success must be the tool’s `estimated_rebate_usd`, not a fresh calculation the model does beside it.

---

## 6. Edge cases worth rehearsing

**Retrieval and categories**

- Question touches two categories (“they reversed my rebate, what happens on my bill and can I appeal?”). Query still gets one primary label. Chunks of document 06 carry both labels, so the filter does not hide the answer. Say which label you would pick and why (user outcome: the bill vs the appeal).
- `non_relevant` (“what’s the weather”, “write a poem”, another company). Do not retrieve the nearest solar chunk and force an answer. Say it is outside SunGrid member support.
- “Is the multi-family tier open?” It is in Company Updates, and the answer is “not decided, do not use this as eligibility guidance.”
- A short follow-up (“what about commercial?”) needs the previous turn. The brief does not require a full chat product, but the demo may be multi-turn. Decide whether we keep a short history.

**Tool vs documents**

- User gives three of four facts. Ask for the fourth. No tool call yet.
- User gives all four, and two checks would fail. The tool reports only the first. Explain that reason. Do not guess the second failure unless you are describing the general rule, clearly separate from this decision.
- User asks a hypothetical with no personal facts (“if income is too high, do I get a smaller rebate?”). That is a policy question: no, hard fail, amount is not reduced. Tool optional. Do not invent an example household and run it unless they gave numbers.
- Budget exhausted vs not eligible. Waitlist is not a failed hard check.
- Battery add-on asked in the same breath as rooftop eligibility. Rooftop tool first. Battery incentive is only discussed as available if the tool says the rooftop rebate passed, and even then the battery dollar amount comes from document 09, not from this tool.

**Numbers the model will want to invent**

- Standard (non-net-metered) true-up rate
- Low-income threshold in dollars
- Fourth-tier rebate rules
- Definition of “good standing”
- Commercial contract rate
- A ZIP outside the five in the stub

The correct behavior is: the documents do not say, so the copilot does not guess.

**Chunking traps**

- The billing FAQ has a small table. A bad split can separate the fee from the tier name.
- Several answers only exist because two files agree (lapse in `07` + “non-approved gets nothing” in `02` + clawback in `06`). A single chunk will not contain the whole story. Retrieval has to be allowed to return a few chunks, and the filter cannot be so strict that the second document disappears.
- Document 06’s pointer to the billing FAQ is wrong. Prefer the sentence in document 06 plus document 12, and do not hallucinate a combined procedure.

**FAISS-specific trap (if we use FAISS)**

FAISS alone does not filter by category. If we search first and then throw away other categories, the top results might all be the wrong category and we return nothing. Fix for a small corpus: search more candidates than we keep, then apply the metadata filter, and back off if the filter empties the list. At 14 documents this is a design choice, not a performance problem. It becomes real when the corpus grows. Good thing to say in Part C.

---

## 7. How a good system behaves (the story to tell)

Same pipeline every time. Category does not pick a different app.

1. **Classify** the question into one category (or `non_relevant`).
2. **Decide** whether this is a rooftop eligibility decision that needs the tool.
3. **If the tool is needed and a field is missing,** ask for it and stop.
4. **If the tool is needed and fields are present,** call `check_rebate_eligibility`. This step does not search documents.
5. **Retrieve** chunks with the category as a metadata filter (document 06 visible to both of its categories). Skip retrieval for `non_relevant`.
6. **Write** the answer from the chunks, and from the tool result when there is one. Cite the file. If the tool failed, lead with that and do not estimate a rebate.

That is already more than two steps. In the demo, point at the tool step and the retrieval step as separate.

General question example: “How long do I have to dispute a normal bill charge?” Classify Billing. Retrieve `03`. Answer: 60 days, grievance process, and this path is not for rebate eligibility.

Eligibility example: “I’m in 94102, income $90,000, 6 kW, approved installer. What rebate do I get?” Call the tool. Answer with its amount ($2,400) and a short citation of the $0.40/watt rule. Do not let the model recompute a different number.

Failure example: same household, income $150,000. Tool returns not eligible, income, $0. Answer that. Stop.

---

## 8. How we plan to build it

This matches the sketch in `Agent.md`. It is a plan. Nothing below this heading is implemented.

**Shape**

```
app/
  api/            FastAPI routes
  rag/
    ingestion.py  load docs, split, attach category metadata
    chunking.py
    embeddings.py
    retrieval.py  vector search + metadata filter
    reranking.py  only if we have time; otherwise say we skipped it
  llm/            chat + embeddings client
  services/       agent loop, tool step
  config.py
  main.py
data/
  documents/      the 14 files (or read straight from the starter kit)
  vector_store/
    index.faiss
    metadata.json
tests/
scripts/          one-shot ingest
```

**Choices already in the sketch**

- FastAPI as the API, Streamlit as a simple front end that shows the answer, the reasoning, and the chunks used.
- Azure OpenAI, GPT for answers and for embeddings.
- FAISS plus `metadata.json` for the category filter.
- Hybrid search: embeddings together with keyword matching (BM25 / SPLADE), so a query that uses the document’s own words still hits.

**Choices still open (decide before coding)**

- Azure vs a normal OpenAI key. The brief allows either. Use whichever key you actually have. Do not block the project on Azure setup.
- Chunk size. These files are short. Split on headings, keep each section whole. Do not use a tiny token window that slices the billing table.
- Reranking. Nice, not required. With 14 documents, skipping it is a reasonable time-box call if we say so in the design doc.
- Chat memory. A single question API is enough for the brief. A few turns of history will make the demo easier.
- How document 06 is tagged: both categories (recommended above).

**What we should not spend the time box on**

- A custom training run for the classifier. A careful prompt (or a tiny set of rules plus a model) is enough at this size, with a test set that checks it.
- Replacing FAISS with a hosted vector database. Fine as a “what I’d change at 100×” answer in Part C.
- Rewriting the stub.

---

## 9. What is actually implemented today

Almost nothing. Be ready to say that if someone looks at the folder before we build.

| Item | State |
|---|---|
| Assessment brief (PDF) | Read. Requirements are in sections 3–7 of this note. |
| 14 knowledge-base documents | Present, unread by any pipeline. |
| `stub_tools.py` | Present and runnable. Signature is the original one. Do not change the rules inside it. |
| `Agent.md` | Folder sketch and technology choices only. |
| `app/`, tests, vector index, API, design doc, README for the solution | Not created. |
| `requirements.txt` | Empty. |

---

## 10. Part C answers you can give even before the code exists

Tighten these once the code is real, and put the final version in a 1–2 page design doc.

**Evaluation**

- A small labeled set of questions we write ourselves: expected category, expected source file, whether the tool must be called, and for tool cases the expected `eligible` / `reason` / amount.
- Include the traps in section 6 on purpose: document 06, missing tool fields, income exactly $120,000, commercial system, `non_relevant`, fourth tier, “what would I have gotten.”
- Offline: category accuracy, did the right file show up, did the answer stick to the tool on failures, citation present.
- Before a real launch: sample live answers, watch tool-error rate, empty-retrieval rate, and latency. A human spot-checks anything about money.

**What breaks first**

- 10× documents (still only ~140 files): quality breaks before infrastructure. Single-category filters start hiding cross-topic pages, the classifier gets less sure, and “search then filter” starts returning empty sets. Change: multi-label documents, a configurable category list, fetch a wider candidate set before filtering, and an evaluation set that grows with the corpus.
- 100× queries: cost and rate limits break first, not FAISS. Every question would call a large model for classification, embedding, and the answer. Change: cache repeated questions, use a smaller model for the category label, and keep the big model for the final answer.

**New category next month**

- Changes: the allowed category list, the classifier instructions, tags on the new documents, and a few eval questions.
- Stays: chunking, embeddings, FAISS, the agent loop, the eligibility tool, and the “filter, don’t swap pipelines” rule.
- That is why categories should live in one config list, not be copied into five files.

**Trade-off (draft, replace with the one we actually make)**

Indexing document 06 under two categories, while forcing every question into one category. A purist would pick a single home for the file. That hides it whenever the user’s wording lands in the other category. Dual tags cost a bit of retrieval precision and buy the ability to answer the clawback question from either direction. The brief allowed this kind of judgment.

---

## 11. Likely demo questions

Use these as a spoken drill. Short answers.

**Why is category a filter and not a router?**
Because most of the pipeline is identical. Only the search constraint changes. Routing would duplicate the agent and make cross-topic documents like 06 fall into the wrong app.

**Why not just let the model read all 14 files?**
It works at this size and hides whether retrieval and filters work. The design has to survive more documents. The brief asks for a vector store and a filter.

**Why call the tool if the formula is already in the policy?**
The policy describes the program. The service applies this year’s ZIP list, income line, and the hard gate, and it is the system of record. The model is good at sounding right while multiplying wrong.

**What if they fail two checks?**
The service returns the first failure only. We report that reason and $0. We do not announce a second failure we did not get back.

**What if the model wants to be helpful and show the rebate anyway?**
That violates the hard gate. The prompt and the tests both forbid a counterfactual amount after `eligible: false`.

**Where did $120,000 and the ZIP codes come from?**
Only from the stub. The policy says those live in an appendix and an annual board figure that were not included. We treat the stub as that missing source.

**What did you do with document 06?**
Tagged it as both Incentive and Billing. Query still has one label. Written down as an assumption, not as the “correct” category.

**What was out of scope?**
Say this honestly once we cut something (likely reranking, auth, a hosted vector DB, or multi-turn memory).

---

## 12. Decisions to make together before we code

1. Which API key you will actually use (Azure OpenAI or another provider from the brief).
2. Confirm document 06 gets both category tags.
3. Leave `stub_tools.py` alone. It is already the interface we must call.
4. Single-question API first, short chat history only if it stays cheap.
5. Skip reranking unless the first retrieval tests look weak, and say that in the design doc.

---

## 13. Questions, answers, and how we get there

These are member questions, not interview questions. Section 11 is the interview drill. This section is what the copilot itself should say.

The kit does not include a question list. These are the questions a reviewer will type, because each one is answered by a specific sentence in the 14 files or by the tool. If you can walk any of them the way this section does, you understand the task.

### The method, every time

Do these in order. Do not jump to writing the answer.

1. **What kind of question is it?** One category, used only to filter search:
   - Program Policies
   - Incentive & Rebate Programs
   - Billing & Account
   - Technical / Installation Guidance
   - Company Updates
   - `non_relevant` (stop here; do not search)
2. **Is this a rooftop-rebate decision for a specific household?**
   - All four facts present (ZIP, income, kW, installer approved): call the tool. The yes/no and the dollar amount come only from the tool.
   - Some facts missing: ask for them. Do not call the tool. Do not guess.
   - General rule, commercial program, battery dollars, or the $25 credit: do not call the tool.
3. **Search** with that category filter. Read the chunks. Document 06 is tagged both Incentive and Billing, so either filter can find it.
4. **Write** only what those chunks and the tool result support. Name the file. If a number is not in the file or the tool, say it is not published.

Two checks the tool applies, in order. The first failure is the only reason it returns:

installer approved → ZIP in 94101–94105 → income **under** $120,000 → size **3.0 to 10.0 kW** → `min(kW × 1000 × 0.40, 4000)`.

$120,000 and those ZIPs are not written in the policy files. They live only in the stub. For a specific household we trust the tool. We do not pretend a policy document stated the number.

---

### A. One document is enough

**What tiers are there?**
Program Policies. No tool. Source: `01`.
Community: no usable roof, you buy a share of the shared array. Household: rooftop on a primary home. Commercial: on-site generation above 25 kW.

**How often can I change tier, and does it rewrite an old rebate?**
Program Policies. No tool. Source: `01`.
Once per 12 months. It starts on the first day of the next billing cycle. It does not go back and change rebate eligibility for a system installed under the old tier.

**How long do you keep my energy data, and who sees it?**
Program Policies. No tool. Source: `01`.
24 months. Not shared with third parties except for rebate-program verification, or when the law requires it.

**What is the rooftop rebate, in general?**
Incentive. No tool. Nobody gave a ZIP, income, size, or installer, so there is nothing to check. Source: `02`.
Household tier, new rooftop system: $0.40 per watt, cap $4,000. Size must be 3–10 kW, the home must be in the service region, income must be under the annual threshold, and the installer must be approved. Income and size are hard checks. Fail either one and the amount is never calculated. Approved installer is also a hard fail (“regardless of other criteria”). The dollar threshold and the ZIP list are not in this file.

**What do I have to submit, and what if the packet is incomplete?**
Incentive. No tool. Source: `02`.
Proof the installer is approved, a copy of the utility interconnection application, and a signed income attestation. Incomplete packets sit for up to 15 business days, then close. After that you must apply again.

**The rebate budget ran out. Does that mean I was rejected?**
Incentive. No tool. Source: `02`.
No. New applications go on a waitlist until next fiscal year’s budget. That is not a failed eligibility check.

**What are the monthly fees?**
Billing. No tool. Source: `03`, the table.

| Tier | Fee | Energy rate |
|---|---|---|
| Community | $12 | $0.09/kWh |
| Household | $8 | $0.07/kWh credit |
| Commercial | $150 | Negotiated per contract |

**When is the bill due, and when does autopay charge?**
Billing. No tool. Source: `03`.
Issued on the 1st, due within 21 days. Autopay charges on the 15th.

**I want to dispute a normal charge from about three months ago.**
Billing. No tool. Source: `03`.
A non-rebate billing dispute goes through the grievance process and must be filed within 60 days of the charge appearing on a statement. Three months is past that window, so this path is closed. Rebate disputes are a different process (question set C and D).

**My rebate is approved but it is not on this month’s bill. Who do I call?**
Billing is the natural label, because they asked about the bill. Sources: `03`, and `02` for who owns disbursement.
Do not call the tool. Disbursement does not follow the normal billing cycle. Contact the Incentive Program committee, not general billing support. `03` is enough for “who to call.” `02` is the process that committee runs.

**My roof is about 25% shaded. Can I still install?**
Technical. No tool. Source: `04`.
More than 20% annual shading is generally not recommended for a standard layout. It is not a ban. Micro-inverters may be proposed where shading is partial. Do not say the rebate is denied. Shading is not an eligibility input.

**The roof faces east and west. Which inverter?**
Technical. No tool. Source: `04`.
Micro-inverters are required on a mixed-orientation roof, to avoid mismatch losses.

**The inverter shows E07. Will SunGrid fix it?**
Technical. No tool. Source: `04`.
E07 is a ground fault. The installer has to inspect it before the system is turned back on. SunGrid does not diagnose hardware. They can only say whether reported output looks normal for that size and location. E01 is usually the utility (grid voltage). E12 is often a gateway reset.

**Generation was 25% below the estimate last month. Who do I tell?**
Technical. No tool. Source: `04`.
The dashboard review is for more than 20% below the seasonal estimate for **two months in a row**. One bad month does not meet that rule. A single fault code goes to the installer, not to that dashboard path. Say the two-month rule. Do not invent a one-month remedy.

**How does a battery have to be wired and sited?**
Technical. No tool. Sources: `13`, and `04` for which inverter is which.
Micro-inverters need a battery with AC coupling. A string inverter may use AC or DC coupling. At least 3 feet from doors, windows, and anything combustible. Indoor units need a ventilation assessment before energizing. The battery is commissioned separately from the panels, including an islanding test.

**Is the new multi-family tier open, and what rebate does it get?**
Company Updates. No tool. Source: `05`.
It is planned for next fiscal year and is not finalized. Do not give eligibility or rebate rules. The newsletter says members must not rely on it until a formal policy exists.

**How big is the co-op now?**
Company Updates. No tool. Use the file that matches the question. Do not blend them.
`05` (Q2 newsletter): 4,200 active household installations; the shared community array is fully subscribed; a second array was approved.
`14` (year-end): just over 5,000 members, up from about 3,600; 38 MW; about 21,000 metric tons of CO2e; about 60% of eligible household installs that year received a rooftop rebate.
“4,200 installations” and “5,000 members” are different counts. Do not correct one with the other.

---

### B. The tool has to answer, because a specific household asked

Category for all of these: Incentive & Rebate Programs. Search can still pull `02` to explain the rule. The decision itself is the tool result.

**ZIP 94103, income $80,000, 5 kW, approved installer. Am I eligible, and for how much?**
Call the tool. All four checks pass. 5 × 1000 × 0.40 = 2,000, under the cap.
Answer: eligible. Estimated rebate **$2,000**. Reason: all checks passed.

**Same home, 10 kW.**
Call the tool. 10 × 1000 × 0.40 = 4,000, which is exactly the cap.
Answer: eligible. **$4,000**. Do not say $4,000-plus.

**Same home, 6 kW, income $90,000, ZIP 94102, approved installer.**
Call the tool. 6 × 400 = **$2,400**. Eligible.

**ZIP 94105, income $119,999, 3.0 kW, approved installer.**
Call the tool. Income is still under $120,000. Size is on the bottom boundary, and the check is inclusive.
Answer: eligible. **$1,200**.

**Same 5 kW home, but income is $120,000.**
Call the tool. Income fails (`>= 120000`). The function returns before it multiplies anything.
Answer: not eligible. Reason: household income exceeds the regional threshold. Estimated rebate **$0**.
Do not add “you would have received $2,000.” That is the partial answer the brief forbids.

**Same home, income $150,000, and the installer is not approved, and the ZIP is 10001, and the system is 2 kW.**
Call the tool. Several things are wrong. The function checks the installer first and stops.
Answer: not eligible. Reason: installer is not on the approved list. Rebate **$0**.
Do not also announce the ZIP, income, and size failures. The service did not return them. You may explain, as general policy, that any one hard failure ends the calculation. You may not list extra failures for this household.

**ZIP 94110, income $50,000, 8 kW, approved installer.**
Call the tool. Installer passes, ZIP fails.
Answer: not eligible. Outside the service region. **$0**. Do not quote 8 × 400 = $3,200.

**I’m in 94103 and I make $70,000. Am I eligible?**
Do **not** call the tool. Size and installer status are missing. Ask for both. Do not assume a size, and do not assume the installer is approved.

**If my income is too high, do I just get a smaller rebate?**
Incentive. No tool. There is no household to check, and inventing one would be wrong. Source: `02`, which matches the tool’s behavior.
No. Income is a hard check. Fail it and the rebate is not calculated at all. It is not scaled down.

---

### C. Sounds like eligibility, but the tool must stay out of it

**I’m a business installing 40 kW. What do I get?**
Incentive. Do not call the tool. A 40 kW input would fail the 3–10 kW check and sound like a rooftop rejection. Source: `02`.
Commercial tier, systems above 25 kW: a performance incentive paid quarterly from metered output, reviewed by the Carbon Markets desk. It is not the $0.40/watt rebate.

**Can I get the battery incentive with no rooftop rebate? What does 10 kWh pay?**
Incentive. Do not call the rooftop tool. The stub cannot price a battery. Sources: `09` and `02`.
No. The rooftop rebate must already be approved. A battery alone does not qualify. The add-on is $0.15 per watt-hour of usable storage, cap $1,500, and it does not use up the $4,000 rooftop cap.
10 kWh = 10,000 Wh × 0.15 = **$1,500**, which is the cap. A larger battery does not pay more than $1,500. “No extra incentive above the cap” (`13`) does not mean the battery rebate is refused.

**I have no solar. Can I get the low-income credit, and is the income line $120,000?**
Incentive. Do not call the tool. Sources: `10` and `02`.
The $25 monthly credit does not require solar and does not depend on the rooftop rebate. It applies to every tier, including Community. Income must be under **200% of the regional low-income threshold**. That threshold is not the rooftop line, and the dollar figure is not in the kit. Do not say $120,000. The credit is its own line on the bill and does not change net-metering math. Recertify every year. If you miss it, the credit pauses; missed months are not paid back.

**I’m Community tier, no panels. Walk me through the rooftop rebate.**
Incentive, plus `01` for what Community means. Do not call the tool. There is no rooftop system here.
The rooftop rebate is for household-tier members installing a new rooftop system. A community member with no rooftop is not in that program. They can still apply for the low-income credit on its own (`02` and `10`).

---

### D. Document 06, and other answers that need two files

**You paid my rebate, then reversed it. What happens to my bill, and how do I appeal?**
Primary category: Incentive & Rebate, because the decision and the appeal are the incentive process. Document `06` is also tagged Billing, so the billing half is still retrieved.
No tool. The reversal already happened; this is not a fresh eligibility calculation.
How the answer is built:
- `06`: the Incentive committee makes the reversal; Billing spreads the payback over up to 6 monthly cycles; written notice at least 30 days before the first adjusted bill.
- `06` plus `02`: appeal through the Incentive Program appeals process (within 30 days of the determination), not through the general grievance process.
- `01`: grievances explicitly do not cover rebate eligibility. That confirms the same point from the other side.
- Autopay members: the adjustment is taken on the scheduled charge. Manual-pay members: they must acknowledge the new amount in the portal before the next cycle (`06`).
`06` says that acknowledgement “follows the autopay-failure process in the Billing FAQs.” That process is not in `03`. It is in `12`. Use `06`’s own sentence for the acknowledgement, and use `12` only if they ask what a failed autopay charge does. Do not invent a merged procedure.

**My installer let their certificate lapse in the middle of the job. Is the rebate still good?**
Primary category: Incentive, because the question is about the rebate. The lapse rule itself is in `07`, which is a Program Policies document. A hard filter on Incentive alone would miss it. That is why `07` should also carry an Incentive tag: the lapse section exists to change rebate eligibility. This is the same idea as dual-tagging `06`, and it belongs in the design note.
No tool, unless they then hand you ZIP, income, size, and a yes/no on the installer. If they do, `installer_approved` should be false for work done during the lapse.
Answer from the files:
- `07`: a job done while certification is lapsed counts as a non-approved installer, even if they were certified before.
- `02`: a non-approved installer means no rebate, regardless of the other facts.
- If the money already went out, `06` is the clawback (up to 6 bills, appeal through the incentive process).

**The installer is current on the certificate, but they had two safety violations this year. Are they still approved?**
Program Policies. No tool. Sources: `01` and `07`.
No. Two or more safety-protocol violations in 12 months remove them from the approved list. Renewal and the violation process are separate. A current certificate does not save them (`07`). Removal means rebate work is non-approved (`02`).

**How do I vote, and who elects the board?**
Program Policies. No tool. Sources: `08` and `01`.
Household, Commercial, and Community each get one vote per account. Community’s vote does not grow with the size of their array share. Board seats are elected by household-tier members, about one-third of seats each year, at the spring meeting. A candidate needs 12 months in good standing. “Good standing” is not defined. Do not invent it.
`01` says voting weight varies by tier. `08` says one vote each. Say both, and do not force them into a single number. Proxy: assign it in the portal at least 5 business days before the meeting, to another member in good standing. Quorum is 15% of eligible voters, in person or by proxy. If that is missed, a follow-up meeting is held within 30 days. Meeting notice goes out at least 30 days ahead (`01`).

**Explain true-up. I exported less than I used. What rate do you charge?**
Billing. No tool. Sources: `11` for the detail, `03` for the short version and the only rates we have.
Household and Community, once a year, cycle ending in March. Net excess generation is credited at that tier’s net-metering rate. Net usage is billed at the **standard** rate, not the net-metering rate. The standard rate is not published. Do not invent one. The only household energy figure in the kit is the **$0.07/kWh credit**. Community’s table figure is **$0.09/kWh**, and the table does not call it a credit.
The true-up statement comes within 10 business days of the March close and lands on the next normal bill. Someone who joined mid-year is prorated to the months they were enrolled, not a full year (`11`).

**Autopay failed yesterday. Am I already late, and what happens next?**
Billing. No tool. Sources: `12`, plus `03` for the 45- and 90-day clocks.
Two more attempts over the next 5 business days. If those fail, that cycle becomes manual-pay. Email and portal notice after the first failure, and another notice if the retry fails. The 45-day review and the 90-day disconnection clock start from the **original due date**, not from yesterday. Re-enrolling in autopay takes effect next cycle.
`03`: more than 45 days past due is flagged for a service review. Community members are not disconnected from the shared array over a billing dispute. Disconnection applies to non-payment past 90 days.

---

### E. Refuse

**What’s the weather in San Francisco?** or **Write me a poem.**
`non_relevant`. Do not search, and do not answer from the nearest solar chunk. Say this is outside SunGrid member support.

**What is the exact standard rate on a true-up debit?** or **What dollar income qualifies for the $25 credit?**
These are in-domain, but the number is not in the kit. Say the documents do not publish it. Do not estimate.

---

### F. How to talk through one of these in the demo

Pick the reversed-rebate question and say it in this order:

1. I label it Incentive, because they are asking about a rebate decision and an appeal. I do not start a different pipeline for Billing.
2. I do not call the tool. Nothing here is a new four-field eligibility check.
3. I still find document 06, because that file is tagged Incentive and Billing.
4. I read 06 for the six-month payback and the 30-day notice, 02 for the 30-day appeal, and 01 for “grievances do not cover rebates.”
5. I mention that 06 points at the wrong file for autopay failure, and that the real retry rules are in 12. I do not paper over that.

That walk-through is the whole assessment in one answer: filter rather than router, tool only when it is the system of record, dual-tag the awkward document, and do not invent a missing fact.
