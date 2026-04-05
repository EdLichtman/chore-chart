"""
Chore Management Flask API
Minimal backend for Phase 1: PDF generation on import
"""

import json
from datetime import datetime
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from jsonschema import validate, ValidationError
import io

from pdf_generator import PDFGenerator
from schema import CHORE_SCHEMA

app = Flask(__name__)
CORS(app)

pdf_generator = PDFGenerator()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/chores/import', methods=['POST'])
def import_chores():
    """
    Import a chores.json file and generate a PDF for the current week.

    Expected payload: JSON body with { "chores": [...] }
    Returns: PDF file
    """
    try:
        data = request.get_json()

        # Validate schema
        validate(instance=data, schema=CHORE_SCHEMA)

        # Generate PDF
        pdf_bytes = pdf_generator.generate_pdf(data['chores'])

        # Return PDF as downloadable file
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"chores-{datetime.now().strftime('%Y%m%d')}.pdf"
        )

    except ValidationError as e:
        return jsonify({'error': f'Invalid chore file: {e.message}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/chores/validate', methods=['POST'])
def validate_chores():
    """
    Validate a chores.json file against the schema.

    Expected payload: JSON body with { "chores": [...] }
    Returns: { "valid": true } or error message
    """
    try:
        data = request.get_json()
        validate(instance=data, schema=CHORE_SCHEMA)
        return jsonify({'valid': True, 'count': len(data.get('chores', []))})
    except ValidationError as e:
        return jsonify({'valid': False, 'error': e.message}), 400
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
