from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from openai import OpenAI
import pdfplumber
import docx
import io
import re
import json
import os
from dotenv import load_dotenv
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# At the top of the file, after imports
import nltk
import time
import os

# Replace the existing NLTK download code
# After imports, modify the NLTK setup
def setup_nltk():
    """Setup NLTK data with retry mechanism"""
    nltk_data_dir = os.path.join(os.path.expanduser("~"), "nltk_data")
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    try:
        # Download without using zip files
        nltk.download('punkt', download_dir=nltk_data_dir, quiet=True)
        nltk.download('stopwords', download_dir=nltk_data_dir, quiet=True)
        return True
    except Exception as e:
        print(f"NLTK setup error: {str(e)}")
        return False

# Modify the OpenAI client initialization
load_dotenv()  # Ensure this is called before accessing env variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "DocAnalyzer"
    }
)

app = FastAPI()

# ======================
# Configuration
# ======================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ======================
# Phase 1: Document Processing (No LLM)
# ======================
def extract_text(file: UploadFile):
    """Handle all file types correctly"""
    try:
        # Reset file position to beginning
        file.file.seek(0)
        content = file.file.read()
        
        if file.content_type == "application/pdf":
            # Check if file is empty
            if not content or len(content) < 100:
                return "Empty or invalid PDF file"
            
            # Try multiple PDF libraries
            pdf_text = ""
            
            # Try pdfplumber
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    pdf_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                    if pdf_text.strip():
                        return pdf_text
            except Exception as e:
                print(f"pdfplumber error: {str(e)}")
            
            # Try PyPDF2
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                if len(reader.pages) > 0:
                    pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages])
                    if pdf_text.strip():
                        return pdf_text
            except Exception as e:
                print(f"PyPDF2 error: {str(e)}")
            
            # If we couldn't extract text, return a message
            if not pdf_text.strip():
                return "Could not extract text from PDF. The file may be scanned or protected."
            
            return pdf_text
        
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([para.text for para in doc.paragraphs])
        
        elif file.content_type == "text/plain":
            # Try UTF-8 first, fallback to latin-1
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1")
        
        raise ValueError(f"Unsupported file type: {file.content_type}")
    
    except Exception as e:
        print(f"Extract text error: {str(e)}")
        return f"Error processing file: {str(e)}"

# Add after imports
def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence)
        if current_size + sentence_size > chunk_size and current_chunk:
            # Add chunk to list
            chunks.append(' '.join(current_chunk))
            # Keep last few sentences for overlap
            overlap_text = ' '.join(current_chunk[-3:])  # Keep last 3 sentences
            current_chunk = [overlap_text, sentence]
            current_size = len(overlap_text) + sentence_size
        else:
            current_chunk.append(sentence)
            current_size += sentence_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# Modify the query_llama function
def query_llama(prompt: str, text: str) -> str:
    """Process text in chunks and combine results"""
    chunks = chunk_text(text, chunk_size=4000, overlap=200)
    all_responses = []
    
    try:
        for chunk in chunks:
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "DocAnalyzer"
                },
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a expert document analyst. Analyze the following chunk of text and provide accurate, concise responses."},
                    {"role": "user", "content": f"{prompt}\n\nDocument Text Chunk:\n{chunk}"}
                ]
            )
            all_responses.append(completion.choices[0].message.content)
        
        # Combine responses
        if len(all_responses) == 1:
            return all_responses[0]
        
        # For multiple chunks, summarize the combined responses
        combined_prompt = "Combine and summarize the following analysis results:\n\n" + "\n\n".join(all_responses)
        final_completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "DocAnalyzer"
            },
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert at combining and summarizing document analysis results."},
                {"role": "user", "content": combined_prompt}
            ]
        )
        return final_completion.choices[0].message.content
        
    except Exception as e:
        raise HTTPException(500, f"LLM API Error: {str(e)}")

# Modify the upload endpoint
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate file type
        if file.content_type not in [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ]:
            raise HTTPException(400, "Unsupported file type")

        # Process file
        file.file.seek(0)  # Reset file position
        text = extract_text(file)
        
        # Check if text extraction was successful
        if text.startswith("Error processing file:") or text.startswith("Could not extract text"):
            return JSONResponse({
                "filename": file.filename,
                "text": "File could not be processed properly. Please try a different file.",
                "error": text,
                "char_count": 0,
                "word_count": 0
            }, status_code=206)  # Partial Content
        
        # Return full text
        return JSONResponse({
            "filename": file.filename,
            "text": text,
            "char_count": len(text),
            "word_count": len(text.split())
        })
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(500, f"File processing failed: {str(e)}")

# ======================
# Phase 2: LLM Processing
# ======================
def query_llama(prompt: str, text: str) -> str:
    """Generic LLM query function"""
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "DocAnalyzer"
            },
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a expert document analyst. Provide accurate, concise responses."},
                {"role": "user", "content": f"{prompt}\n\nDocument Text:\n{text[:15000]}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(500, f"LLM API Error: {str(e)}")

@app.post("/analyze/summarize")
async def summarize(text: str = Form(...)):
    prompt = """Create a comprehensive summary with:
    - Key objectives
    - Main findings
    - Significant conclusions
    - Supporting data
    Format as bullet points."""
    return JSONResponse({"summary": query_llama(prompt, text)})

@app.post("/analyze/qa")
async def question_answer(text: str = Form(...), question: str = Form(...)):
    prompt = f"""Answer based EXCLUSIVELY on this document:
    Question: {question}
    Provide:
    - Direct answer
    - Relevant excerpt
    - Confidence level (High/Medium/Low)"""
    return JSONResponse({"answer": query_llama(prompt, text)})

@app.post("/analyze/key-elements")
async def key_elements(text: str = Form(...)):
    prompt = """Extract and format:
    - Conclusions
    - Recommendations
    - Critical data
    - Key terms
    Format as JSON with keys: conclusions, recommendations, data_points, key_terms"""
    response = query_llama(prompt, text)
    try:
        return JSONResponse(json.loads(re.findall(r'\{.*?\}', response, re.DOTALL)[0]))
    except:
        return JSONResponse({"error": "Failed to parse response"})

@app.post("/analyze/entities")
async def recognize_entities(text: str = Form(...)):
    prompt = """Identify and categorize entities:
    - PERSON (names)
    - ORG (organizations)
    - GEO (locations)
    - DATE (dates)
    - TECH (technical terms)
    Format as JSON with category arrays."""
    response = query_llama(prompt, text)
    try:
        return JSONResponse(json.loads(re.findall(r'\{.*?\}', response, re.DOTALL)[0]))
    except:
        return JSONResponse({"error": "Failed to parse response"})

@app.post("/compare")
async def compare_docs(text1: str = Form(...), text2: str = Form(...)):
    prompt = """Compare these documents and highlight:
    - Content differences
    - Additions/Deletions
    - Data discrepancies
    - Thematic changes
    Format as:
    - Summary
    - Key differences (bulleted)
    - Change analysis"""
    return JSONResponse({"comparison": query_llama(prompt, f"DOC1:\n{text1}\n\nDOC2:\n{text2}")})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
