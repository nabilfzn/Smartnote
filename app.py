import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import tempfile
import re
import json
import uuid
from fpdf import FPDF
import base64
import time
import requests
import pandas as pd
import datetime
from io import BytesIO
from dashboard import microfon

# Load environment variables
load_dotenv()

# Konfigurasi API Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FLASK_SERVER_URL = os.getenv("FLASK_SERVER")
print("FLASK_SERVER_URL:", FLASK_SERVER_URL)

genai.configure(api_key=GOOGLE_API_KEY)

# Inisialisasi session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'quizzes' not in st.session_state:
    st.session_state.quizzes = {}
if 'user_type' not in st.session_state:
    st.session_state.user_type = None

# Fungsi untuk audio summarize
def summarize(audio_file_path):
    audio_file = genai.upload_file(path=audio_file_path)
    model_summarize = genai.GenerativeModel(
        model_name="gemini-2.0-flash-thinking-exp-01-21",
        generation_config={
            'temperature': 0.0,
            'top_p': 1.0,
            'top_k': 0
        }
    )
    response = model_summarize.generate_content([
        {"role": "user", "parts": ["ringkas audio ini dan berikan poin poin penting yang harus diketahui"]},
        {"role": "user", "parts": [audio_file]}
    ])
    return response.text

# Fungsi untuk membuat modul    
def modul(audio_file_path):
    audio_file = genai.upload_file(path=audio_file_path)
    
    model_modul = genai.GenerativeModel(
        model_name="gemini-2.0-flash-thinking-exp-01-21",
        generation_config={
            'max_output_tokens': 300000,
            'temperature': 0.2,
            'top_p': 1.0,
            'top_k': 0
        }
    )

    response = model_modul.generate_content([
        """
        Buatkan modul pelajaran yang lengkap dan terstruktur berdasarkan isi audio berikut.

        Kriteria:
        - Gunakan gaya bahasa buku pelajaran.
        - Sertakan struktur:
          1. Pendahuluan
          2. Materi
             2.1 Bab 1
             2.2 Bab 2
             ...
        - Gunakan paragraf panjang dan penjelasan mendalam.
        - Tidak perlu diringkas, tapi jelaskan rinci.
        - jangan ada kalimat pembuka darimu langsung subheading modul
        """,
        audio_file
    ])

    return response.text

# Fungsi untuk menyimpan file yang diupload
def save_uploaded_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    
    except Exception as e:
        st.error(f'Kesalahan saat upload file {e}')
        return None

def generate_quiz(material, difficulty="Medium", num_questions=5):
    # Inisialisasi model generatif
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-thinking-exp-01-21",  # Ganti dengan model yang sesuai
        generation_config={
            "temperature": 0.05,
            "max_output_tokens": 100000
        }
    )
    
    # Membuat prompt
    prompt = f"""
    Buat {num_questions} soal kuis pilihan ganda berdasarkan teks berikut:
    ---
    {material}
    ---
    **Format Output (HARUS JSON):**
    {{
        "quiz": [
            {{
                "question": "pertanyaan",
                "options": {{
                    "a": "teks opsi a",
                    "b": "teks opsi b", 
                    "c": "teks opsi c",
                    "d": "teks opsi d"
                }},
                "correct_answer": "a",  # Pilih dari a/b/c/d
                "correct_text": "teks opsi a",  # Teks jawaban benar yang sesuai dengan salah satu opsi
                "explanation": "penjelasan terkait jawaban benar"
            }}
        ]
    }}
    **Aturan:**
    1. Tingkat kesulitan: {difficulty}
    2. Pastikan 'correct_text' sama persis dengan salah satu opsi
    3. Format output HARUS JSON dan valid, tanpa komentar atau teks tambahan
    """
    
    # Generate content menggunakan model
    response = model.generate_content(prompt)
    
    # Tampilkan response untuk debugging
    print("Response dari model:", response.text)
    
    try:
        # Ambil hanya bagian JSON valid dari response
        json_str = re.search(r'\{[\s\S]*\}', response.text)
        
        # Pastikan kita menemukan JSON yang valid
        if json_str:
            json_str = json_str.group()
            quiz_data = json.loads(json_str)
        else:
            raise ValueError("Tidak ditemukan format JSON yang valid dalam response.")
        
        # Validasi data kuis
        for question in quiz_data["quiz"]:
            if question["correct_answer"] not in ['a', 'b', 'c', 'd']:
                raise ValueError("Jawaban benar harus salah satu dari opsi: a, b, c, d")
            if question["correct_text"] != question["options"].get(question["correct_answer"]):
                raise ValueError("Teks jawaban benar tidak cocok dengan opsi yang dipilih")
        
        return quiz_data
    
    except (json.JSONDecodeError, AttributeError) as e:
        raise ValueError("Format JSON tidak valid atau tidak ditemukan dalam response.") from e
    except Exception as e:
        raise ValueError(f"Terjadi kesalahan: {str(e)}") from e

# Fungsi untuk membuat quiz code
def create_quiz_code():
    # Membuat kode quiz yang unik
    return str(uuid.uuid4())[:8]

# Fungsi untuk sidebar navigasi
def render_sidebar():
    with st.sidebar:
        st.title("Smart Classroom")
        
        # User type selection
        if st.session_state.user_type is None:
            st.header("Pilih Jenis Pengguna")
            if st.button("Guru"):
                st.session_state.user_type = "teacher"
                st.rerun()
            if st.button("Siswa"):
                st.session_state.user_type = "student"
                st.rerun()
        else:
            st.write(f"Mode: **{st.session_state.user_type.capitalize()}**")
            
            # Menu navigation
            if st.session_state.user_type == "teacher":
                st.header("Menu")
                if st.button("Home"):
                    st.session_state.current_page = 'home'
                    st.rerun()
                if st.button("Audio to Materi"):
                    st.session_state.current_page = 'audio_to_materi'
                    st.rerun()
                if st.button("Quiz Generator"):
                    st.session_state.current_page = 'quiz_generator'
                    st.rerun()
                if st.button("Daftar Quiz"):
                    st.session_state.current_page = 'quiz_list'
                    st.rerun()
                if st.button("Rekam Materi"):
                    st.session_state.current_page = 'microfon'
            elif st.session_state.user_type == "student":
                st.header("Menu")
                if st.button("Home"):
                    st.session_state.current_page = 'home'
                    st.rerun()
                if st.button("Kerjakan Quiz"):
                    st.session_state.current_page = 'take_quiz'
                    st.rerun()
            
            # Reset user type
            if st.button("Ganti Pengguna"):
                st.session_state.user_type = None
                st.rerun()

# Halaman Home
def render_home():
    st.title("Smart Classroom")
    
    if st.session_state.user_type == "teacher":
        st.write("""
        ## Selamat Datang, Guru!
        
        Aplikasi Smart Classroom menyediakan alat untuk meningkatkan efektivitas pembelajaran:
        
        1. **Audio to Materi** - Rekam penjelasan Anda dan ubah menjadi ringkasan dan modul lengkap
        2. **Quiz Generator** - Buat quiz berdasarkan materi yang Anda buat
        3. **Daftar Quiz** - Kelola quiz yang telah Anda buat
        
        Gunakan menu di sidebar untuk navigasi.
        """)
    elif st.session_state.user_type == "student":
        st.write("""
        ## Selamat Datang, Siswa!
        
        Aplikasi Smart Classroom membantu Anda dalam pembelajaran:
        
        1. **Kerjakan Quiz** - Masukkan kode quiz dari guru untuk mengerjakan soal-soal
        
        Gunakan menu di sidebar untuk navigasi.
        """)
    else:
        st.write("""
        ## Selamat Datang di Smart Classroom!
        
        Pilih jenis pengguna pada sidebar untuk memulai.
        """)

# Halaman Audio to Materi
def render_audio_to_materi():
    st.title("Audio to Materi")
    st.write("Upload rekaman audio untuk diubah menjadi ringkasan dan modul")

    audio_file = None

    # Cek apakah datang dari halaman recording
    if st.session_state.get('from_recording', False) and 'selected_audio_file' in st.session_state:
        try:
            # Ambil file dari server
            selected_audio_file = st.session_state['selected_audio_file']
            audio_url = f"{FLASK_SERVER_URL}/uploads/{selected_audio_file}"
            audio_content = requests.get(audio_url).content

            # Simpan file sementara
            temp_audio_path = f"temp_{selected_audio_file}"
            with open(temp_audio_path, 'wb') as f:
                f.write(audio_content)

            audio_path = temp_audio_path
            st.audio(audio_url)

            st.success(f"Berhasil memuat audio: {selected_audio_file}")
            st.session_state['from_recording'] = False

        except Exception as e:
            st.error(f"Gagal memuat audio dari server: {str(e)}")
            return

    else:
        # Fitur drag & drop tetap aktif
        audio_file = st.file_uploader("Upload penjelasan materi", type=['wav', 'mp3'])
        if audio_file is not None:
            audio_path = save_uploaded_file(audio_file)
            st.audio(audio_path)

    # Mulai rangkum jika audio_path ada
    if 'audio_path' not in locals() and 'audio_path' in st.session_state:
        audio_path = st.session_state['audio_path']  # backup untuk rerun

    if 'audio_path' in locals():
        if st.button('Summarize audio'):
            with st.spinner('Merangkum Materi...'):
                summary = summarize(audio_path)
                st.session_state['summary'] = summary
                st.session_state['audio_path'] = audio_path
                st.session_state['tampilkan_tombol_modul'] = True

        if 'summary' in st.session_state:
            st.subheader("Ringkasan")
            st.info(st.session_state['summary'])

        if st.session_state.get('tampilkan_tombol_modul', False):
            if st.button('Buat Modul'):
                with st.spinner('Membuat Modul...'):
                    modul_text = modul(audio_path)
                    st.session_state['modul_text'] = modul_text
                    st.subheader("Modul")
                    st.info(modul_text)

        if 'modul_text' in st.session_state:
            if st.button("Buat Quiz"):
                st.session_state.current_page = 'quiz_generator'
                st.session_state.from_modul = True
                st.rerun()




# Halaman Quiz Generator
def render_quiz_generator():
    st.title("Quiz Generator")
    st.write("Buat kuis berdasarkan materi")
    
    # Jika datang dari halaman modul, gunakan materi yang sudah dibuat
    if st.session_state.get('from_modul', False) and 'modul_text' in st.session_state:
        user_material = st.text_area("**Materi:**", value=st.session_state['modul_text'], height=200)
        st.session_state.from_modul = False
    else:
        user_material = st.text_area("**Materi:**", height=200, placeholder="Paste teks materi di sini...")
    
    difficulty = st.selectbox("**Tingkat Kesulitan:**", ["Easy", "Medium", "Hard"])
    num_questions = st.slider("**Jumlah Soal:**", 1, 10, 5)
    
    if st.button("Generate Quiz") and user_material:
        with st.spinner("Membuat kuis..."):
            try:
                quiz_data = generate_quiz(user_material, difficulty, num_questions)
                
                # Buat kode quiz unik
                quiz_code = create_quiz_code()
                
                # Simpan quiz dalam session state
                st.session_state.quizzes[quiz_code] = {
                    "data": quiz_data,
                    "material": user_material,
                    "difficulty": difficulty,
                    "num_questions": num_questions,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.current_quiz = quiz_code
                st.session_state.current_page = 'view_quiz'
                st.success("Quiz berhasil dibuat!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}\n\nCoba generate lagi.")

# Halaman View Quiz (Tampilan Guru)
def render_view_quiz():
    if 'current_quiz' not in st.session_state or st.session_state.current_quiz not in st.session_state.quizzes:
        st.error("Quiz tidak ditemukan!")
        return
    
    quiz_code = st.session_state.current_quiz
    quiz_data = st.session_state.quizzes[quiz_code]
    
    st.title(f"Quiz - Kode: {quiz_code}")
    st.write(f"**Tingkat Kesulitan:** {quiz_data['difficulty']}")
    st.write(f"**Jumlah Soal:** {quiz_data['num_questions']}")
    st.write(f"**Dibuat pada:** {quiz_data['created_at']}")
    
    # Tampilkan semua soal dengan jawaban dan penjelasan
    for i, q in enumerate(quiz_data['data']['quiz']):
        with st.expander(f"Soal {i+1}: {q['question']}"):
            st.write("**Opsi Jawaban:**")
            for key, option in q['options'].items():
                if key == q['correct_answer']:
                    st.success(f"{key.upper()}. {option} ✓")
                else:
                    st.write(f"{key.upper()}. {option}")
            
            st.write(f"**Jawaban Benar:** {q['correct_answer'].upper()}")
            st.write(f"**Penjelasan:** {q.get('explanation', 'Tidak ada penjelasan')}")
    
    # Tombol untuk bagikan quiz ke siswa
    st.divider()
    st.subheader("Bagikan Quiz ke Siswa")
    st.write(f"Kode Quiz: **{quiz_code}**")
    st.write("Beritahu siswa untuk memasukkan kode ini pada halaman 'Kerjakan Quiz'")
    
    # Tombol untuk kembali ke daftar quiz
    if st.button("Kembali ke Daftar Quiz"):
        st.session_state.current_page = 'quiz_list'
        st.rerun()

# Halaman Daftar Quiz
def render_quiz_list():
    st.title("Daftar Quiz")
    
    if not st.session_state.quizzes:
        st.info("Belum ada quiz yang dibuat.")
        return
    
    for code, quiz in st.session_state.quizzes.items():
        with st.expander(f"Quiz {code} - {quiz['created_at']}"):
            st.write(f"**Tingkat Kesulitan:** {quiz['difficulty']}")
            st.write(f"**Jumlah Soal:** {quiz['num_questions']}")
            
            if st.button(f"Lihat Quiz {code}", key=f"view_{code}"):
                st.session_state.current_quiz = code
                st.session_state.current_page = 'view_quiz'
                st.rerun()

# Halaman Take Quiz (Siswa)
def render_take_quiz():
    st.title("Kerjakan Quiz")
    
    # Input kode quiz
    quiz_code = st.text_input("Masukkan Kode Quiz:")
    
    if quiz_code:
        if quiz_code not in st.session_state.quizzes:
            st.error("Kode quiz tidak valid!")
            return
        
        quiz_data = st.session_state.quizzes[quiz_code]['data']
        
        # Inisialisasi jawaban siswa jika belum ada
        if 'student_answers' not in st.session_state:
            st.session_state.student_answers = {}
        
        if quiz_code not in st.session_state.student_answers:
            st.session_state.student_answers[quiz_code] = {}
        
        # Tampilkan quiz
        st.divider()
        st.header("📝 Soal")
        
        for i, q in enumerate(quiz_data['quiz']):
            st.subheader(f"Soal {i+1}: {q['question']}")
            options = list(q["options"].values())
            
            # Simpan jawaban siswa
            st.session_state.student_answers[quiz_code][i] = st.radio(
                "Pilih jawaban:",
                options,
                key=f"q{i}_{quiz_code}",
                index=None
            )
            st.write("---")
        
        # Check answers
        if st.button("Selesai & Periksa Jawaban"):
            st.session_state.show_results = True
            st.session_state.current_quiz_check = quiz_code
            st.rerun()
        
        # Tampilkan hasil
        if st.session_state.get('show_results', False) and st.session_state.get('current_quiz_check') == quiz_code:
            render_quiz_results(quiz_code)

# Tampilkan hasil quiz
def render_quiz_results(quiz_code):
    quiz_data = st.session_state.quizzes[quiz_code]['data']
    student_answers = st.session_state.student_answers[quiz_code]
    
    st.divider()
    st.header("📊 Hasil")
    score = 0
    
    for i, q in enumerate(quiz_data['quiz']):
        user_answer = student_answers.get(i)
        correct_key = q["correct_answer"]
        correct_text = q["correct_text"]
        
        st.subheader(f"Soal {i+1}")
        st.write(f"**Pertanyaan:** {q['question']}")
        
        if user_answer == correct_text:
            st.success(f"✅ Jawaban Anda: {user_answer} (Benar)")
            score += 1
        else:
            st.error(f"❌ Jawaban Anda: {user_answer or 'Tidak dijawab'}")
            st.info(f"Jawaban benar: {correct_text} ({correct_key.upper()})")
        
        st.write(f"💡 Penjelasan: {q.get('explanation', 'Tidak ada penjelasan')}")
        st.write("---")
    
    st.success(f"🎉 Skor Anda: {score}/{len(quiz_data['quiz'])}")
    
    # Reset
    if st.button("Kerjakan Quiz Lain"):
        st.session_state.show_results = False
        st.session_state.current_quiz_check = None
        st.rerun()

# Main App
def main():
    render_sidebar()
    
    if st.session_state.current_page == 'home':
        render_home()
    elif st.session_state.current_page == 'audio_to_materi':
        render_audio_to_materi()
    elif st.session_state.current_page == 'quiz_generator':
        render_quiz_generator()
    elif st.session_state.current_page == 'view_quiz':
        render_view_quiz()
    elif st.session_state.current_page == 'quiz_list':
        render_quiz_list()
    elif st.session_state.current_page == 'take_quiz':
        render_take_quiz()
    elif st.session_state.current_page == 'microfon':  # tambahkan ini
        microfon()

if __name__ == "__main__":
    main()
