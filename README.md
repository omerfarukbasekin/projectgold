# Gold Ingestor & Firebase Syncer

Bu proje, Altınkaynak üzerinden çekilen canlı altın fiyatlarını yerel bir SQLite veritabanında toplar ve bağımsız bir Docker servisi (Syncer) aracılığıyla Firebase Firestore veritabanına aktarır.

## Mimari

1. **Toplayıcı Container (`gold-collector-old`):**
   - Hali hazırda çalışan eski Docker container'ı tarafından yönetilir.
   - 10 dakikada bir fiyatları çeker ve kök dizindeki `app.db` isimli SQLite veritabanına yazar.
2. **Senkronizasyon Container (`gold-syncer`):**
   - Yeni oluşturulan bağımsız bir Docker servisidir (`Dockerfile.syncer` ve `docker-compose.yml` kullanır).
   - Ana dizindeki `app.db` dosyasını volume olarak bağlar (okur).
   - 30 dakikada bir çalışarak SQLite'ta biriken verileri (Atomic Batch mekanizması ile duplicate riski olmadan) Firebase Firestore'a basar.

## Kurulum ve Çalıştırma

### Firebase Kimlik Doğrulaması (Auth)
Container'ın Firebase veritabanına veri yazabilmesi için iki yetki yönteminden birini kullanmalısınız:

**Seçenek 1 (JSON Anahtarı - Tavsiye Edilen):**
Firebase Console -> Project Settings -> Service Accounts -> "Generate new private key" diyerek JSON dosyasını indirin. Bu dizine `service-account.json` olarak kaydedin. Ardından `docker-compose.yml` içindeki yorum satırını kaldırarak (uncomment) volume mount işlemini aktifleştirin.

**Seçenek 2 (Application Default Credentials - ADC):**
GCP (Google Cloud VM) üzerindeki yetkilerinizi kullanmak istiyorsanız, sunucuda yetki verdikten sonra (`gcloud auth application-default login`) o yetkiyi container'a env ve volume olarak geçmeniz gerekir.

### Sistemi Başlatma (Syncer)

Aşağıdaki komutla sadece Syncer container'ını arka planda (detached) ayağa kaldırın:
```bash
docker-compose up --build -d
```

- **Durumu Kontrol Etmek İçin:** `docker ps`
- **Logları Canlı İzlemek İçin:** `docker logs -f gold-syncer`
- **Durdurmak İçin:** `docker-compose down`

*Not: `gold-collector-old` container'ınız bu komutlardan etkilenmez, kendi döngüsünde çalışmaya devam eder.*
