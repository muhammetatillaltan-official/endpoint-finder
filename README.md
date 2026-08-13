# 🚀 ENDPOINT FINDER v2.1

**Web Endpoint Keşif & Analiz Aracı** — Hedef sitenin endpoint haritasını çıkaran interaktif Python pentest tool'u.

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              ███████╗███╗   ██╗██████╗                      ║
║              ██╔════╝████╗  ██║██╔══██╗                     ║
║              █████╗  ██╔██╗ ██║██║  ██║                     ║
║              ██╔══╝  ██║╚██╗██║██║  ██║                     ║
║              ███████╗██║ ╚████║██████╔╝                     ║
║              ╚══════╝╚═╝  ╚═══╝╚═════╝                      ║
║                                                              ║
║                  ███████╗██╗███╗   ██╗██████╗               ║
║                  ██╔════╝██║████╗  ██║██╔══██╗              ║
║                  █████╗  ██║██╔██╗ ██║██║  ██║              ║
║                  ██╔══╝  ██║██║╚██╗██║██║  ██║              ║
║                  ██║     ██║██║ ╚████║██████╔╝              ║
║                  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝               ║
║                                                              ║
║                    E N D P O I N T   F I N D E R             ║
║                             v2.1                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

> *"Harbici buradayız lan!"* — dedirten o tool. 🔐😅

---

## 📌 Özellikler

| Özellik | Açıklama |
|---|---|
| 🎨 **Cinematic Banner** | pyfiglet varsa figlet fontu, yoksa el yapımı ASCII blok font. Renkli, typing efektli açılış. |
| 🧙 **İnteraktif Sihirbaz** | URL, protokol (HTTPS/HTTP), dosya adı, format (JSON/HTML/TXT), verbose, thread sayısı — hepsi tek tek sorulur. |
| 🕷️ **BFS Crawler** | Sayfaları derinlik limitine kadar gezer; link, form action, script, iframe, HTML yorumu toplar. |
| 🧬 **JS Kurcalama** | `fetch`, `XHR`, `axios`, `url:` anahtarları ve dosya pattern'lerini regex ile tarar. |
| 🤖 **robots.txt + sitemap.xml** | Otomatik okur, Disallow yollarını ve sitemap adreslerini keşfe ekler. |
| ⚡ **Thread'li Durum Kontrolü** | `ThreadPoolExecutor` ile paralel HTTP status sorgusu + canlı progress bar. |
| 🗂️ **3 Format Rapor** | JSON (makine okuması), HTML (koyu temalı, renkli rozetli), TXT (düz metin). |
| 🐢 **Verbose Mod** | Her adım `time.sleep(0.3)` ile yavaş, izlenebilir ve havalı akar. |

---

## ⚙️ Kurulum

```bash
# 1. Depoyu çek
git clone https://github.com/muhammetatillaltan-official/endpoint-finder.git
cd endpoint-finder

# 2. Bağımlılıkları kur
pip install -r requirements.txt

# 3. Çalıştır
python3 endpoint_finder.py
```

> **Not:** pyfiglet opsiyoneldir — kuruluysa banner daha süslü görünür, kurulu değilse tool kendi ASCII fontuna düşer.

---

## 🎮 Kullanım

Tool tamamen interaktiftir; çalıştırınca sırayla sorular sorar:

```
?  Hedef web adresini gir (ornek: www.cia.gov)
> www.cia.gov

[>] Adreste protokol yok, tamamlamak icin sec:
   [1] HTTPS  (guvenli, varsayilan)
   [2] HTTP   (acik baglanti)
?  Secimin: 1

?  Rapor dosyasinin adi ne olsun (ornek: results)
> results

[>] Hangi formatta kaydedilsin:
   [1] JSON   (makine okumasi, en detayli)
   [2] HTML   (tarayicida acilir, suslu)
   [3] TXT    (duz metin, hizli bakis)
?  Secimin: 1

?  Verbose mod acilsin mi? [y]evet / [n]hayir
> y

?  Kac thread ile taransin (ornek: 10)
> 10
```

### Akış şeması

```
Banner → Bilgi kartı → URL + Protokol → Dosya adı + Format
      → Verbose (y/n) → Thread sayısı → Tarama Planı özeti
      → robots.txt → sitemap.xml → BFS crawl → JS kurcalama
      → Thread'li status kontrol → Renkli tablo → Özet → Rapor
```

---

## 📤 Örnek Çıktı

```
[*] Hedef belirlendi: https://www.cia.gov
[*] Domain: www.cia.gov | Thread: 10
[*] robots.txt araniyor...
[*] robots.txt bulundu, Disallow yollari toplaniyor
[*] Sayfa gezintisi basliyor (BFS)
[*] [SAYFA] https://www.cia.gov (derinlik: 0)
[*] [JS] https://www.cia.gov/assets/app.js
[*] [JS] https://www.cia.gov/assets/api-client.js

==> 42 endpoint durum kontrolu basliyor (10 thread)...
[%] %100.0  |  42/42 taranan endpoint

============================================================
  DURUM   BOYUT   TIP                     ENDPOINT
============================================================
   200      8423  text/html               https://www.cia.gov/
   301       162  text/html               https://www.cia.gov/login
   403       512  text/html               https://www.cia.gov/admin
   404       234  text/html               https://www.cia.gov/backup
============================================================

== OZET ==
[+] Hedef           : https://www.cia.gov
[+] Sure            : 12.84 sn
[+] Gezilen sayfa   : 8
[+] Bulunan endpoint: 42
[+] Canli (2xx)     : 31
[+] Yonlendirme     : 6
[+] Istek hatasi    : 5

[+] JSON raporu yazildi -> results.json
[✓] Tarama tamamlandi. Rapor -> results.json
Harbici buradayiz lan! Iyi avlar.
```

---

## 📁 Rapor Formatları

### JSON
Makine okuması için ideal: tarih, süre, özet istatistikler, her endpoint'in status/boyut/tip bilgisi ve tüm bulguların kaynaklarıyla listesi.

### HTML
Koyu temalı, tarayıcıda açılan şık rapor. Durum kodları renkli rozetlerle (`2xx` yeşil, `3xx` mavi, `4xx` turuncu, `5xx` kırmızı).

### TXT
Hızlı bakış için düz metin — status kodları ve URL listesi.

---

## 🛠️ Teknik Detaylar

- **Dil:** Python 3.8+
- **Bağımlılıklar:** `requests`, `beautifulsoup4`, `colorama`, `pyfiglet` (opsiyonel)
- **Crawl:** BFS, derinlik limiti varsayılan 2
- **Concurrency:** `ThreadPoolExecutor` (1–64 thread desteklenir)
- **Sertifika:** Pentest standardı gereği SSL doğrulaması kapalı (`verify=False`), uyarılar bastırılmış
- **User-Agent:** Tarama kimliği belirtilmiş varsayılan UA

---

## 🗺️ Yol Haritası (Roadmap)

- [ ] Wordlist tabanlı brute-force modu (ffuf/feroxbuster tarzı)
- [ ] Burp Suite proxy desteği (`--proxy`)
- [ ] Tarama duraklatma / devam ettirme (session save/load)
- [ ] JWT / token yakalama ve analiz
- [ ] Tech fingerprint (Wappalyzer tarzı teknoloji tespiti)
- [ ] Docker desteği

---

## ⚠️ Yasal Uyarı

> **Bu araç yalnızca eğitim ve yetkili güvenlik testleri için geliştirilmiştir.**
> İzin alınmamış sistemlere karşı kullanımı birçok ülkede **suçtur**. Kullanmadan önce hedef üzerinde **yazılı yetkinizin** olduğundan emin olun. Tüm sorumluluk kullanıcıya aittir.

---

## 📄 Lisans

MIT — detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 🙏 Katkı

Pull request'lere ve fikirlere açığız! Yol haritasındaki maddelerden birini üstlenmek isterseniz issue açın, konuşalım. 🤝
