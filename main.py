# backlog-converter/main.py
import os
from dotenv import load_dotenv
from backlog_processor import BacklogProcessor

def main():
    """
    Fungsi utama untuk menjalankan aplikasi converter backlog.
    """
    load_dotenv()
    
    # Mengambil API Key Google dari environment
    api_key = os.getenv("GOOGLE_API_KEY")
    
    input_file = "raw_backlog.txt"
    output_file = "processed_backlog_gemini.csv" # Nama file output diubah agar tidak menimpa hasil lama
    
    try:
        processor = BacklogProcessor(api_key=api_key)
        processor.run(input_filepath=input_file, output_filepath=output_file)
    except ValueError as e:
        print(f"Error Inisialisasi: {e}")
    except Exception as e:
        print(f"Terjadi error yang tidak terduga: {e}")

if __name__ == "__main__":
    main()