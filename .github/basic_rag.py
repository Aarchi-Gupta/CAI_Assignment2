# -*- coding: utf-8 -*-
"""Basic_RAG.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/19RYpz6kUa3pAWpH1c0vb8yjsfqqcHrfs
"""

import pdfplumber
import fitz  # PyMuPDF
import pandas as pd
import re
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import faiss
import numpy as np
import pickle
import chromadb  # Vector Database

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize ChromaDB client and collection
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("financial_data")

# Function to extract text from PDF
def extract_text(pdf_path):
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text())
    return "\n".join(filter(None, text))  # Join pages, remove None values

# Function to extract tables
def extract_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_table()
            if extracted:
                df = pd.DataFrame(extracted[1:], columns=extracted[0])  # Use first row as header
                tables.append(df)
    return tables

# Function to clean extracted text
def clean_text(text):
    text = re.sub(r'\n+', '\n', text)  # Normalize multiple newlines
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces
    return text.strip()

# Function to chunk text into smaller pieces
def chunk_text(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    return splitter.split_text(text)

# Function to convert tables into structured format
def process_tables(tables):
    structured_data = []
    for df in tables:
        structured_data.append(df.to_dict(orient="records"))  # Convert DataFrame to list of dicts
    return structured_data

# Function to embed text chunks
def embed_text(chunks):
    embeddings = embedding_model.encode(chunks, convert_to_numpy=True)
    return embeddings

"""###FAISS Start"""

# Function to store embeddings and chunks in FAISS
def store_in_faiss(embeddings, chunks, faiss_index_file, metadata_file):
    d = embeddings.shape[1]  # Dimension of embeddings
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)  # Add embeddings to FAISS

    # Save the FAISS index
    faiss.write_index(index, faiss_index_file)

    # Save chunks metadata
    with open(metadata_file, "wb") as f:
        pickle.dump(chunks, f)

    return index

# Function to load FAISS index and metadata
def load_faiss_index(faiss_index_file, metadata_file):
    index = faiss.read_index(faiss_index_file)
    with open(metadata_file, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks

# Function to retrieve similar text chunks from FAISS
def retrieve_similar_chunks(query, index, chunks, top_k=3):
    query_embedding = embedding_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    results = [chunks[idx] for idx in indices[0]]
    return results

# Main function to process the PDFs and store embeddings
def process_and_store_financial_reports(pdf_path, faiss_index_file="faiss_index.bin", metadata_file="chunks.pkl"):
    text = extract_text(pdf_path)
    tables = extract_tables(pdf_path)

    cleaned_text = clean_text(text)
    text_chunks = chunk_text(cleaned_text)
    structured_tables = process_tables(tables)

    # Combine text and table data for embedding
    all_chunks = text_chunks + [str(table) for table in structured_tables]

    # Generate embeddings
    embeddings = embed_text(all_chunks)

    # Store embeddings in FAISS
    store_in_faiss(embeddings, all_chunks, faiss_index_file, metadata_file)

    return embeddings, all_chunks

# Process 2023 and 2024 reports
process_and_store_financial_reports("2024-02-06-COGNIZANT-REPORTS-FOURTH-QUARTER-AND-FULL-YEAR-2023-RESULTS.pdf",
                                    "faiss_index_2023.bin", "chunks_2023.pkl")
process_and_store_financial_reports("2025-02-05-Cognizant-Reports-Fourth-Quarter-and-Full-Year-2024-Results.pdf",
                                    "faiss_index_2024.bin", "chunks_2024.pkl")

# Load FAISS index for retrieval
index_2023, chunks_2023 = load_faiss_index("faiss_index_2023.bin", "chunks_2023.pkl")

# Load FAISS index for retrieval
index_2024, chunks_2024 = load_faiss_index("faiss_index_2024.bin", "chunks_2024.pkl")

# Example query to retrieve similar financial data
query = "How much is the Total liabilities and stockholders' equity until December 31, 2024"
retrieved_chunks = retrieve_similar_chunks(query, index_2023, chunks_2023)

# Print retrieved results
print("Top Retrieved Chunks:")
for chunk in retrieved_chunks:
    print(chunk)
    print("-" * 50)

# Example query to retrieve similar financial data
query_2024 = "How much is the Total liabilities and stockholders' equity until December 31, 2024"
retrieved_chunks_2024 = retrieve_similar_chunks(query_2024, index_2024, chunks_2024)

# Print retrieved results
print("Top Retrieved Chunks:")
for chunk in retrieved_chunks_2024:
    print(chunk)
    print("-" * 50)

"""###FAISS END"""

from huggingface_hub import login

# Log in to your Hugging Face account
login(token='hf_KWGCDOKcYOUrYUUJZurryXKJrwxqqNgnNK')

from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

# Download and cache the model and tokenizer
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Create the pipeline
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

def ask_local_llm(query, retrieved_chunks):
    context = "\n\n".join(retrieved_chunks)
    prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

    response = generator(prompt, max_new_tokens=200)
    return response[0]["generated_text"]

# Generate response using local LLM
response = ask_local_llm(query_2024, retrieved_chunks_2024)
print(response)

"""###ChromaDB"""

# Function to embed and store in ChromaDB
def embed_and_store(chunks, doc_id):
    embeddings = embedding_model.encode(chunks, convert_to_numpy=True)
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        collection.add(
            ids=[f"{doc_id}_{i}"],
            embeddings=[embedding.tolist()],
            metadatas=[{"text": chunk, "source": doc_id}]
        )

# Function to process PDFs and store in ChromaDB
def process_and_store_financial_reports(pdf_path, doc_id):
    text = extract_text(pdf_path)
    tables = extract_tables(pdf_path)
    cleaned_text = clean_text(text)
    text_chunks = chunk_text(cleaned_text)
    structured_tables = process_tables(tables)
    all_chunks = text_chunks + [str(table) for table in structured_tables]
    embed_and_store(all_chunks, doc_id)

# Process reports
doc_2023 = "2023_Financial_Report"
doc_2024 = "2024_Financial_Report"
process_and_store_financial_reports("2024-02-06-COGNIZANT-REPORTS-FOURTH-QUARTER-AND-FULL-YEAR-2023-RESULTS.pdf", doc_2023)
process_and_store_financial_reports("2025-02-05-Cognizant-Reports-Fourth-Quarter-and-Full-Year-2024-Results.pdf", doc_2024)

# Function to retrieve relevant chunks
def retrieve_similar_chunks(query, top_k=3):
    query_embedding = embedding_model.encode([query], convert_to_numpy=True)[0]
    results = collection.query(query_embeddings=[query_embedding.tolist()], n_results=top_k)
    print(results["distances"][0])
    print(results["metadatas"][0])
    if min(results["distances"][0]) < 0.8:
      return results["metadatas"][0] if "metadatas" in results else []
    else:
      return [{"text":"I don't have enough information on this topic."}]

# Example Query
query_DB = ["How did Cognizant's voluntary attrition rate change between 2023 and 2024?",
    "What was Cognizant's revenue growth in 2024 compared to 2023?",
    "How did operating margin fluctuate in these two years?"]
retrieved_chunks_DB = retrieve_similar_chunks(query_DB)
print(retrieved_chunks_DB)

# Print retrieved results
print("Top Retrieved Chunks:")
for chunk in retrieved_chunks_DB:
  print(chunk["text"])

"""###SLM for text generation"""

def ask_local_llm(query, retrieved_chunks):
    # Extract text from retrieved chunks
    context = "\n\n".join([chunk["text"] for chunk in retrieved_chunks])


    prompt = f"""
    You are a financial AI answering based on Cognizant's 2023 and 2024 report.
    Stick to the retrieved context. If unsure, say "I don't know."

    Context:
    {context}

    Question: {query}
    """

    response = generator(prompt, max_new_tokens=200)
    return response[0]["generated_text"]

# Generate response using local LLM
response = ask_local_llm(query_DB, retrieved_chunks_DB)
print(response)

!pip install ipynb-py-convert

!jupyter nbconvert --to script Basic_RAG.ipynb