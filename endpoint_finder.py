#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import html
import threading
from collections import deque
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from bs4 import BeautifulSoup, Comment
except ImportError:
    print("[!] Eksik kutuphane var!")
    print("    pip install requests beautifulsoup4 colorama")
    sys.exit(1)

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    K = Fore.BLACK; R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW
    B = Fore.BLUE; M = Fore.MAGENTA; C = Fore.CYAN; W = Fore.WHITE
    S = Style.RESET_ALL
except ImportError:
    K = R = G = Y = B = M = C = W = S = ""

# pyfiglet varsa kullan, yoksa elimizdeki blok font var
try:
    import pyfiglet
    FIGLET_VAR = True
except ImportError:
    FIGLET_VAR = False

# pentest'te self-signed sertifika olayini sessize al
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

BLOK_FONT = {
    " ": ["     ", "     ", "     ", "     ", "     "],
    "E": ["██████ ", "██     ", "█████  ", "██     ", "██████ "],
    "N": ["███   ██", "████  ██", "██ ██ ██", "██  ████", "██   ██"],
    "D": ["██████ ", "██   ██", "██   ██", "██   ██", "██████ "],
    "P": ["██████ ", "██   ██", "██████ ", "██     ", "██     "],
    "O": [" █████ ", "██   ██", "██   ██", "██   ██", " █████ "],
    "I": ["███████", "  ███  ", "  ███  ", "  ███  ", "███████"],
    "T": ["███████", "  ███  ", "  ███  ", "  ███  ", "  ███  "],
    "F": ["██████ ", "██     ", "█████  ", "██     ", "██     "],
    "R": ["██████ ", "██   ██", "██████ ", "██ ██  ", "██  ██ "],
}


def ascii_banner(yazi):
    """Verilen metni blok fontla 5 satirlik ASCII'ye cevirir."""
    satirlar = [""] * 5
    for harf in yazi:
        blok = BLOK_FONT.get(harf.upper(), BLOK_FONT["I"])
        for i in range(5):
            satirlar[i] += " " + blok[i]
    return satirlar


def tip(metin, hiz=0.0015):
    """Karakter karakter yazan tip efektli print."""
    for karakter in metin:
        sys.stdout.write(karakter)
        sys.stdout.flush()
        time.sleep(hiz)
    sys.stdout.write("\n")


def _uzunluk(metin):
    """ANSI renk kodlarini saymadan gercek uzunlugu dondurur."""
    return len(re.sub(r"\x1b\[[0-9;]*m", "", metin))


def banner_goster():
    """Ekrani temizler, banner'i renkli ve tip efektiyle basar."""
    os.system("cls" if os.name == "nt" else "clear")

    if FIGLET_VAR:
        satirlar = pyfiglet.figlet_format("ENDPOINT FINDER", font="big").rstrip("\n").split("\n")
    else:
        satirlar = ascii_banner("ENDPOINT FINDER")

    renk_dongusu = [C, M, B, G, Y]
    for i, satir in enumerate(satirlar):
        if satir.strip():
            tip(renk_dongusu[i % len(renk_dongusu)] + satir + S, 0.0009)
        else:
            print()
    tip(f"{Y}· v2.1 · Web Endpoint Kesif & Analiz Araci · Muhammet Atilla Altan{S}", 0.001)
    time.sleep(0.4)


def bilgi_karti():
    """Banner altindaki bilgi kutusu."""
    genislik = 60
    ic_genislik = genislik - 2
    cizgi = "═" * ic_genislik

    def kutu(satir):
        dolu = satir + " " * (ic_genislik - _uzunluk(satir))
        return f"{C}║{S}{dolu}{C}║{S}"

    print(f"{C}╔{cizgi}╗{S}")
    print(kutu(f" {M}ENDPOINT FINDER{S} {Y}v2.1{S}  |  Web Endpoint Kesif Araci"))
    print(kutu(f" {W}Yapimci  :{S} {G}sibermareşalatillabey{S}"))
    print(kutu(f" {W}Discord  :{S} {G}muhammetatillaaltan{S}"))
    print(kutu(f" {W}Platform :{S} {G}Python 3.8+  /  Kali-Termux-iSH uyumlu{S}"))
    print(kutu(f" {R}[!]{S} {W}SORUMLULUK SİZE AİTTİR!{S}"))
    print(f"{C}╚{cizgi}╝{S}")

#  JS dosyalarinda aranacak endpoint pattern'leri

JS_PATERNLERI = [
    (r'fetch\s*\(\s*["\']([^"\']+)["\']',                                                    "FETCH"),
    (r'\.open\s*\(\s*["\'](?:GET|POST|PUT|DELETE|PATCH|OPTIONS)["\']\s*,\s*["\']([^"\']+)["\']', "XHR"),
    (r'(?:url|href|src|action)\s*[:=]\s*["\']([^"\']+)["\']',                                "URL_ANAHTARI"),
    (r'axios\.\w+\([^)]*["\']([^"\']+)["\']',                                                "AXIOS"),
    (r'([a-zA-Z0-9\-\.]+\.(?:php|asp|aspx|jsp|do|action|json|xml)(?:\?[^"\'\s]*)?)',          "DOSYA"),
    (r'["\'](/[A-Za-z0-9_\-./~%+?=&]{4,})["\']',                                             "GENEL_YOL"),
]

# GENEL_YOL pattern'inden gelen gurultuyu filtrelemek icin anahtar kelimeler

ANAHTAR_KELIMELER = ["api", "v1", "v2", "v3", "admin", "login", "auth", "token",
                     "user", "search", "upload", "download", "panel", "dashboard",
                     "config", "debug", "test", "backup", "private", "graphql",
                     "wp-", "sitemap", "swagger", "health", "status", "session"]


# ============================================================
#  KESIF MOTORU
# ============================================================
class KesifMotoru:
    def __init__(self, hedef_url, verbose=False, thread_sayisi=10, max_derinlik=2):
        self.hedef = hedef_url
        self.ayristirilmis = urlparse(hedef_url)
        self.domain = self.ayristirilmis.netloc
        self.verbose = verbose
        self.thread_sayisi = thread_sayisi
        self.max_derinlik = max_derinlik

        self.baslangic = time.time()
        self.oturum = requests.Session()
        self.oturum.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EndpointFinder/2.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
        })
        self.oturum.verify = False  # pentest standarti: sertifika dogrulamasini atla

        # her thread'in kendi session'i olsun (thread safety icin)
        self.thread_yerel = threading.local()
        self.kilit = threading.Lock()

        self.kuyruk = deque()
        self.gezilenler = set()
        self.sayfa_boyutlari = {}
        self.js_dosyalari = set()
        self.harici_domainler = set()
        self.endpointler = set()      # benzersiz endpoint URL'leri
        self.bulgular = set()         # (tip, url, kaynak) ucleyi
        self.sonuclar = {}            # url -> {kod, boyut, tip, konum}
        self.islem_sayaci = 0
        self.islem_toplam = 0

    # --------------------------------------------------------
    def vlog(self, mesaj):
        """Verbose modda adim adim goster. NOT: 0.3 sn yavaslatma."""
        if self.verbose:
            print(f"{C}[*]{S} {mesaj}")
            time.sleep(0.3)

    # --------------------------------------------------------
    def istek(self, url, yonlendirme=True):
        """GET istegi atar, hatalari yakalar, None doner."""
        try:
            return self.oturum.get(url, timeout=12, allow_redirects=yonlendirme)
        except requests.exceptions.SSLError:
            self.vlog(f"{R}[SSL HATASI]{S} {url}")
        except requests.exceptions.Timeout:
            self.vlog(f"{Y}[ZAMAN ASIMI]{S} {url}")
        except requests.exceptions.ConnectionError:
            self.vlog(f"{R}[BAGLANTI YOK]{S} {url}")
        except Exception as hata:
            self.vlog(f"{R}[HATA]{S} {url} -> {hata}")
        return None

    # --------------------------------------------------------
    def ayni_domain_mi(self, url):
        try:
            return urlparse(url).netloc.lower() == self.domain.lower()
        except Exception:
            return False

    # --------------------------------------------------------
    def url_temizle(self, url):
        """Kotu linkleri eler, goreceli adresleri tam URL yapar."""
        url = url.strip()
        if not url or url.startswith(("#", "?")):
            return None
        if url.lower().startswith(("javascript:", "mailto:", "tel:",
                                   "data:", "about:", "vbscript:")):
            return None
        tam = urljoin(self.hedef, url)
        parcali = urlparse(tam)
        if parcali.scheme not in ("http", "https"):
            return None
        return urlunparse((parcali.scheme, parcali.netloc, parcali.path,
                           "", parcali.query, ""))

    # --------------------------------------------------------
    def bulgu_ekle(self, tip, url, kaynak):
        if not url:
            return
        with self.kilit:
            self.bulgular.add((tip, url, kaynak))
            self.endpointler.add(url)

    # --------------------------------------------------------
    def robots_oku(self):
        self.vlog("robots.txt araniyor...")
        cevap = self.istek(urljoin(self.hedef, "/robots.txt"))
        if cevap and cevap.status_code == 200:
            self.vlog("robots.txt bulundu, Disallow yollari toplaniyor")
            for satir in cevap.text.splitlines():
                satir = satir.strip()
                if satir.lower().startswith("disallow"):
                    yol = satir.split(":", 1)[1].strip()
                    # "/" ve "*" gibi genel kurallari at, gerisini al
                    if yol and yol not in ("/", "*"):
                        tam = self.url_temizle(urljoin(self.hedef, yol))
                        if tam:
                            self.bulgu_ekle("ROBOTS", tam, "robots.txt")
        else:
            self.vlog("robots.txt yok ya da erisilemedi")

    # --------------------------------------------------------
    def sitemap_oku(self):
        self.vlog("sitemap.xml araniyor...")
        cevap = self.istek(urljoin(self.hedef, "/sitemap.xml"))
        if cevap and cevap.status_code == 200:
            adresler = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", cevap.text, re.I)
            self.vlog(f"sitemap.xml bulundu, {len(adresler)} adres var")
            for adres in adresler:
                tam = self.url_temizle(adres)
                if tam and self.ayni_domain_mi(tam):
                    self.kuyruk.append((tam, 1))
                    self.bulgu_ekle("SITEMAP", tam, "sitemap.xml")
        else:
            self.vlog("sitemap.xml yok ya da erisilemedi")

    # --------------------------------------------------------
    def gez(self, url, derinlik):
        """Bir sayfayi indirir, icindeki her seyi cikarir."""
        self.vlog(f"{G}[SAYFA]{S} {url} (derinlik: {derinlik})")
        cevap = self.istek(url)
        if not cevap:
            return

        icerik_tipi = cevap.headers.get("Content-Type", "")
        if "text/html" not in icerik_tipi and "application/xhtml" not in icerik_tipi:
            return  # pdf, resim vs. -> parse etmeye gerek yok

        self.sayfa_boyutlari[url] = len(cevap.content)
        try:
            corba = BeautifulSoup(cevap.text, "html.parser")
        except Exception:
            return

        # --- linkler (a ve area) ---
        for etiket in corba.find_all(["a", "area"], href=True):
            tam = self.url_temizle(etiket.get("href"))
            if not tam:
                continue
            if self.ayni_domain_mi(tam):
                self.bulgu_ekle("LINK", tam, url)
                # kuyrukta yoksa ve derinlik limiti icindeyse gez
                if tam not in self.gezilenler and derinlik < self.max_derinlik:
                    self.kuyruk.append((tam, derinlik + 1))
            else:
                self.harici_domainler.add(tam)
                self.bulgu_ekle("HARICI", tam, url)

        # --- form action'lari ---
        for form in corba.find_all("form", action=True):
            tam = self.url_temizle(form.get("action"))
            if not tam:
                continue
            self.bulgu_ekle("FORM", tam, url)
            if self.ayni_domain_mi(tam) and tam not in self.gezilenler:
                if derinlik < self.max_derinlik:
                    self.kuyruk.append((tam, derinlik + 1))

        # --- script src'leri (JS dosyalari) ---
        for script in corba.find_all("script", src=True):
            tam = self.url_temizle(script.get("src"))
            if tam:
                self.js_dosyalari.add(tam)
                self.bulgu_ekle("SCRIPT", tam, url)

        # --- iframe'ler ---
        for iframe in corba.find_all("iframe", src=True):
            tam = self.url_temizle(iframe.get("src"))
            if tam:
                self.bulgu_ekle("IFRAME", tam, url)

        # --- HTML yorumlari (gizli ipucu avi) ---
        for yorum in corba.find_all(string=lambda m: isinstance(m, Comment)):
            gizli = re.findall(r'https?://[^\s"\']+|/[A-Za-z0-9_\-./?=&]{4,}', yorum)
            for adres in gizli:
                tam = self.url_temizle(adres)
                if tam:
                    self.bulgu_ekle("YORUM", tam, url)

    # --------------------------------------------------------
    def js_kurcala(self, js_url):
        """JS dosyasini indir, icindeki endpoint pattern'lerini cikar."""
        self.vlog(f"{M}[JS]{S} {js_url}")
        cevap = self.istek(js_url)
        if not cevap or cevap.status_code != 200:
            return
        icerik = cevap.text

        for pattern, tip in JS_PATERNLERI:
            for eslesme in re.finditer(pattern, icerik):
                aday = eslesme.group(1).strip()
                tam = self.url_temizle(urljoin(js_url, aday))
                if not tam:
                    continue
                # GENEL_YOL pattern'inde anahtar kelime filtresi (gurultu azalt)
                if tip == "GENEL_YOL" and not any(k in aday.lower() for k in ANAHTAR_KELIMELER):
                    continue
                self.bulgu_ekle(f"JS-{tip}", tam, js_url)

    # --------------------------------------------------------
    def islem_sayac(self):
        with self.kilit:
            self.islem_sayaci += 1
            return self.islem_toplam - self.islem_sayaci

    # --------------------------------------------------------
    def durum_kontrol(self, url):
        """Tek endpoint'in HTTP durum kodunu kontrol eder (thread-safe)."""
        try:
            # her thread kendi session'ina sahip olsun
            yerel = getattr(self.thread_yerel, "oturum", None)
            if yerel is None:
                yerel = requests.Session()
                yerel.headers.update(self.oturum.headers)
                yerel.verify = False
                self.thread_yerel.oturum = yerel
            cevap = yerel.get(url, timeout=15, allow_redirects=True)
            with self.kilit:
                self.sonuclar[url] = {
                    "kod": cevap.status_code,
                    "boyut": len(cevap.content),
                    "tip": cevap.headers.get("Content-Type", "").split(";")[0],
                    "konum": cevap.headers.get("Location", ""),
                }
            return cevap.status_code
        except Exception:
            with self.kilit:
                self.sonuclar[url] = {"kod": 0, "boyut": 0, "tip": "", "konum": ""}
            return 0

    # --------------------------------------------------------
    def tumunu_kontrol_et(self):
        """ThreadPoolExecutor ile tum endpointlere durum sor + progress bar."""
        adresler = sorted(self.endpointler)
        self.islem_toplam = len(adresler)
        self.islem_sayaci = 0
        if not adresler:
            print(f"{Y}[-] Kontrol edilecek endpoint bulunamadi.{S}")
            return

        print(f"\n{Y}==> {len(adresler)} endpoint durum kontrolu basliyor "
              f"({self.thread_sayisi} thread)...{S}")

        with ThreadPoolExecutor(max_workers=self.thread_sayisi) as havuz:
            gelecekler = {havuz.submit(self.durum_kontrol, a): a for a in adresler}
            for gelecek in as_completed(gelecekler):
                gelecek.result()
                kalan = self.islem_sayac()
                yapilan = self.islem_toplam - kalan
                yuzde = (yapilan / self.islem_toplam) * 100
                print(f"\r{G}[%]{S} %{yuzde:5.1f}  |  {yapilan}/{self.islem_toplam} "
                      f"taranan endpoint", end="", flush=True)
        print()

    # --------------------------------------------------------
    def calistir(self):
        """Ana akis: robots -> sitemap -> BFS gez -> JS kurcala -> durum kontrol."""
        self.vlog(f"Hedef belirlendi: {self.hedef}")
        self.vlog(f"Domain: {self.domain} | Thread: {self.thread_sayisi}")
        self.kuyruk.append((self.hedef, 0))

        self.robots_oku()
        self.sitemap_oku()

        self.vlog("Sayfa gezintisi basliyor (BFS)")
        while self.kuyruk:
            adres, derinlik = self.kuyruk.popleft()
            if adres in self.gezilenler:
                continue
            self.gezilenler.add(adres)
            self.gez(adres, derinlik)

        self.vlog("JS dosyalari kurcalaniyor")
        for js in list(self.js_dosyalari):
            self.js_kurcala(js)

        self.tumunu_kontrol_et()

# ============================================================
#  RAPOR YAZICILAR
# ============================================================
def renkli_durum(kod):
    """Durum koduna gore renk sec (terminal tablosu icin)."""
    if kod == 0:            return R
    if 200 <= kod < 300:    return G
    if 300 <= kod < 400:    return C
    if 400 <= kod < 500:    return Y
    return M


def rapor_txt(dosya_adi, motor, baslangic):
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  ENDPOINT FINDER v2.1 - TARAMA RAPORU\n")
        f.write(f"  Tarih     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  Hedef     : {motor.hedef}\n")
        f.write(f"  Sure      : {time.time() - baslangic:.2f} sn\n")
        f.write(f"  Endpoint  : {len(motor.sonuclar)}\n")
        f.write("=" * 70 + "\n\n")
        for url in sorted(motor.sonuclar):
            bilgi = motor.sonuclar[url]
            f.write(f"[{bilgi['kod']:>3}] {url}\n")
    print(f"{G}[+] TXT raporu yazildi -> {dosya_adi}{S}")


def rapor_json(dosya_adi, motor, baslangic):
    veri = {
        "arac": "Endpoint Finder v2.1",
        "tarih": datetime.now().isoformat(),
        "hedef": motor.hedef,
        "sure_sn": round(time.time() - baslangic, 2),
        "ozet": {
            "toplam_endpoint": len(motor.endpointler),
            "gezilen_sayfa": len(motor.gezilenler),
            "js_dosyasi": len(motor.js_dosyalari),
            "harici_domain": len(motor.harici_domainler),
        },
        "sonuclar": [
            {"url": u, **motor.sonuclar[u]} for u in sorted(motor.sonuclar)
        ],
        "bulgular": [
            {"tip": t, "url": u, "kaynak": k} for t, u, k in sorted(motor.bulgular)
        ],
    }
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    print(f"{G}[+] JSON raporu yazildi -> {dosya_adi}{S}")


def rapor_html(dosya_adi, motor, baslangic):
    satirlar = []
    for url in sorted(motor.sonuclar):
        bilgi = motor.sonuclar[url]
        renk = "#198754"          # 2xx yesil
        if bilgi["kod"] == 0:     renk = "#dc3545"
        if 300 <= bilgi["kod"] < 400: renk = "#0dcaf0"
        if 400 <= bilgi["kod"] < 500: renk = "#fd7e14"
        if 500 <= bilgi["kod"]:        renk = "#dc3545"
        satirlar.append(
            f'<tr><td><span class="badge" style="background:{renk}">'
            f'{bilgi["kod"]}</span></td><td>{html.escape(url)}</td>'
            f'<td>{html.escape(bilgi["tip"])}</td><td>{bilgi["boyut"]}</td></tr>'
        )
    dokuman = f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>Endpoint Finder Raporu - {html.escape(motor.domain)}</title>
<style>
  body {{ font-family: 'Segoe UI', monospace; background: #0f172a; color: #e2e8f0; padding: 30px; }}
  h1 {{ color: #38bdf8; }} h2 {{ color: #94a3b8; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
  th, td {{ border: 1px solid #334155; padding: 8px 12px; text-align: left; }}
  th {{ background: #1e293b; }}
  tr:nth-child(even) {{ background: #1e293b; }}
  .badge {{ padding: 3px 10px; border-radius: 10px; color: #fff; font-weight: bold; }}
</style></head><body>
<h1>&#9889; ENDPOINT FINDER RAPORU</h1>
<h2>Hedef: {html.escape(motor.hedef)}</h2>
<p>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
   Sure: {time.time() - baslangic:.2f} sn |
   Endpoint: {len(motor.sonuclar)}</p>
<table><tr><th>Durum</th><th>URL</th><th>Tip</th><th>Boyut</th></tr>
{''.join(satirlar)}
</table></body></html>"""
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write(dokuman)
    print(f"{G}[+] HTML raporu yazildi -> {dosya_adi}{S}")

# ============================================================
#  INTERAKTIF SIHIRBAZ (kullaniciya tek tek sorar)
# ============================================================
def soru_sor(soru, bos_izin=False, ornek=""):
    """Kullaniciya soru sor, girdisini dondur."""
    ek = f" (ornek: {ornek})" if ornek else ""
    while True:
        cevap = input(f"\n{M}?{S} {soru}{Y}{ek}{S}\n> ").strip()
        if cevap or bos_izin:
            return cevap
        print(f"{R}[!] Bos birakamazsin, tekrar dene.{S}")


def url_sor():
    """URL al. Scheme yoksa https=1 http=2 diye sor, tamamla."""
    while True:
        ham = soru_sor("Hedef web adresini gir", ornek="www.cia.gov")
        if "." not in ham:
            print(f"{R}[!] Bu adres gecersiz gorunuyor, ornek gibi yaz.{S}")
            continue

        # scheme yoksa kullaniciya sor
        if not ham.startswith(("http://", "https://")):
            print(f"\n{C}[>]{S} Adreste protokol yok, tamamlamak icin sec:")
            print(f"   {G}[1]{S} HTTPS  (guvenli, varsayilan)")
            print(f"   {Y}[2]{S} HTTP   (acik baglanti)")
            secim = input(f"{M}?{S} Secimin: ").strip()
            if secim == "2":
                tam = "http://" + ham
            else:
                tam = "https://" + ham
        else:
            tam = ham

        if not tam.startswith(("http://", "https://")):
            print(f"{R}[!] Protokol taninmadi, tekrar dene.{S}")
            continue
        return tam


def dosya_sor():
    """Dosya adi + format (JSON/HTML/TXT) sor."""
    isim = soru_sor("Rapor dosyasinin adi ne olsun", ornek="results")

    print(f"\n{C}[>]{S} Hangi formatta kaydedilsin:")
    print(f"   {G}[1]{S} JSON   (makine okumasi, en detayli)")
    print(f"   {C}[2]{S} HTML   (tarayicida acilir, suslu)")
    print(f"   {Y}[3]{S} TXT    (duz metin, hizli bakis)")
    secim = input(f"{M}?{S} Secimin: ").strip()

    uzanti = {1: ".json", 2: ".html", 3: ".txt"}.get(int(secim) if secim.isdigit() else 3, ".txt")

    # kullanici adin sonuna uzanti eklemisse onu kullan
    if isim.lower().endswith((".json", ".html", ".txt")):
        return isim
    return isim + uzanti


def verbose_sor():
    """Verbose mod acilsin mi (y/n)."""
    while True:
        cevap = input(f"\n{M}?{S} Verbose mod acilsin mi? {G}[y]{S}evet / {R}[n]{S}hayir\n> ").strip().lower()
        if cevap in ("y", "yes", "e", "evet"):
            return True
        if cevap in ("n", "no", "h", "hayir"):
            return False
        print(f"{R}[!] Sadece y veya n gir.{S}")


def thread_sor():
    """Thread sayisini al, 1-64 arasi zorla."""
    while True:
        cevap = soru_sor("Kac thread ile taransin", ornek="10")
        if cevap.isdigit() and 1 <= int(cevap) <= 64:
            return int(cevap)
        print(f"{R}[!] 1 ile 64 arasi bir sayi gir.{S}")


# ============================================================
#  SONUC GORSEL: renkli tablo + ozet
# ============================================================
def sonuc_tablosu(motor):
    """Endpointleri durum koduna gore renkli tablo halinde basar."""
    satirlar = []
    for url in sorted(motor.sonuclar):
        bilgi = motor.sonuclar[url]
        renkli = renkli_durum(bilgi["kod"])
        satirlar.append(
            f"  {renkli}{str(bilgi['kod']):>4}{S}  {G}{bilgi['boyut']:>8}{S}  {C}{bilgi['tip'][:24]:<24}{S}  {url}"
        )

    genislik = max((_uzunluk(s) for s in satirlar), default=60) + 4
    cizgi = "=" * genislik
    print(f"\n{G}{cizgi}{S}")
    print(f"{G}  DURUM   BOYUT   TIP                     ENDPOINT{S}")
    print(f"{G}{cizgi}{S}")
    for s in satirlar:
        print(s)
    print(f"{G}{cizgi}{S}")


def ozet_goster(motor, baslangic):
    """Tarama sonrasi istatistik ozeti."""
    sure = time.time() - baslangic
    kodlar = [motor.sonuclar[u]["kod"] for u in motor.sonuclar]
    bulunan = {200: 0, 201: 0, 301: 0, 302: 0, 403: 0, 404: 0, 500: 0}

    print(f"\n{M}== OZET =={S}")
    print(f"{G}[+]{S} Hedef           : {motor.hedef}")
    print(f"{G}[+]{S} Sure            : {sure:.2f} sn")
    print(f"{G}[+]{S} Gezilen sayfa   : {len(motor.gezilenler)}")
    print(f"{G}[+]{S} Bulunan endpoint: {len(motor.endpointler)}")
    print(f"{G}[+]{S} Durum kontrol   : {len(motor.sonuclar)} adet")
    print(f"{G}[+]{S} JS dosyasi      : {len(motor.js_dosyalari)}")
    print(f"{G}[+]{S} Harici domain   : {len(motor.harici_domainler)}")

    if kodlar:
        canli = sum(1 for k in kodlar if 200 <= k < 300)
        yonlen = sum(1 for k in kodlar if 300 <= k < 400)
        hata4 = sum(1 for k in kodlar if 400 <= k < 500)
        hata5 = sum(1 for k in kodlar if k >= 500)
        erisilemez = sum(1 for k in kodlar if k == 0)
        print(f"{G}[+]{S} Canli (2xx)    : {canli}")
        print(f"{C}[+]{S} Yonlendirme    : {yonlen}")
        print(f"{Y}[+]{S} Istek hatasi   : {hata4}")
        print(f"{R}[+]{S} Sunucu hatasi  : {hata5}")
        print(f"{R}[-]{S} Erisilemeyen   : {erisilemez}")


def main():
    while True:
        banner_goster()
        bilgi_karti()

        print(f"\n{C}[>]{S} {W}Tarama ayarlari sihirbazi basliyor...{S}")
        time.sleep(0.5)

        hedef = url_sor()
        dosya = dosya_sor()
        verbose = verbose_sor()
        thread = thread_sor()

        # son bir onay + ozet
        print(f"\n{G}{'=' * 58}{S}")
        print(f"{G}  TARAMA PLANI:{S}")
        print(f"{G}  Hedef   :{S} {hedef}")
        print(f"{G}  Rapor   :{S} {dosya}")
        print(f"{G}  Verbose :{S} {'ACIK' if verbose else 'KAPALI'}")
        print(f"{G}  Thread  :{S} {thread}")
        print(f"{G}{'=' * 58}{S}")

        baslangic = time.time()

        if verbose:
            print(f"{C}[*]{S} Verbose mod acik, her adim yavaslatilarak gosteriliyor...")
            time.sleep(0.3)

        motor = KesifMotoru(
            hedef,
            verbose=verbose,
            thread_sayisi=thread
        )

        motor.calistir()

        sonuc_tablosu(motor)
        ozet_goster(motor, baslangic)

        # raporu secilen formata gore yaz
        if dosya.endswith(".json"):
            rapor_json(dosya, motor, baslangic)
        elif dosya.endswith(".html"):
            rapor_html(dosya, motor, baslangic)
        else:
            rapor_txt(dosya, motor, baslangic)

        print(f"\n{G}[✓]{S} Tarama tamamlandi. Rapor -> {dosya}")
        print(f"{M}Harbici buradayiz lan! {S}{Y}Iyı avlar.{S}\n")

        # ----------------------------------------------------
        # ANA MENU / CIKIS
        # ----------------------------------------------------
        while True:
            secim = input(
                f"{M}?{S} Ana Menuye donmek ister misin? "
                f"{G}[Y]{S} Evet / {R}[N]{S} Hayir\n> "
            ).strip().lower()

            if secim in ("y", "yes", "e", "evet"):
                # main while dongusunun basina doner.
                # banner_goster() zaten ekrani temizliyor.
                break

            if secim in ("n", "no", "h", "hayir"):
                print(f"\n{C}[*]{S} Program kapatiliyor...")
                return

            print(f"{R}[!] Sadece Y veya N gir.{S}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Y}[!]{S} Kullanici cikti. Gule gule!{S}")
