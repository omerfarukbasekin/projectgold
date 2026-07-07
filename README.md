# [TR] Gold Price Tracker | Backend Pipeline 🪙

Bu proje, altın fiyatlarını anlık olarak çekerek ilişkisel bir veritabanında saklayan ve her 30 dakikada bir Cloud Firestore'a senkronize eden profesyonel bir arka plan veri hattıdır (data pipeline).

---

## 🏛️ Mimari Yapı

Proje, birbirleriyle uyumlu çalışan üç ana bileşenden oluşur:
1. **PostgreSQL 15 (Veritabanı):** Tüm geçmiş altın verilerini `trades` tablosunda güvenle depolar. Tablodaki `synced_to_firebase` kolonu (boolean) sayesinde veritabanı seviyesinde hangi satırın Firestore'a gidip gitmediği takip edilir.
2. **Gold Collector (Python Servisi):** Altınkaynak API'sinden 5 dakikada bir anlık fiyatları çekerek Postgres'e yazar (`ON CONFLICT` ile mükerrer kayıtlar engellenir).
3. **Firebase Syncer (Python Servisi):** Postgres'ten henüz eşleşmemiş kayıtları toplu olarak çeker, her 30 dakikada bir Firestore'a yazar ve başarıyla aktarılanları Postgres'te `TRUE` olarak işaretler.

---

## 📁 Proje Dosya Düzeni

```text
project gold/
├── .env                  # Yerel / Konteyner ortam değişkenleri (Git'e atılmaz)
├── .gitignore            # Güvenlik ve çöp dosyaları engelleme listesi
├── requirements.txt      # Gerekli kütüphaneler (psycopg2-binary, firebase-admin, vb.)
├── Dockerfile            # Python imajı derleme tarifi
├── docker-compose.yml    # Postgres, Collector ve Syncer servislerini ayağa kaldıran dosya
├── runner.sh             # Döngü yöneticisi (collector / syncer seçimine göre çalışır)
├── collector.py          # Fiyatları çeken ve Postgres'e yazan ana script
└── syncer.py             # Postgres'ten Firestore'a verileri 30 dakikada bir basan script
```

---

## ⚙️ Kurulum ve Çalıştırma

### 1. Ortam Değişkenlerini Ayarlayın
Dizin içinde `.env` dosyası oluşturun ve aşağıdaki şablonu kendi bilgilerinize göre doldurun:
```ini
DB_HOST=db
DB_PORT=5432
DB_NAME=gold_db
DB_USER=gold_user
DB_PASSWORD=your_secure_password
FIREBASE_PROJECT_ID=projectgold-6b3bf
```

### 2. Yetkilendirme (Firebase Auth)
Yerel makinede veya Docker üzerinde Firestore'a yazabilmek için:
- Firebase Console -> Proje Ayarları -> Hizmet Hesapları (Service Accounts) sekmesinden yeni bir **Özel Anahtar (JSON)** üretin.
- İndirdiğiniz JSON dosyasını bu klasör içine `service-account.json` ismiyle kaydedin. (Git tarafından otomatik olarak yoksayılacaktır).

### 3. Docker ile Sistemi Ayağa Kaldırın
```bash
docker compose up -d --build
```
Bu komut sırasıyla PostgreSQL'i, 5 dk bir çalışan veri toplayıcıyı ve 30 dk bir çalışan eşitleyiciyi ayağa kaldıracaktır.

---

## 🔄 SQLite'dan PostgreSQL'e Veri Göçü (Migration)

Eski `app.db` SQLite veritabanındaki tüm geçmişinizi yeni PostgreSQL veritabanına taşımak için:

1. Önce sadece PostgreSQL veritabanını başlatın:
   ```bash
   docker compose up -d db
   ```
2. Geçici göç scriptinizi hazırlayın (`migrate.py`) ve yerel sanal ortamınızı kullanarak çalıştırın:
   ```bash
   source ../.venv/bin/activate
   python migrate.py
   ```
3. Göç işlemi tamamlandıktan sonra tüm servisleri tam kapasite başlatabilirsiniz:
   ```bash
   docker compose up -d
   ```

---
---

# [EN] Gold Price Tracker | Backend Pipeline 🪙

This project is a professional background data pipeline designed to fetch gold prices, store them in a relational database, and synchronize them with Cloud Firestore every 30 minutes.

---

## 🏛️ Architecture

The project consists of three main components working in harmony:
1. **PostgreSQL 15 (Database):** Safely stores all historical gold data in the `trades` table. A boolean column `synced_to_firebase` tracks at the database level whether a row has been synchronized with Firestore.
2. **Gold Collector (Python Service):** Fetches instant prices from Altınkaynak API every 5 minutes and writes them to Postgres (prevents duplicate records using `ON CONFLICT`).
3. **Firebase Syncer (Python Service):** Periodically pulls unsynced records from Postgres, batch-writes them to Firestore every 30 minutes, and updates the status to `TRUE` in Postgres upon a successful write.

---

## 📁 Project Directory Tree

```text
project gold/
├── .env                  # Local / Container environment variables (ignored by Git)
├── .gitignore            # Security and junk files ignore list
├── requirements.txt      # Required libraries (psycopg2-binary, firebase-admin, etc.)
├── Dockerfile            # Python base image build recipe
├── docker-compose.yml    # Main compose file hosting Postgres, Collector, and Syncer services
├── runner.sh             # Loop runner script (handles collector vs syncer loops)
├── collector.py          # Main script pulling price data and inserting to Postgres
└── syncer.py             # Script syncing Postgres data to Firestore every 30 minutes
```

---

## ⚙️ Installation and Setup

### 1. Set Up Environment Variables
Create a `.env` file in the folder and fill in the following template with your actual credentials:
```ini
DB_HOST=db
DB_PORT=5432
DB_NAME=gold_db
DB_USER=gold_user
DB_PASSWORD=your_secure_password
FIREBASE_PROJECT_ID=projectgold-6b3bf
```

### 2. Authorization (Firebase Auth)
To write to Firestore from your local environment or Docker containers:
- Go to Firebase Console -> Project Settings -> Service Accounts.
- Generate a new **Private Key (JSON)**.
- Rename the downloaded JSON file to `service-account.json` and save it directly in this directory (it will be automatically ignored by Git).

### 3. Spin Up the System using Docker Compose
```bash
docker compose up -d --build
```
This command builds and runs PostgreSQL, the 5-minute data collector service, and the 30-minute syncer worker in the background.

---

## 🔄 SQLite to PostgreSQL Migration

To migrate all historical gold price records from your legacy `app.db` SQLite database to the new PostgreSQL database:

1. Spin up only the PostgreSQL service first:
   ```bash
   docker compose up -d db
   ```
2. Create and run your migration script (`migrate.py`) locally using your virtual environment:
   ```bash
   source ../.venv/bin/activate
   python migrate.py
   ```
3. Once the migration has completed, safely start all the background services:
   ```bash
   docker compose up -d
   ```
