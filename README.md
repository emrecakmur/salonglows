# 💅 SalonnPRO | Güzellik Merkezleri & Kuaförler İçin Akıllı Randevu, Seans & Müşteri Yönetim SaaS Platformu

Güzellik salonları, kuaförler, berberler ve estetisyenler için geliştirilmiş; müşterilerin Instagram bio linki üzerinden 7/24 online randevu almasını sağlayan, otomatik WhatsApp randevu hatırlatması gönderen ve seans paketlerini takip eden **B2B SaaS Yazılımı**.

---

## 🌟 Öne Çıkan Satış Özellikleri

1. **Güzellik Salonu Yönetim Paneli (`/`)**:
   * Bugünü randevu akışı ve saatlik çizelge.
   * Tahmini günlük ciro ve kasa takibi.
   * Ekip ve uzman kadrosu çalışma takvimi.

2. **Instagram Bio Randevu Linki (`/b/glamour-guzellik`)**:
   * Müşterilerin telefonda sıra beklemeden 7/24 online randevu aldığı mobil uyumlu ekran.
   * Hizmet seçimi, uzman seçimi, tarih/saat seçimi ve anında onay.

3. **Seans & Paket Takip Modülü**:
   * Lazer epilasyon ve cilt bakım paketlerinin seans hakları takibi (Örn. 8 Seans Lazer -> 4 Seans Tamamlandı).
   * Tek tıkla "1 Seans Düş" butonu.

4. **Otomatik WhatsApp Randevu Hatırlatıcı**:
   * Randevu zamanından önce müşteriye otomatik WhatsApp mesajı gönderme ve onay alma.

5. **SaaS Abonelik & Satış Sayfası (`/subscription`)**:
   * **Başlangıç Paketi** (Tek Kuaför / Uzman): 499 ₺ / ay
   * **PRO Salon Paketi** (Sınırsız Uzman + WhatsApp + Seans Takip): 990 ₺ / ay
   * **Enterprise VIP** (Çoklu Şube): 1.990 ₺ / ay

---

## 🚀 Çalıştırma

```bash
cd C:\Users\user\.gemini\antigravity\scratch\salonn_pro
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Salon Yönetim Paneli**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Müşteri Online Randevu Ekranı (Instagram Linki)**: [http://127.0.0.1:8000/b/glamour-guzellik](http://127.0.0.1:8000/b/glamour-guzellik)
- **SaaS Paket & Fiyatlandırma Sayfası**: [http://127.0.0.1:8000/subscription](http://127.0.0.1:8000/subscription)
