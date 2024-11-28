import os
from collections import OrderedDict
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeOutputOption, AnalyzeResult
from dotenv import load_dotenv
import json
import nltk

# Ensure you have downloaded the punkt tokenizer
nltk.download('punkt')
from nltk.tokenize import sent_tokenize

load_dotenv()

ENDPOINT = os.environ["Azure_Doc_Endpoint"]
KEY = os.environ["Azure_Doc_Key"]

if not ENDPOINT or not KEY:
    raise ValueError("Azure_Doc_Endpoint and Azure_Doc_Key must be set in the environment variables.")

document_intelligence_client = DocumentIntelligenceClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))

def process_document(file_path):
    """Process a single document and return its hierarchy"""
    try:
        with open(file_path, "rb") as f:
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-layout",
                analyze_request=f,
                output=[AnalyzeOutputOption.FIGURES],
                content_type="application/octet-stream",
            )
        result: AnalyzeResult = poller.result()
        operation_id = poller.details["operation_id"]

        # Initialize OrderedDict for the document
        document_hierarchy = OrderedDict()
        filename = os.path.basename(file_path)
        document_hierarchy['Document'] = filename
        document_hierarchy['Sections'] = []

        if result.paragraphs:
            # Sort paragraphs by their span's offset to maintain order
            sorted_paragraphs = sorted(result.paragraphs, key=lambda p: p.spans[0].offset)

            current_section = None

            for paragraph in sorted_paragraphs:
                content = paragraph.content.strip()
                role = paragraph.role.lower() if paragraph.role else "body"

                # Determine if the paragraph is a Title/Subtitle
                if role.lower() in ['title', 'subtitle', 'heading', 'header']:
                    # Start a new section
                    current_section = OrderedDict()
                    current_section['Title'] = content
                    current_section['Paragraphs'] = []
                    document_hierarchy['Sections'].append(current_section)
                else:
                    if current_section is None: # If no section exists, create a default one
                        current_section = OrderedDict()
                        current_section['Title'] = "Untitled Section"
                        current_section['Paragraphs'] = []
                        document_hierarchy['Sections'].append(current_section)

                    # Split paragraph into sentences through nltk
                    sentences = sent_tokenize(content)
                    paragraph_dict = {
                        'Paragraph': content,
                        'Sentences': sentences
                    }
                    current_section['Paragraphs'].append(paragraph_dict)

        return document_hierarchy

    except PermissionError:
        print(f"Permission denied: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")
        return None

def save_hierarchy_to_json(hierarchy, output_path):
    """Save the document hierarchy to a JSON file"""
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(hierarchy, json_file, ensure_ascii=False, indent=4)
    print(f"Document hierarchy has been saved to {output_path}")

# Example usage:
# file_path = "sample_documents\2408.07055v1.pdf"
# hierarchy = process_document(file_path)
# if hierarchy:
#    save_hierarchy_to_json(hierarchy, "output.json")