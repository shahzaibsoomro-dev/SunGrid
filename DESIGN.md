# SunGrid copilot — design note

## What is built

This is a member-support chat system over the 14 SunGrid documents. Chat goes to an agent that uses GPT-5 on Azure OpenAI. Chunks are embedded with text-embedding-3-large, also on Azure, and each vector is 3072 dimensions. These vectors are stored in a FAISS index. Retrieval does not search the whole index and then throw away other categories. While chunking we store metadata for each chunk:

```json
{
  "id": "06#1",
  "source": "06_ambiguous_rebate_billing_adjustments.md",
  "section": "document title > heading",
  "text": "the chunk text",
  "section_categories": ["Incentive & Rebate Programs", "Billing & Account"],
  "chunk_categories": ["Billing & Account"],
  "row": 33
}
```

- `id` is the chunk id, file number plus section number.
- `source` is the document file.
- `section` is the document title and the heading.
- `text` text within that title 
- `section_categories` is the label set for the whole page.
- `chunk_categories` is the label set of that section and we do retreival on basis of this.
- `row` is the matching row in the FAISS index.

we embed section(haeding) + text and store that as a embedded chunk in our vector store

It filters the metadata first, then scores only the rows whose chunk categories overlap the question. A global search can fill the top hits with the wrong category and leave the filter with nothing.

A chunk is kept when its score is at least 0.50. If more than three chunks pass, only the top five are kept. I first kept the threshold at 0.60, but a case in the golden dataset failed, so I moved it to 0.55 and later to 0.50 to give more margin. If three or fewer pass, all of them are kept. If none pass, the tool returns nothing and the model is told to say the documents do not cover it.

## What the model returns

Every model turn is one JSON object with three fields.

- `reasoning` is a short note on how it decided.
- `intent` is exactly one label: Program Policies, Incentive & Rebate Programs, Billing & Account, Technical/Installation Guidance, Company Updates, or `non_relevant`.
- `action` is either the reply the member/user reads, or one tool call.

The two tools are `retrieve_knowledge` and `check_rebate_eligibility`. Retrieval takes the question text and a category list, and that list has to include the intent. The eligibility tool is the stub in the starter kit. It is used only when the intent is Incentive & Rebate Programs and the member has given ZIP, income, system size, and whether the installer is approved. Commercial incentives, the battery add-on, the low-income credit, and appeals stay on that intent and are answered from documents. 

The ZIP list and the $120,000 income line are not in the policy documents, and they are not in the prompt, they are only in stub. If it says the household is not eligible, the rebate is $0.



## Part C#1: Before shipping

1. I would have extended my evaluation system more in depth, as have added one evaluation at retreival 
stage where i would have built a golden dataset against few common queries and test it accordingly. i've already built a small one. 
2. I usually build an easy, medium, and hard query set for this kind of system, and check retrieval and generation on them. I would measure accuracy and time to first token.
3. After retrieval is evaluated, I would evaluate generation. That part is mostly human review.
4. A golden set for answers, and the generation review, need a subject matter expert.

## Part C#2: What breaks first

1. At 10x documents, retrieval quality and indexing become the problem. I would look at better metadata and partitioning, the indexing strategy, hybrid search, reranking, incremental ingestion, and scaling the vector database.
2. At 100x queries, latency and cost become the problem. I would cache results, shorten time to first token on easy queries, retrieve asynchronously, and serve this through an API, would see where i can use lighter llm to save time and cost.
3. Ten times the documents is still a small corpus for this system. The first thing that breaks is the fixed 0.50 threshold and the single retrieval query. I would experiment with more queries, fusion, and reranking.

## Part C#3:  A new category

1. Add the new category to the label list, and put that label on the new chunks. Retrieval already filters on the labels it is given. The agent loop, the JSON shape, and the eligibility tool stay as they are.
2. The harder problem is labeling at scale. Fourteen files can be labeled by hand. A new category, or a lot of new documents, needs a labeling step before those chunks are indexed. 

## Part C#4: One tradeoff

Chunks have to be labeled when they are created, by a subject matter expert or another labeling pass, so retrieval can narrow to the right ones. I labeled this set by page, then narrowed a few sections of documents 06 and 07 by hand. The tradeoff is that a label that is too narrow hides a chunk from the other category, and a label that is too wide pulls in sections that do not answer the question. So I'm assuming we would need a SME for labeling each chunk or whatever the pass is but we would need chunks labeled.
Chunking is the back bone of RAG systems, we need to focus on them the most.


## If this were production

- I would use Qdrant, not FAISS, as FAISS is just a store/library for vectors, not a proper database. Once the corpus grows I need filters, updates, and backups in one place, not a file the app loads itself.
- Add hybrid search with BM25 (SPLADE). Embeddings performs bad when we have exact amounts, ZIP codes, and short phrases like "6 monthly bills".
- Search with more than one query and rerank the results. A short member question often does not use the same words as the heading where the answer sits.
- Build a proper evaluation setup. The golden set only checks three retrieval questions. It does not check the written answer, or that a failed eligibility check.
- Serve it as an API with SSE streaming. The terminal and Streamlit app wait for the whole reply. A member should see the answer as it is written.
- Add logging and monitoring. I need the intent, the tool, an empty retrieval, latency, and any rebate amount after a failed check, or I will not know the failure happened.
- I would experiment with temperature and the other model parameters, and keep the settings that fit this system's needs.