#!/usr/bin/env python3
"""
SOP Parser - A command-line tool for extracting Standard Operating Procedures from PDFs
and converting them into Mermaid.js flowcharts.

This script reads a PDF file, extracts SOP text, parses it into structured steps,
and generates a Mermaid flowchart representation saved to a .mmd file.

Author: Expert Python Developer
Version: 1.0
Python: 3.9+
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install it with: pip install PyMuPDF")
    sys.exit(1)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file using PyMuPDF.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Concatenated text from all pages
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If the PDF is corrupted or cannot be read
    """
    try:
        # Check if file exists
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Open the PDF document
        doc = fitz.open(pdf_path)
        full_text = ""
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            full_text += page_text + "\n"
        
        doc.close()
        
        if not full_text.strip():
            raise Exception("No text content found in the PDF")
            
        return full_text
        
    except FileNotFoundError:
        raise
    except Exception as e:
        raise Exception(f"Error reading PDF file: {str(e)}")


def clean_sop_steps(text_lines: List[str]) -> List[str]:
    """
    Extract only the numbered SOP steps, ignoring everything else.
    This simplified approach focuses on finding actual numbered procedures.
    """
    full_text = "\n".join(text_lines)
    
    # Find all numbered steps (1., 2., 3., etc.)
    step_pattern = r'^\s*(\d+)\s*\.\s*(.+?)(?=^\s*\d+\s*\.|$)'
    steps = re.findall(step_pattern, full_text, re.MULTILINE | re.DOTALL)
    
    cleaned_steps = []
    for step_num, step_text in steps:
        # Clean up the step text
        clean_text = re.sub(r'\s+', ' ', step_text.strip())
        # Remove page breaks and artifacts
        clean_text = re.sub(r'Page \d+', '', clean_text)
        clean_text = re.sub(r'Corporate IT Infrastructure Manual', '', clean_text)
        clean_text = clean_text.strip()
        
        if clean_text and len(clean_text) > 10:  # Only keep substantial steps
            cleaned_steps.append(clean_text)
    
    return cleaned_steps


def parse_sop_to_flowchart_logic(sop_steps: List[str]) -> List[Dict]:
    """
    Create a simple, linear flowchart from SOP steps.
    This simplified version focuses on reliability over complexity.
    """
    if not sop_steps:
        return []

    nodes = []
    for i, step_text in enumerate(sop_steps):
        node_id = f'node{i}'
        text_lower = step_text.lower()

        # Determine node type based on keywords
        node_type = 'process'
        if any(keyword in text_lower for keyword in ['check', 'login', 'verify']):
            node_type = 'decision'
        elif any(keyword in text_lower for keyword in ['send out an e-mail', 'abort', 'fail']):
            node_type = 'failure'
        elif any(keyword in text_lower for keyword in ['success', 'completed']):
            node_type = 'success'
        
        # Create clean, short summary
        summary = step_text[:60] + '...' if len(step_text) > 60 else step_text
        
        nodes.append({
            'id': node_id,
            'text': summary,
            'type': node_type,
            'children': []
        })

    # Create simple linear connections
    for i in range(len(nodes) - 1):
        nodes[i]['children'].append({'target': nodes[i+1]['id'], 'label': ''})

    return nodes


def sanitize_for_mermaid(text: str) -> str:
    """Sanitize text to be safely used in a Mermaid node.
    - Encloses the text in double quotes.
    - Escapes internal double quotes.
    - Replaces newlines with <br> tags for multi-line text.
    """
    # Escape internal double quotes with their HTML entity equivalent
    sanitized = text.replace('"', '#quot;')
    # Replace newlines with Mermaid-compatible line breaks
    sanitized = sanitized.replace('\n', '<br>')
    # Enclose the entire string in double quotes
    return f'"{sanitized}"'

def generate_mermaid_code(flow_nodes: List[Dict]) -> str:
    """
    Generate Mermaid.js flowchart code from structured node data.
    
    Args:
        flow_nodes (List[Dict]): List of flowchart node dictionaries
        
    Returns:
        str: Complete Mermaid flowchart code
    """
    if not flow_nodes:
        return "graph TD;\n    A[No steps found]"
    
    # If we have too many nodes, limit them to prevent rendering issues
    if len(flow_nodes) > 20:
        flow_nodes = flow_nodes[:20]
    
    mermaid_lines = ["graph TD;"]
    
    # Generate node definitions and connections
    for i, node in enumerate(flow_nodes):
        node_id = node['id']
        
        node_text = sanitize_for_mermaid(node['text'])
 
        node_type = node['type']
        
        # Choose appropriate bracket style based on type
        if node_type == 'decision':
            node_def = f'    {node_id}{{{node_text}}}'
        elif node_type == 'process':
            node_def = f'    {node_id}[{node_text}]'
        elif node_type == 'failure':
            node_def = f'    {node_id}[{node_text}]'
        elif node_type == 'success':
            node_def = f'    {node_id}[{node_text}]'
        else:
            node_def = f'    {node_id}[{node_text}]'
        
        mermaid_lines.append(node_def)
        
        # Add connections to children with labels
        for connection in node.get('children', []):
            if connection.get('label'):
                mermaid_lines.append(f'    {node_id} -->|{connection["label"]}| {connection["target"]}')
            else:
                mermaid_lines.append(f'    {node_id} --> {connection["target"]}')
    
    # Add style definitions
    mermaid_lines.extend([
        "",
        "    %% Style definitions",
        "    classDef processStyle fill:#e0f2fe,stroke:#38bdf8",
        "    classDef decisionStyle fill:#fef9c3,stroke:#facc15",
        "    classDef failureStyle fill:#ffedd5,stroke:#fb923c",
        "    classDef successStyle fill:#dcfce7,stroke:#4ade80",
        ""
    ])
    
    # Apply styles to nodes
    for node in flow_nodes:
        node_id = node['id']
        node_type = node['type']
        
        if node_type == 'decision':
            mermaid_lines.append(f'    {node_id}:::decisionStyle')
        elif node_type == 'failure':
            mermaid_lines.append(f'    {node_id}:::failureStyle')
        elif node_type == 'success':
            mermaid_lines.append(f'    {node_id}:::successStyle')
        else:  # process
            mermaid_lines.append(f'    {node_id}:::processStyle')
    
    return '\n'.join(mermaid_lines)


def main():
    """
    Main execution function that orchestrates the SOP parsing and flowchart generation.
    """
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Extract SOP from PDF and convert to Mermaid flowchart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sop_parser.py document.pdf
  python sop_parser.py document.pdf -o my_flowchart.mmd
        """
    )
    
    parser.add_argument(
        'pdf_path',
        help='Path to the input PDF file containing the SOP'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output.mmd',
        help='Path for the output .mmd file (default: output.mmd)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        print(f"Processing PDF: {args.pdf_path}")
        
        # Step 1: Extract text from PDF
        print("Extracting text from PDF...")
        full_text = extract_text_from_pdf(args.pdf_path)
        
        # Step 2: Isolate SOP steps
        print("Isolating SOP steps...")
        sop_steps = isolate_sop_steps(full_text)
        
        if not sop_steps:
            print("Warning: No SOP steps found in the document")
            return
        
        print(f"Found {len(sop_steps)} SOP steps")
        
        # Step 3: Parse steps into flowchart logic
        print("Parsing steps into flowchart structure...")
        flow_nodes = parse_sop_to_flowchart_logic(sop_steps)
        
        # Step 4: Generate Mermaid code
        print("Generating Mermaid flowchart code...")
        mermaid_code = generate_mermaid_code(flow_nodes)
        
        # Step 5: Write to output file
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        
        print(f"Successfully generated flowchart at {output_path}")
        print(f"Generated {len(flow_nodes)} flowchart nodes")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
