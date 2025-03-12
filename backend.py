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

load_dotenv()

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
    content = file.file.read()
    
    try:
        if file.content_type == "application/pdf":
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                if not text.strip():  # OCR fallback for scanned PDFs
                    import pytesseract
                    from pdf2image import convert_from_bytes
                    images = convert_from_bytes(content)
                    text = "\n".join([pytesseract.image_to_string(img) for img in images])
            return text
        
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
        raise RuntimeError(f"File processing error: {str(e)}")

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
        content = await file.read()
        text = ""
        
        if file.content_type == "application/pdf":
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            if not text.strip():  # OCR fallback
                images = convert_from_bytes(content)
                text = "\n".join([pytesseract.image_to_string(img) for img in images])
        
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join([para.text for para in doc.paragraphs])
        
        else:  # text/plain
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1")

        return JSONResponse({
            "filename": file.filename,
            "text": text[:5000],  # Return first 5000 chars
            "truncated": len(text) > 5000
        })
        
    except Exception as e:
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