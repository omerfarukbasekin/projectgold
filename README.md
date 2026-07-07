# Gold Price Tracker | Backend Pipeline 🪙

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
