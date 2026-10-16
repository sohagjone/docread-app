# pdf-app.py  (Streamlit Cloud version, uses Gemini)

import os
import logging
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

logging.basicConfig(level=logging.INFO)

# Constants (model names change often; check ai.google.dev if one stops working)
DOC_PATH = "./data/BOI.pdf"
CHAT_MODEL = "gemini-3.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-2"
VECTOR_STORE_NAME = "simple-rag"
GOOGLE_API_KEY = "AIzaSyAT_kvPU9T3s7mD7hGcWwARi6jXRWFAfjw"
# Read the key by its NAME from Streamlit secrets. Never paste the key here.
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Streamlit secrets.")
    st.stop()
API_KEY = st.secrets["GOOGLE_API_KEY"]


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


@st.cache_resource(show_spinner="Building the vector database (first run can take a minute)...")
def load_vector_db():
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL, google_api_key=API_KEY
    )
    chunks = split_documents(ingest_pdf(DOC_PATH))

    # In-memory database: rebuilt when the app restarts, cached while it runs
    vector_db = Chroma(
        collection_name=VECTOR_STORE_NAME,
        embedding_function=embeddings,
    )
    batch = 16
    for i in range(0, len(chunks), batch):
        vector_db.add_documents(chunks[i:i + batch])
    logging.info("Vector database created.")
    return vector_db


@st.cache_resource(show_spinner="Loading the model...")
def get_chain():
    llm = ChatGoogleGenerativeAI(model=CHAT_MODEL, google_api_key=API_KEY)
    retriever = load_vector_db().as_retriever(search_kwargs={"k": 4})

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
