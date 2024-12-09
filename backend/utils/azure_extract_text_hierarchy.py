from collections import OrderedDict
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import tempfile
from azure.core.exceptions import HttpResponseError

from backend.utils.azure_doc_utils import process_image_document

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
frontend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "frontend"
)

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are supported.")

    try:
        # Create a temporary file to store the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_path = temp_file.name

            global_hierarchy = []
            hierarchy = process_image_document(temp_path)

            if hierarchy:
                return hierarchy
        
        #return document_hierarchy
    
    except HttpResponseError as e:
        # Specific handling for Azure HTTP response errors
        print(f"Azure HTTP Response Error: {e}")
        raise HTTPException(status_code=500, detail=f"Azure Error: {e.message}")
    except Exception as e:
        # General error handling
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))