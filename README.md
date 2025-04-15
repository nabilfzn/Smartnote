# 📕 SmartNote

**SmartNote** adalah solusi pembelajaran cerdas yang memanfaatkan teknologi **IoT** dan **Generative AI** untuk meningkatkan efektivitas belajar. Dengan kemampuan untuk merekam dan merangkum penjelasan audio secara otomatis, SmartNote membantu memastikan setiap materi tetap terdokumentasi meski disampaikan secara lisan.

Sistem ini secara instan mengubah rekaman menjadi **ringkasan** dan **modul pembelajaran** yang jelas dan terstruktur. Selain itu, SmartNote juga menyediakan **Quiz Generator** yang menghasilkan soal-soal berdasarkan materi tersebut, sehingga siswa dapat langsung mengukur pemahaman mereka.

> Dengan SmartNote, belajar jadi lebih **mudah**, **efisien**, dan **terarah**.

---

## 🚀 Cara Menggunakan SmartNote

### 1. Pastikan Versi Python
Gunakan **Python 3.10** atau versi yang sesuai dengan dependensi dalam proyek ini.

### 2. Buat Virtual Environment
Untuk menjaga lingkungan tetap bersih dan terisolasi:
```bash
python -m venv venv
```
### 3. Aktifkan Virtual Environment
  - Windows:
  ```bash
  venv\Scripts\activate
  ```
  - MacOS/Linux:
  ```bash
  source venv/bin/activate
  ```
### 4. Install Semua Library
Pastikan sudah berada di direktori utama proyek. Jalankan:

```bash
pip install -r requirements.txt
```

### 5. Buat File .env
Buat file .env di root project (satu folder dengan app.py dan flask.py) dan isi dengan variabel berikut:

```bash
OPENAI_API_KEY=your_openai_api_key
FLASK_SERVER_URL=http://alamat-ip-esp32-atau-server:port
```
Contoh:

```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
FLASK_SERVER_URL=http://192.168.1.100:5000
```
#### ⚠️ Catatan Penting:
- Pastikan semua perangkat (komputer, ESP32, dan server Flask) berada dalam satu jaringan WiFi yang sama.
- URL yang tidak sesuai (salah IP atau port) akan menyebabkan koneksi gagal antara Streamlit dan Flask.

<br>

## 🧠 Langkah Menjalankan Aplikasi
1. Jalankan terlebih dahulu server Flask:
```bash
python flask.py
```
2. Setelah Flask aktif, jalankan aplikasi Streamlit:
```bash
streamlit run app.py
```

<br>


## 📂 Struktur Proyek (Contoh)

```bash
SmartNote/
├── app.py
├── flask.py
├── requirements.txt
├── .env
├── utils/
│   ├── summarizer.py
│   ├── quiz_generator.py
│   └── ...
└── README.md
```

<br>
## ✅ Fitur Utama

🎙️ Kontrol dan Rekam Audio via ESP32
✂️ Ringkasan Otomatis dari Penjelasan Audio
📚 Modul Pembelajaran Terstruktur
❓ Quiz Generator Otomatis
📡 Integrasi IoT + AI dalam satu sistem


<br>
## 🛠️ Teknologi yang Digunakan

- Python
- Streamlit
- Flask
- ESP32 + I2S Mic
- Gemini
- SD Card Module (ESP32)

<br>

## 🧩 Catatan Tambahan
- Jika menggunakan ESP32, pastikan firmware yang dipakai sesuai dengan kebutuhan dan bisa menangani:
  
  - Rekam audio via I2S
  - Simpan ke SD card
  - Kirim file via HTTP POST ke Flask server

- Gunakan serial monitor (misal Arduino IDE) untuk melihat log dari ESP32 jika terjadi error saat merekam atau mengupload.




