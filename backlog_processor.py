import os
import pandas as pd
import io
import google.generativeai as genai
import re

# --- FUNGSI BARU UNTUK MENERJEMAHKAN TANGGAL ---
def convert_indonesian_date(date_str: str) -> str | None:
    """Menerjemahkan string tanggal bahasa Indonesia (e.g., '2 Juni 2025') ke format bahasa Inggris."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None

    month_map_id_to_en = {
        'januari': 'January', 'februari': 'February', 'maret': 'March',
        'april': 'April', 'mei': 'May', 'juni': 'June',
        'juli': 'July', 'agustus': 'August', 'september': 'September',
        'oktober': 'October', 'november': 'November', 'desember': 'December'
    }
    
    try:
        parts = date_str.lower().split()
        if len(parts) == 3:
            day, month_id, year = parts
            month_en = month_map_id_to_en.get(month_id)
            if month_en:
                return f"{day} {month_en} {year}"
    except Exception:
        pass # Jika ada error, kembalikan None
    
    return None # Kembalikan None jika format tidak cocok

class BacklogProcessor:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key tidak ditemukan.")
        genai.configure(api_key=api_key)

    def _create_prompt(self, raw_backlog_text: str) -> str:
        prompt = f"""
        Anda adalah seorang Agile Project Manager yang sangat ahli dalam melakukan backlog grooming.
        Tugas Anda adalah menganalisis daftar backlog mentah berikut dan mengelompokkannya ke dalam Epic yang logis dan spesifik.

        FORMAT INPUT:
        Setiap baris dalam backlog mentah memiliki format yang dipisahkan oleh karakter TAB.
        Formatnya adalah: Backlog<TAB>PIC<TAB>Status<TAB>Start Date<TAB>End Date.
        Penting untuk Anda mengenali bahwa pemisah antar kolom adalah TAB.

        ATURAN PENTING:
        1.  **Identifikasi Epic**: Berdasarkan deskripsi 'Backlog', tentukan nama Epic yang paling relevan.
        2.  **Ekstraksi Akurat**: Ekstrak SEMUA kolom dari input (Backlog, PIC, Status, Start Date, End Date) dengan benar. JANGAN sampai ada kolom yang hilang atau kosong jika datanya ada di input.
        3.  **Format Output**: Hasil akhir HARUS berupa teks dengan format CSV, menggunakan pemisah pipa '|'. Jangan tambahkan teks pembuka atau penutup apa pun, hanya data CSV murni.
        4.  **Kolom Output**: Urutan kolom harus persis seperti ini: Epic|Backlog|PIC|Status|Start Date|End Date

        Berikut adalah daftar backlog mentah yang harus Anda proses:
        --- BACKLOG MENTAH ---
        {raw_backlog_text}
        --- AKHIR BACKLOG MENTAH ---

        Sekarang, proses backlog di atas dan hasilkan output dalam format CSV dengan pemisah pipa '|' sesuai aturan. Pastikan semua kolom terisi dengan benar.
        """
        return prompt

    def process_with_llm(self, raw_backlog_text: str) -> str:
        prompt = self._create_prompt(raw_backlog_text)
        print("Mengirim permintaan ke Google Gemini...")
        try:
            model = genai.GenerativeModel('gemini-2.5-flash') 
            generation_config = {"temperature": 0.1}
            safety_settings = {'HATE': 'block_none', 'HARASSMENT': 'block_none', 'SEXUAL' : 'block_none', 'DANGEROUS' : 'block_none'}
            response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
            print("Respons dari Gemini diterima.")
            return response.text.strip()
        except Exception as e:
            print(f"Terjadi error saat menghubungi API Gemini: {e}")
            return ""

    def _parse_llm_response(self, llm_response: str) -> pd.DataFrame:
        if not llm_response:
            print("Respons LLM kosong, tidak ada yang bisa diurai.")
            return pd.DataFrame()
        cleaned_response = re.sub(r'```(csv)?', '', llm_response)
        lines = cleaned_response.strip().split('\n')
        data_lines = [line.strip() for line in lines if '|' in line]
        if not data_lines:
            print("Tidak ada baris data valid (dengan pemisah '|') yang ditemukan dalam respons LLM.")
            return pd.DataFrame()
        csv_data_to_parse = "\n".join(data_lines)
        data = io.StringIO(csv_data_to_parse)
        header_str = "Epic|Backlog|PIC|Status|Start Date|End Date"
        expected_columns = header_str.split('|')
        try:
            first_line_is_header = all(col.strip() in data_lines[0] for col in ['Epic', 'Backlog', 'PIC'])
            if first_line_is_header:
                df = pd.read_csv(data, sep='|')
            else:
                print("Header tidak ditemukan di respons. Menambahkan header secara manual.")
                df = pd.read_csv(data, sep='|', header=None, names=expected_columns)
            if len(df.columns) != len(expected_columns):
                raise ValueError(f"Jumlah kolom tidak cocok. Diharapkan {len(expected_columns)}, didapat {len(df.columns)}")
            df.columns = [col.strip() for col in expected_columns]
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
            print("Respons LLM berhasil diurai menjadi tabel.")
            return df
        except Exception as e:
            print(f"Gagal mengurai respons LLM. Error: {e}")
            return pd.DataFrame()

    def run_with_text(self, raw_text: str) -> pd.DataFrame | None:
        llm_result = self.process_with_llm(raw_text)
        if not llm_result: return None
        structured_data = self._parse_llm_response(llm_result)
        if structured_data.empty: return None
        
        # --- LOGIKA PENANGANAN TANGGAL YANG DIPERBAIKI TOTAL ---

        # 1. Terapkan fungsi penerjemah ke kolom tanggal
        if 'Start Date' in structured_data.columns:
            structured_data['Start Date'] = structured_data['Start Date'].apply(convert_indonesian_date)
        if 'End Date' in structured_data.columns:
            structured_data['End Date'] = structured_data['End Date'].apply(convert_indonesian_date)

        # 2. Sekarang konversi ke datetime, ini seharusnya berhasil tanpa warning
        if 'Start Date' in structured_data.columns:
            structured_data['Start Date'] = pd.to_datetime(structured_data['Start Date'], errors='coerce')
        if 'End Date' in structured_data.columns:
            structured_data['End Date'] = pd.to_datetime(structured_data['End Date'], errors='coerce')

        # 3. Urutkan data
        structured_data = structured_data.sort_values(by=['Epic', 'Start Date'], ascending=[True, True], na_position='last')
        
        # 4. Ganti nilai kosong dengan string ''
        structured_data.fillna('', inplace=True)

        # 5. Format tanggal untuk ditampilkan
        if 'Start Date' in structured_data.columns:
            structured_data['Start Date'] = structured_data['Start Date'].apply(lambda x: x.strftime('%d %B %Y') if pd.notna(x) and x != '' else '')
        if 'End Date' in structured_data.columns:
            structured_data['End Date'] = structured_data['End Date'].apply(lambda x: x.strftime('%d %B %Y') if pd.notna(x) and x != '' else '')

        return structured_data