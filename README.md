# Gold Ingestor & Firebase Syncer

Bu proje, Altınkaynak üzerinden çekilen canlı altın fiyatlarını yerel bir SQLite veritabanında toplar ve bağımsız bir zamanlayıcı (`runner_direct.sh`) aracılığıyla Firebase Firestore veritabanına aktarır.

## Mimari

1. **Toplayıcı Container (`gold-collector-old`):**
   - Hali hazırda çalışan eski Docker container'ı tarafından yönetilir.
   - 10 dakikada bir fiyatları çeker ve kök dizindeki `app.db` isimli SQLite veritabanına yazar.
2. **Senkronizasyon Zamanlayıcısı (`runner_direct.sh`):**
   - Her 30 dakikada bir otomatik olarak `manual_push_all.py` scriptini tetikler.
   - Limitleri ve delay (bekleme) mekanizmalarıyla Firebase kotalarını yormadan verileri Firestore'a yollar.

---

## Kurulum ve Çalıştırma

Sistem sanal bir Python ortamı (Virtual Environment - `venv`) kullanır. Projeyi bir sunucuda veya yerel ortamda ilk defa kuruyorsanız aşağıdaki adımları sırasıyla izleyin.

### 1. Sanal Ortam (venv) Oluşturma ve Aktifleştirme
Sunucunuzun Python sistemini bozmamak için projenin kök dizininde bir sanal ortam oluşturmalısınız:
```bash
# Sanal ortamı oluşturun
python3 -m venv venv

# Sanal ortamı aktifleştirin (Terminalinizin başında "(venv)" yazısını göreceksiniz)
source venv/bin/activate
```

### 2. Gerekli Kütüphanelerin Yüklenmesi
Sanal ortam aktifken (yukarıdaki adımı yaptıktan sonra), Firebase veritabanına veri yazabilmemiz için gerekli kütüphaneyi kurun:
```bash
pip install firebase-admin
```

### 3. Firebase Kimlik Doğrulaması (Auth)
Script'in Firebase veritabanına veri yazabilmesi için sunucu üzerinde yetkilendirme yapmanız gerekir. GCP (Google Cloud) kullanıyorsanız doğrudan terminalinizde şu komutu çalıştırarak güvenli bağlantıyı (Application Default Credentials - ADC) sağlayabilirsiniz:
```bash
gcloud auth application-default login
```
*Bu komut size bir link verecektir. Tarayıcıdan bu linke gidip hesabınızla onay verdikten sonra size verilen kodu tekrar terminale yapıştırın.*

### 4. Sistemi Başlatma (Syncer)
Sanal ortam kurulup yetki verildikten sonra, her 30 dakikada bir çalışacak zamanlayıcıyı başlatmak için sadece şu komutu çalıştırın:
```bash
# İlk önce script'e çalışma izni verin (Bir defaya mahsus)
chmod +x runner_direct.sh

# Zamanlayıcıyı başlatın
./runner_direct.sh
```

Bunu yaptıktan sonra ekranda "Başarıyla başlatıldı!" yazısını göreceksiniz. Artık terminali tamamen kapatabilirsiniz. Sistem arka planda sonsuza dek çalışmaya devam edecektir.

- **Ne Yaptığını Canlı İzlemek İçin:** `tail -f direct_syncer.log`
- **Sistemi Tamamen Durdurmak İçin:** `pkill -f runner_direct.sh` ve ardından `pkill -f manual_push_all.py`
