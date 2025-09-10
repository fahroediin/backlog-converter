import os
from flask import Flask, render_template, request, jsonify
from backlog_processor import BacklogProcessor
from google.api_core import exceptions as google_exceptions
import pandas as pd

app = Flask(__name__)

# Rute utama sekarang hanya untuk menampilkan halaman awal
@app.route('/')
def index():
    return render_template('index.html')

# Rute BARU untuk memproses data via AJAX
@app.route('/process', methods=['POST'])
def process_backlog():
    data = request.get_json()
    raw_backlog = data.get('backlog_text')
    api_key = data.get('api_key')

    if not api_key or not api_key.strip():
        return jsonify({'error': "API Key tidak boleh kosong."}), 400
    
    if not raw_backlog or not raw_backlog.strip():
        return jsonify({'error': "Area teks backlog tidak boleh kosong."}), 400

    try:
        processor = BacklogProcessor(api_key=api_key)
        result_df = processor.run_with_text(raw_text=raw_backlog)
        
        if result_df is not None and not result_df.empty:
            # Siapkan data untuk dikirim sebagai JSON
            headers = result_df.columns.tolist()
            rows = result_df.values.tolist()
            tsv_data = result_df.to_csv(sep='\t', index=False)
            
            return jsonify({
                'success': True,
                'headers': headers,
                'rows': rows,
                'tsv_data': tsv_data
            })
        else:
            return jsonify({'error': "Gagal memproses backlog. Respons dari AI tidak dapat diurai."}), 500

    except google_exceptions.ResourceExhausted as e:
        error_message = "Error: Anda telah mencapai batas kuota API. Solusi: Coba lagi nanti, gunakan backlog lebih pendek, atau aktifkan penagihan di Google Cloud."
        return jsonify({'error': error_message}), 429
    except Exception as e:
        print(f"Error di aplikasi Flask: {e}")
        return jsonify({'error': f"Terjadi error internal: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)