#!/usr/bin/env python3
"""
Vercel-compatible API endpoint for SOP to Flowchart converter
"""

import os
import sys
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import uuid

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sop_parser import (
    extract_text_from_pdf,
    clean_sop_steps,
    parse_sop_to_flowchart_logic,
    generate_mermaid_code
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store for session data (in production, use a proper database)
sessions = {}

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('../static', 'index.html')

@app.route('/api/process', methods=['POST'])
def process_pdf():
    """Process uploaded PDF and generate Mermaid flowchart"""
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
        # Create a temporary file to store the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
            file.save(temp_path)
        
        try:
            # Step 1: Extract text from PDF
            full_text = extract_text_from_pdf(temp_path)
            text_lines = full_text.split('\n')
            
            # Step 2: Isolate SOP steps
            sop_steps = clean_sop_steps(text_lines)
            
            if not sop_steps:
                return jsonify({
                    'error': 'No SOP steps found in the PDF. Please ensure the document contains numbered steps (1., 2., 3., etc.)'
                }), 400
            
            # Step 3: Parse into flowchart logic
            flow_nodes = parse_sop_to_flowchart_logic(sop_steps)
            
            if not flow_nodes:
                return jsonify({
                    'error': 'Could not parse SOP steps into flowchart nodes'
                }), 400
            
            # Step 4: Generate Mermaid code
            mermaid_code = generate_mermaid_code(flow_nodes)
            
            # Create session for debugging
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'sop_steps': sop_steps,
                'flow_nodes': flow_nodes,
                'mermaid_code': mermaid_code
            }
            
            return jsonify({
                'success': True,
                'mermaid_code': mermaid_code,
                'session_id': session_id,
                'steps_found': len(sop_steps)
            })
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/debug/<session_id>')
def debug_session(session_id):
    """Debug endpoint to view session data"""
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(sessions[session_id])

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda status, headers: None)

if __name__ == '__main__':
    app.run(debug=True)
