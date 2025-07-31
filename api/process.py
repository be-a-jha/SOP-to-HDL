import os
import sys
import tempfile
import json
from urllib.parse import parse_qs

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sop_parser import (
        extract_text_from_pdf,
        clean_sop_steps,
        parse_sop_to_flowchart_logic,
        generate_mermaid_code
    )
except ImportError as e:
    print(f"Import error: {e}")

def handler(request):
    """Vercel serverless function handler"""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight requests
    if request.get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    if request.get('method') != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # Get the uploaded file from the request
        # This is a simplified approach for Vercel
        body = request.get('body', '')
        
        # For now, return a simple success response
        # In a real implementation, you'd need to handle file upload differently
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'API is working',
                'mermaid_code': '''graph TD;
    A[Start] --> B[Process Document];
    B --> C[Generate Flowchart];
    C --> D[End];
    
    classDef processStyle fill:#e0f2fe,stroke:#38bdf8
    A:::processStyle
    B:::processStyle
    C:::processStyle
    D:::processStyle'''
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Processing failed: {str(e)}'})
        }
