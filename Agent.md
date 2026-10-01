Important Note:
- We need to 


Firstly we need to build a 

app/
├── api/
├── rag/
│   ├── ingestion.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── retrieval.py
│   └── reranking.py
├── llm/
├── services/
├── config.py
└── main.py

data/
-- documents/
-- vector_store/
   -- index.faiss
   -- metadata.json (to apply filters/metadata on embeddings/indexes)
tests/
scripts/




FastApi as api service
azure as an LLM provider
gpt for llms and embeddings
Faiss for vector library/indexing
we would be having a index and metadata file 
we will be having embeddings + bm25(splade) etc inshort keyword matching + embeddings
we will build a streamlit app as frotend (clean and simple)
we will show reasoning and relevant chunks from where we got answer from (if any)
prompt.py file where we are using many and big prompts
