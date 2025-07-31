#!/usr/bin/env python3
"""
Flask web application for SOP Parser with frontend interface.
Provides a web UI for uploading PDFs and generating Mermaid flowcharts.
"""

import os
import tempfile
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import json

# Import our SOP parser functions
from sop_parser import (
    extract_text_from_pdf,
    clean_sop_steps,
    parse_sop_to_flowchart_logic,
    generate_mermaid_code
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store processing results temporarily
processing_results = {}


@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """
    Handle PDF file upload and process it into a Mermaid flowchart.
    
    Returns:
        JSON response with processing results or error message
    """
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Generate unique ID for this processing session
        session_id = str(uuid.uuid4())
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(temp_path)
        
        try:
            # Process the PDF
            print(f"Processing PDF: {filename}")
            
            # Step 1: Extract text from PDF
            full_text = extract_text_from_pdf(temp_path)
            text_lines = full_text.split('\n')
            
            # Step 2: Isolate SOP steps
            sop_steps = clean_sop_steps(text_lines)
            
            if not sop_steps:
                return jsonify({
                    'error': 'No SOP steps found in the document. Please ensure the PDF contains a structured procedure.'
                }), 400
            
            # Step 3: Parse steps into flowchart logic
            flow_nodes = parse_sop_to_flowchart_logic(sop_steps)
            
            # Step 4: Generate Mermaid code
            mermaid_code = generate_mermaid_code(flow_nodes)
            
            # Store results
            processing_results[session_id] = {
                'filename': filename,
                'sop_steps': sop_steps,
                'flow_nodes': flow_nodes,
                'mermaid_code': mermaid_code,
                'stats': {
                    'total_steps': len(sop_steps),
                    'process_nodes': len([n for n in flow_nodes if n['type'] == 'process']),
                    'decision_nodes': len([n for n in flow_nodes if n['type'] == 'decision']),
                    'failure_nodes': len([n for n in flow_nodes if n['type'] == 'failure']),
                    'success_nodes': len([n for n in flow_nodes if n['type'] == 'success'])
                }
            }
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'filename': filename,
                'mermaid_code': mermaid_code,
                'stats': processing_results[session_id]['stats'],
                'steps_preview': sop_steps[:5]  # First 5 steps for preview
            })
            
        finally:
            # Clean up uploaded file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/download/<session_id>')
def download_mermaid(session_id):
    """
    Download the generated Mermaid file for a session.
    
    Args:
        session_id (str): The session ID for the processed file
        
    Returns:
        File download response or error
    """
    if session_id not in processing_results:
        return jsonify({'error': 'Session not found or expired'}), 404
    
    try:
        result = processing_results[session_id]
        
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
            f.write(result['mermaid_code'])
            temp_file_path = f.name
        
        # Generate download filename
        base_name = Path(result['filename']).stem
        download_filename = f"{base_name}_flowchart.mmd"
        
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/api/steps/<session_id>')
def get_steps(session_id):
    """
    Get the full list of extracted SOP steps for a session.
    
    Args:
        session_id (str): The session ID for the processed file
        
    Returns:
        JSON response with step details
    """
    if session_id not in processing_results:
        return jsonify({'error': 'Session not found or expired'}), 404
    
    result = processing_results[session_id]
    return jsonify({
        'steps': result['sop_steps'],
        'flow_nodes': result['flow_nodes'],
        'stats': result['stats']
    })


@app.route('/api/debug/<session_id>')
def debug_mermaid(session_id):
    """
    Debug endpoint to see the generated Mermaid code.
    
    Args:
        session_id (str): The session ID for the processed file
        
    Returns:
        JSON response with debug information
    """
    if session_id not in processing_results:
        return jsonify({'error': 'Session not found or expired'}), 404
    
    result = processing_results[session_id]
    return jsonify({
        'mermaid_code': result['mermaid_code'],
        'flow_nodes': result['flow_nodes'],
        'filename': result['filename']
    })


@app.errorhandler(413)
def file_too_large(e):
    """Handle file size limit exceeded."""
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413


@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error occurred.'}), 500


if __name__ == '__main__':
    print("Starting SOP Parser Web Application...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
