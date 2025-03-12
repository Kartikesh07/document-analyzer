import streamlit as st
import requests
import json
import base64
from io import BytesIO
import time
from PIL import Image
import numpy as np
import threading
import subprocess
import time

def start_backend():
    # Start the FastAPI server using uvicorn
    subprocess.Popen(["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"])
    # Wait a couple of seconds to ensure the backend is up before making any requests
    time.sleep(2)

# Start the backend in a separate daemon thread
threading.Thread(target=start_backend, daemon=True).start()
# Configuration
BACKEND_URL = "http://localhost:8000"
SUPPORTED_TYPES = ["pdf", "docx", "txt"]

# Apply dark theme and custom styling
def apply_custom_style():
    st.markdown("""
    <style>
    /* Overall page styling */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #7986cb;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Main title */
    .main-title {
        background: linear-gradient(90deg, #7986cb, #3949ab);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Cards */
    .card {
        background-color: #1a1f2c;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #7986cb;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #3949ab;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 15px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #5c6bc0;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Input fields */
    .stTextInput>div>div>input {
        background-color: #2a2f3a;
        color: white;
        border: 1px solid #3949ab;
        border-radius: 5px;
    }
    
    /* File uploader */
    .stFileUploader>div>button {
        background-color: #3949ab;
        color: white;
    }
    
    /* Radio buttons */
    .stRadio>div {
        background-color: #1a1f2c;
        padding: 10px;
        border-radius: 10px;
    }
    
    /* Success message */
    .success-box {
        background-color: #1a472a;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #2e7d32;
        margin: 10px 0;
    }
    
    /* Info message */
    .info-box {
        background-color: #0d47a1;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #1976d2;
        margin: 10px 0;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1a1f2c;
        border-radius: 5px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1f2c;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        color: white;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3949ab !important;
        color: white !important;
    }
    
    /* Dividers */
    hr {
        border-color: #3949ab;
        margin: 30px 0;
    }
    
    /* Table styling */
    .dataframe {
        background-color: #1a1f2c;
        color: white;
        border-radius: 5px;
    }
    
    .dataframe th {
        background-color: #3949ab;
        color: white;
        padding: 10px;
    }
    
    .dataframe td {
        padding: 8px;
    }
    
    /* Spinner */
    .stSpinner>div>div {
        border-top-color: #3949ab !important;
    }
    
    /* Status */
    .StatusWidget-enter-done {
        background-color: #1a1f2c;
        border: 1px solid #3949ab;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to handle file uploads
def handle_upload(uploaded_file):
    """Proper file upload handling with error reporting"""
    try:
        # Create proper multipart form data
        files = {
            "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
        }
        
        response = requests.post(
            f"{BACKEND_URL}/upload",
            files=files,
            timeout=30  # Add timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_msg = "Unknown error"
        try:
            error_msg = e.response.json().get('detail', 'Unknown error')
        except:
            pass
        st.error(f"Backend error: {error_msg}")
    except requests.exceptions.ConnectionError:
        st.error("Connection failed: Cannot reach the backend server. Please check if the server is running.")
    except requests.exceptions.Timeout:
        st.error("Connection timeout: The server took too long to respond. Try with a smaller file.")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
    return None

# Function to display JSON data in formatted sections
def display_json(data):
    """Display JSON data in elegantly styled cards"""
    if isinstance(data, dict):
        for key, value in data.items():
            with st.expander(f"📌 {key.title()}", expanded=False):
                st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                    # Convert list of dicts to DataFrame
                    import pandas as pd
                    st.dataframe(pd.DataFrame(value), use_container_width=True)
                elif isinstance(value, list):
                    # Display as a list with bullets
                    for item in value:
                        st.markdown(f"• {item}")
                else:
                    st.write(value)
                st.markdown("</div>", unsafe_allow_html=True)

# Function to generate a loading animation
def load_animation():
    with open("data:image/gif;base64,R0lGODlhgACAAPIAAP///93d3bu7u5mZmQAA/wAAAAAAAAAAACH5BAUFAAQAIf8LTkVUU0NBUEUyLjADAQAAACwAAAAAgACAAAAD/ki63P4wygYCmMnOTMD9GKVHEGBpEiRpvubKtOVrfO+zTfP82vMfg0CgsEgsCo9IEXJJFDanCScz+qxar9goQsvsCr1TcBj8RZvP6LR6Te4Sxmu4W86p1z9B+36PF+T9gIFddoOEhXGHiImJYYuOhI2PkpOJk5aMf5idm5F1oZGKo6WojXmojq6srpmis7Corbitq6q2uai6u7inssDBpb7EwcfGvsi8zMvKz7jR0rfP1dTX073Z28HY3tnL37Xl5OPb6ODp7OHf7+vt8uPz9vX4++Ht/Pz+/wABOuInEF69fwgBMgRY0OCWgwwdRpRIMWLFixE9TsRIUf/jRpAaS2YsyFHkSZIpT7JkKHOlS5guZ7KUaXOjzZ03eZrkmHNoz6BBP+oc+jPpEKJImdJwmhSp06I3plKVehVqDq1auXod+zXs17JZzZ5NKZIF27ZD384laRbuXI915d6VWxfvXLZ59abVCxjv4MD6+B4GbPhw38SIFy9GHFhyY8STK0OmfJnxZsyROV/2DBq0ZdOfTaMWnXo16xhq93H+sfsJFFqWR59WTVv2GCeYaM22mJu3Ctm8dUv6HXw4JOHDizM3jnw5pOWYjT+3sZx6c+rVsReHTh27Iu3buVv3Dv4ReO/ky5tPT36S+vXm27unDr++/fr99ev3D7///gD+JyCBBPZHYIEHCojggQIu2OCDDioo4YQSVohhgBhmqOGGHFrY4YcZepjhhyCKWOKJIp6I4oostgjiiy7GKGOJMs5I44023ogjjjr2yKOPPw4Z5I9D7ljkj0geORwAADs=", "rb") as f:
        return f.read()

# Function to create animated progress
def create_progress_animation():
    animation = load_animation()
    animation_placeholder = st.empty()
    animation_placeholder.markdown(
        f'<img src="data:image/gif;base64,{base64.b64encode(animation).decode()}" alt="loading..." style="width:100px;height:100px;">',
        unsafe_allow_html=True
    )
    return animation_placeholder

# Function to display an elegant alert
def show_alert(message, alert_type="info"):
    if alert_type == "success":
        st.markdown(f'<div class="success-box">{message}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="info-box">{message}</div>', unsafe_allow_html=True)

# Function to create a pulsing effect on waiting
def pulse_effect(element, seconds=3):
    for i in range(10):
        element.markdown(f"<div style='opacity:{0.5 + 0.5 * np.sin(i/2)};'>⏳ Processing...</div>", unsafe_allow_html=True)
        time.sleep(seconds/10)

# Main application
def main():
    st.set_page_config(
        page_title="LLaMA Document Analyzer",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom styling
    apply_custom_style()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 📊 Document Analyzer")
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This tool uses LLaMA to analyze documents and extract valuable insights.
        
        **Features:**
        * Document Summarization
        * Question Answering
        * Key Element Extraction
        * Entity Recognition
        * Document Comparison
        
        **Supported file types:**
        * PDF (.pdf)
        * Word (.docx)
        * Text (.txt)
        """)
        
        st.markdown("---")
        st.markdown("### File Limitations")
        st.info("Maximum file size: 10MB")
        
        st.markdown("---")
        st.markdown("### Help")
        if st.button("How to Use"):
            st.markdown("""
            1. Upload your document(s)
            2. Select the analysis type
            3. View the results
            
            For best results, ensure documents are text-based (not scanned images).
            """)
    
    # Main content
    st.markdown("<div class='main-title'><h1>📄 Intelligent Document Processing System</h1></div>", unsafe_allow_html=True)
    
    # Initialize session state
    if "document_text" not in st.session_state:
        st.session_state.document_text = ""
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []
    
    # Main tabs with custom styling
    tab_analyze, tab_compare, tab_history = st.tabs(["📝 Document Analysis", "🔍 Document Comparison", "📚 Analysis History"])
    
    with tab_analyze:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("📤 Upload Document")
            
            # File upload section with animation
            uploaded_file = st.file_uploader(
                "Select document (PDF, DOCX, TXT)",
                type=SUPPORTED_TYPES,
                key="main_file"
            )
            
            if uploaded_file:
                if uploaded_file.size > 10 * 1024 * 1024:  # 10MB limit
                    st.error("File size exceeds 10MB limit")
                    st.stop()
                    
                with st.status("Processing document...", expanded=True) as status:
                    # Create a pulsing animation
                    status_elem = st.empty()
                    pulse_effect(status_elem, 1.5)
                    
                    # Step 1: Upload and extract text
                    status_elem.markdown("🔍 Extracting text from document...")
                    upload_result = handle_upload(uploaded_file)
                    
                    if upload_result:
                        st.session_state.document_text = upload_result.get("text", "")
                        status.update(label="✅ Document processed successfully!", state="complete")
                        show_alert(f"Successfully processed: {uploaded_file.name}", "success")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            if st.session_state.document_text:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.subheader("📊 Document Statistics")
                
                # Document stats
                word_count = len(st.session_state.document_text.split())
                char_count = len(st.session_state.document_text)
                
                # Display stats with gauges
                st.markdown(f"**File name:** {uploaded_file.name if 'uploaded_file' in locals() else 'Document'}")
                st.markdown(f"**Words:** {word_count:,}")
                st.markdown(f"**Characters:** {char_count:,}")
                
                # Word count gauge
                st.markdown("**Document size:**")
                if word_count < 500:
                    st.progress(0.2)
                    st.caption("Small document")
                elif word_count < 2000:
                    st.progress(0.5)
                    st.caption("Medium document")
                else:
                    st.progress(0.9)
                    st.caption("Large document")
                st.markdown("</div>", unsafe_allow_html=True)
        
        if st.session_state.document_text:
            # Text preview with improved styling
            with st.expander("📝 Document Preview", expanded=False):
                st.markdown("<div style='background-color: #1a1f2c; padding: 15px; border-radius: 10px;'>", unsafe_allow_html=True)
                preview = st.session_state.document_text[:2000] + ("..." if len(st.session_state.document_text) > 2000 else "")
                st.text_area("Extracted Text", preview, height=200, disabled=True)
                if len(st.session_state.document_text) > 2000:
                    st.caption("Showing first 2000 characters...")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Analysis options with improved styling
            st.markdown("---")
            st.subheader("🔍 Analysis Options")
            
            # Analysis type selection with icons
            analysis_type = st.radio(
                "Select Analysis Type:",
                [
                    "✨ Summarize", 
                    "❓ Question Answering", 
                    "🔑 Key Elements", 
                    "🏢 Entity Recognition"
                ],
                horizontal=True,
                index=0
            )
            
            # Display appropriate analysis interface based on selection
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            if analysis_type == "✨ Summarize":
                st.write("Generate a comprehensive summary of the document with key points and main findings.")
                if st.button("Generate Summary", key="btn_summary"):
                    progress_placeholder = st.empty()
                    progress_bar = progress_placeholder.progress(0)
                    
                    # Simulate progress
                    for i in range(101):
                        time.sleep(0.01)
                        progress_bar.progress(i)
                    
                    with st.spinner("Analyzing document..."):
                        result = requests.post(
                            f"{BACKEND_URL}/analyze/summarize",
                            data={"text": st.session_state.document_text}
                        ).json()
                    
                    # Clear the progress bar
                    progress_placeholder.empty()
                    
                    if result:
                        st.markdown("<div style='background-color: #1a1f2c; padding: 20px; border-radius: 10px; border-left: 4px solid #3949ab;'>", unsafe_allow_html=True)
                        st.subheader("📋 Document Summary")
                        st.markdown(result.get("summary", ""))
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Add to history
                        if "analysis_history" in st.session_state:
                            st.session_state.analysis_history.append({
                                "type": "Summary",
                                "document": uploaded_file.name if 'uploaded_file' in locals() else "Document",
                                "result": result.get("summary", ""),
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
            
            elif analysis_type == "❓ Question Answering":
                st.write("Ask specific questions about the document content.")
                question = st.text_input("Enter your question about the document:")
                
                if question and st.button("Get Answer", key="btn_qa"):
                    with st.spinner("Searching for answers..."):
                        result = requests.post(
                            f"{BACKEND_URL}/analyze/qa",
                            data={
                                "text": st.session_state.document_text,
                                "question": question
                            }
                        ).json()
                    
                    if result:
                        st.markdown("<div style='background-color: #1a1f2c; padding: 20px; border-radius: 10px; border-left: 4px solid #2e7d32;'>", unsafe_allow_html=True)
                        st.subheader("💬 Answer")
                        st.markdown(result.get("answer", ""))
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Add to history
                        if "analysis_history" in st.session_state:
                            st.session_state.analysis_history.append({
                                "type": "Question & Answer",
                                "document": uploaded_file.name if 'uploaded_file' in locals() else "Document",
                                "question": question,
                                "result": result.get("answer", ""),
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
            
            elif analysis_type == "🔑 Key Elements":
                st.write("Extract important elements like conclusions, recommendations, and critical data points.")
                if st.button("Extract Key Elements", key="btn_elements"):
                    with st.spinner("Identifying key elements..."):
                        result = requests.post(
                            f"{BACKEND_URL}/analyze/key-elements",
                            data={"text": st.session_state.document_text}
                        ).json()
                    
                    if result:
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.subheader("🔑 Key Document Elements")
                            display_json(result)
                            
                            # Add to history
                            if "analysis_history" in st.session_state:
                                st.session_state.analysis_history.append({
                                    "type": "Key Elements",
                                    "document": uploaded_file.name if 'uploaded_file' in locals() else "Document",
                                    "result": str(result),
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                })
            
            elif analysis_type == "🏢 Entity Recognition":
                st.write("Identify and categorize names, organizations, locations, dates, and technical terms.")
                if st.button("Identify Entities", key="btn_entities"):
                    with st.spinner("Recognizing entities..."):
                        result = requests.post(
                            f"{BACKEND_URL}/analyze/entities",
                            data={"text": st.session_state.document_text}
                        ).json()
                    
                    if result:
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.subheader("🏢 Recognized Entities")
                            display_json(result)
                            
                            # Add to history
                            if "analysis_history" in st.session_state:
                                st.session_state.analysis_history.append({
                                    "type": "Entity Recognition",
                                    "document": uploaded_file.name if 'uploaded_file' in locals() else "Document",
                                    "result": str(result),
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                })
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with tab_compare:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📊 Document Comparison")
        st.write("Compare two documents to identify differences, additions, deletions, and thematic changes.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div style='background-color: #1a1f2c; padding: 15px; border-radius: 10px;'>", unsafe_allow_html=True)
            st.subheader("First Document")
            file1 = st.file_uploader(
                "Upload first document",
                type=SUPPORTED_TYPES,
                key="compare_file1"
            )
            if file1:
                st.success(f"Uploaded: {file1.name}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div style='background-color: #1a1f2c; padding: 15px; border-radius: 10px;'>", unsafe_allow_html=True)
            st.subheader("Second Document")
            file2 = st.file_uploader(
                "Upload second document",
                type=SUPPORTED_TYPES,
                key="compare_file2"
            )
            if file2:
                st.success(f"Uploaded: {file2.name}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        if file1 and file2:
            if st.button("Compare Documents", key="btn_compare"):
                with st.spinner("Analyzing differences..."):
                    # Get texts from both documents
                    result1 = handle_upload(file1)
                    result2 = handle_upload(file2)
                    
                    if result1 and result2:
                        text1 = result1.get("text", "")
                        text2 = result2.get("text", "")
                        
                        # Perform comparison
                        result = requests.post(
                            f"{BACKEND_URL}/compare",
                            data={
                                "text1": text1,
                                "text2": text2
                            }
                        ).json()
                        
                        if result:
                            st.markdown("<div style='background-color: #1a1f2c; padding: 20px; border-radius: 10px; border-left: 4px solid #3949ab;'>", unsafe_allow_html=True)
                            st.subheader("📊 Comparison Results")
                            comparison = result.get("comparison", "")
                            st.markdown(comparison)
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                            # Add to history
                            if "analysis_history" in st.session_state:
                                st.session_state.analysis_history.append({
                                    "type": "Document Comparison",
                                    "document": f"{file1.name} vs {file2.name}",
                                    "result": comparison,
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                })
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tab_history:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📚 Analysis History")
        
        if not st.session_state.analysis_history:
            st.info("No analysis has been performed yet. Your analysis results will appear here.")
        else:
            # Add a search box
            search = st.text_input("🔍 Search history:", "")
            
            # Filter history based on search
            filtered_history = st.session_state.analysis_history
            if search:
                filtered_history = [
                    h for h in st.session_state.analysis_history 
                    if search.lower() in str(h).lower()
                ]
            
            # Display history items
            for i, item in enumerate(reversed(filtered_history)):
                with st.expander(f"**{item['type']}** - {item['document']} ({item['timestamp']})", expanded=False):
                    st.markdown("<div style='background-color: #1a1f2c; padding: 15px; border-radius: 10px;'>", unsafe_allow_html=True)
                    
                    if item['type'] == "Question & Answer":
                        st.markdown(f"**Question:** {item['question']}")
                        st.markdown("**Answer:**")
                    
                    st.markdown(item['result'])
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # Clear history button
            if st.button("Clear History"):
                st.session_state.analysis_history = []
                st.experimental_rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()