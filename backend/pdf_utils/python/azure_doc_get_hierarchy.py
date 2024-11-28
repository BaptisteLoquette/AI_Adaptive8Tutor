import json  # Added for JSON serialization
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import requests
import os
#import Pydantic
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import tempfile
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("Azure_Doc_Endpoint")
KEY = os.getenv("Azure_Doc_Key")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the absolute path to the frontend directory
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "frontend")

# Mount static files
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

def process_document_structure(result):
    """Process document into hierarchical structure with titles and paragraphs."""
    document_structure = {}
    current_title = "Untitled Section"  # Default section for content without a title
    current_paragraphs = []
    
    # Use paragraphs, sorted by the y-coordinate of the top-left corner of the bounding box
    try:
        paragraphs = sorted(
            result.paragraphs,
            key=lambda x: x.bounding_box[0][1] if hasattr(x, 'bounding_box') and x.bounding_box else 0
        )
    except AttributeError as e:
        print(f"Error accessing bounding_box: {e}")
        return document_structure
    
    for paragraph in paragraphs:
        content = paragraph.content.strip()
        if not content:
            continue
        
        # Debug: Print the content and bounding box
        print(f"Processing paragraph: '{content}' with bounding_box: {getattr(paragraph, 'bounding_box', 'N/A')}")
        
        # Identify titles by their appearance or heuristics
        is_title = (
            len(content) < 100 and (
                content.endswith(':') or  # Simple heuristic
                getattr(paragraph, 'role', None) == "title"
            )
        )
        
        if is_title:
            # If we have content for the previous title, save it
            if current_paragraphs:
                if current_title not in document_structure:
                    document_structure[current_title] = {}
                document_structure[current_title][f"paragraph-{len(document_structure[current_title]) + 1}"] = current_paragraphs
                current_paragraphs = []
            
            current_title = content
            print(f"Identified as title: '{current_title}'")
        else:
            current_paragraphs.append(content)
            print(f"Added to current paragraph list under '{current_title}': '{content}'")
    
    # Don't forget to save the last section
    if current_paragraphs:
        if current_title not in document_structure:
            document_structure[current_title] = {}
        document_structure[current_title][f"paragraph-{len(document_structure[current_title]) + 1}"] = current_paragraphs
        print(f"Saved last section under '{current_title}'")
    
    return document_structure

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Create a temporary file to store the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_path = temp_file.name

        # Initialize Document Analysis Client
        document_analysis_client = DocumentAnalysisClient(
            endpoint=ENDPOINT, credential=AzureKeyCredential(KEY)
        )
        
        # Analyze the document
        with open(temp_path, 'rb') as doc:
            poller = document_analysis_client.begin_analyze_document(
                "prebuilt-layout", doc
            )
            result = poller.result()
        
        # Process the document into the desired structure
        document_hierarchy = process_document_structure(result)
        
        # Clean up the temporary file
        try:
            os.unlink(temp_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_path}: {e}")
        
        return document_hierarchy
    
    except Exception as e:
        # If any error occurs, attempt to clean up
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass
        raise e