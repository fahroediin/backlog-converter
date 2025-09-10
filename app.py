# backlog-converter/app.py
import os
from flask import Flask, render_template, request
from backlog_processor import BacklogProcessor
from google.api_core import exceptions as google_exceptions
import pandas as pd

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        raw_backlog = request.form.get('backlog_text')
        api_key = request.form.get('api_key')
        
        if not api_key or not api_key.strip():
            return render_template('index.html', error="API Key tidak boleh kosong.")
        
        if not raw_backlog or not raw_backlog.strip():
            return render_template('index.html', error="Area teks backlog tidak boleh kosong.")

        try:
            processor = BacklogProcessor(api_key=api_key)
            result_df = processor.run_with_text(raw_text=raw_backlog)
            
            if result_df is not None and not result_df.empty:
                # Siapkan data untuk ditampilkan di tabel HTML
                headers = result_df.columns.tolist()
                rows = result_df.values.tolist()
                
                # Siapkan data untuk disalin (format Tab)
                tsv_data = result_df.to_csv(sep='\t', index=False)
                
                return render_template('index.html', headers=headers, rows=rows, tsv_data=tsv_data)
            else:
                return render_template('index.html', error="Gagal memproses backlog. Respons dari AI tidak dapat diurai. Cek terminal server untuk detail.")

        except google_exceptions.ResourceExhausted as e:
            error_message = "Error: Anda telah mencapai batas kuota API. Solusi: Coba lagi nanti, gunakan backlog lebih pendek, atau aktifkan penagihan di Google Cloud."
            return render_template('index.html', error=error_message)
        except Exception as e:
            return render_template('index.html', error=f"Terjadi error: {e}")

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)