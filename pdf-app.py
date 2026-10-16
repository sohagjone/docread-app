# pdf-rag-streamlit.py

import os
import logging
import streamlit as st
import ollama
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

logging.basicConfig(level=logging.INFO)

# Constants
DOC_PATH = "./data/BOI.pdf"
MODEL_NAME = "llama3.2"
EMBEDDING_MODEL = "nomic-embed-text"
VECTOR_STORE_NAME = "simple-rag"
PERSIST_DIRECTORY = "./chroma_db"
USE_MULTI_QUERY = False  # True = better recall but much slower on a CPU


def ingest_pdf(doc_path):
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"PDF file not found at path: {doc_path}")
    data = PyPDFLoader(doc_path).load()
    logging.info("PDF loaded successfully.")
    return data


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
    chunks = splitter.split_documents(documents)
    logging.info("Documents split into chunks.")
    return chunks


def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)


@st.cache_resource(show_spinner="Loading vector database (first run can take a minute)...")
def load_vector_db():
    # Pull the embedding model only if it is not installed yet
    installed = [m.model for m in ollama.list().models]
    if not any(name.startswith(EMBEDDING_MODEL) for name in installed):
        ollama.pull(EMBEDDING_MODEL)

    vector_db = Chroma(
        collection_name=VECTOR_STORE_NAME,
        embedding_function=OllamaEmbeddings(model=EMBEDDING_MODEL),
        persist_directory=PERSIST_DIRECTORY,
    )

    # Build the database only if it is empty (Chroma saves automatically)
    if len(vector_db.get()["ids"]) == 0:
        chunks = split_documents(ingest_pdf(DOC_PATH))
        batch = 8
        for i in range(0, len(chunks), batch):
            vector_db.add_documents(chunks[i:i + batch])
        logging.info("Vector database created and persisted.")
    else:
        logging.info("Loaded existing vector database.")
    return vector_db


@st.cache_resource(show_spinner="Loading the model...")
def get_chain():
    llm = ChatOllama(model=MODEL_NAME, num_ctx=2048, num_predict=400)
    vector_db = load_vector_db()

    if USE_MULTI_QUERY:
        try:
            from langchain.retrievers.multi_query import MultiQueryRetriever
        except ImportError:
            from langchain_classic.retrievers.multi_query import MultiQueryRetriever
        retriever = MultiQueryRetriever.from_llm(
            vector_db.as_retriever(search_kwargs={"k": 3}), llm
        )
    else:
        retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_template(
        """Answer the question based ONLY on the following context:
{context}
Question: {question}
"""
    )

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def main():
    st.title("Document Assistant")

    user_input = st.text_input("Enter your question:", "")

    if user_input:
        try:
            chain = get_chain()
            st.markdown("**Assistant:**")
            st.write_stream(chain.stream(user_input))
        except FileNotFoundError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.info("Please enter a question to get started.")


if __name__ == "__main__":
    main()