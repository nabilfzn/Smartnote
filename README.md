# SmartNote

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


