# 🌐 SalonGlow Canlıya Alma ve Domain Rehberi

Bu rehber, **SalonGlow** projenizi tüm dünyadan insanların ve salon sahiplerinin erişebileceği canlı bir siteye dönüştürmeniz için hazırlanmıştır.

---

## 📌 1. Aşama: Domain (Alan Adı) Satın Alma

Sitenizin internetteki adresi (Örn: `www.salonglow.com` veya `www.salonglow.com.tr`):

### 💡 Önerilen Domain İsimleri:
- `salonglow.com` (En iyisi - Küresel ve prestijli)
- `salonglow.com.tr` (Türkiye odaklı, kurumsal güven verir)
- `salonglow.app` (Modern yazılım/SaaS hissi verir)

### 🛒 Nereden Alınır?
- **.com.tr için**: Natro.com veya METUnic.com.tr (Belgesiz, anında onaylanır, ~100-150 TL/yıl)
- **.com veya .app için**: Cloudflare.com veya Namecheap.com (~10-12$)

---

## 🚀 2. Aşama: Ücretsiz Canlı Cloud Sunucu (Render.com)

SalonGlow'u 7/24 kesintisiz çalıştıracak ve ücretsiz SSL (HTTPS kilit simgesi) sağlayacak sunucu kurulumu:

1. Render.com adresine ücretsiz üye olun.
2. GitHub hesabınıza `salonn_pro` projenizi yükleyin (veya Render'a zip/git bağlayın).
3. Render panelinde **"New Web Service"** butonuna tıklayın.
4. Reponuzu seçin ve şu ayarları yapın:
   - **Name**: `salonglow`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **"Create Web Service"** butonuna basın. 2 dakika içinde siteniz `https://salonglow.onrender.com` olarak canlıya geçecektir!

---

## 🔗 3. Aşama: Domain ile Render Sunucusunu Bağlama

1. Render panelinde projenizin **"Settings" -> "Custom Domains"** bölümüne gelin.
2. Satın aldığınız alan adını ekleyin (`salonglow.com` veya `salonglow.com.tr`).
3. Domain firması panelinizde (Natro/Cloudflare vb.) DNS kayıtlarına Render'ın verdiği `CNAME` veya `A` adresini ekleyin.
4. **SSL (HTTPS)** sertifikası 5 dakika içinde otomatik aktif olacaktır.

---

## 📱 Sonuç
Artık kuaförlere ve güzellik salonlarına kartvizitinizde veya Instagram'da **`https://salonglow.com`** adresinizi verebilir, üyelik satmaya başlayabilirsiniz!
