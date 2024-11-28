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

# Add a root endpoint to serve index.html
@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Create a temporary file to store the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_path = temp_file.name  # Store the path for later use

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
        
        # Clean up the temporary file after we're done with it
        try:
            os.unlink(temp_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_path}: {e}")
        
        # Convert result to dict and return
        return result.to_dict()
    
    except Exception as e:
        # If any error occurs, attempt to clean up
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass
        raise e