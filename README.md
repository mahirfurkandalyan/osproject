# Mini Mobile OS Simulator

Python ve Flask ile gelistirilmis interaktif mini mobil isletim sistemi simulatoru.

Bu proje; process yonetimi, FIFO ve Round Robin scheduling, memory pressure, file I/O blocking, lock conflict, priority inversion ve controlled failure senaryolarini web arayuzu uzerinden gostermektedir.

## Gereksinimler

- Python 3.10 veya uzeri
- pip
- Modern bir web tarayicisi

## Projeyi Indirme

```powershell
git clone https://github.com/mahirfurkandalyan/osproject.git
cd osproject
```

## Kurulum

Windows PowerShell icin:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS veya Linux icin:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Calistirma

Windows PowerShell:

```powershell
python app.py
```

macOS veya Linux:

```bash
python3 app.py
```

Uygulama acildiktan sonra tarayicida su adresi acin:

```text
http://127.0.0.1:5000
```

## Arayuzdeki Ana Butonlar

- `Open App`: Yeni bir mobil uygulama process'i olusturur.
- `Close App`: Aktif process'lerden birini sonlandirir.
- `Switch Scheduler`: FIFO ve Round Robin scheduler arasinda gecis yapar.
- `Simulate File I/O`: Bir process'i file I/O sebebiyle BLOCKED durumuna alir.
- `Simulate Memory Pressure`: RAM kullanimini artirir ve gerekirse pressure handler process sonlandirir.
- `Simulate Lock Conflict`: Shared resource uzerinde lock conflict olusturur.
- `Priority Inversion`: Priority inversion ve priority inheritance senaryosunu baslatir.
- `Trigger Failure Scenario`: Kontrollu process crash senaryosu olusturur.
- `Reset System`: Simulasyonu temiz baslangic durumuna dondurur.

## Demo Akisi

1. `Open App` butonuna birkac kez basarak birden fazla process olusturun.
2. Process tablosunda `READY` ve `RUNNING` durumlarini inceleyin.
3. `Switch Scheduler` ile FIFO ve Round Robin davranisini karsilastirin.
4. `Simulate File I/O` ile bir process'in `BLOCKED` durumuna gecmesini ve scheduler'in baska process secmesini izleyin.
5. `Simulate Lock Conflict` ile bir process'in shared resource bekledigi icin block olmasini inceleyin.
6. `Simulate Memory Pressure` ile RAM doldugunda pressure handler'in dusuk oncelikli process'i oldurmesini takip edin.
7. `Priority Inversion` ile dusuk oncelikli process'in priority inheritance ile boost edilmesini gorun.
8. `Trigger Failure Scenario` ile kontrollu crash ve termination davranisini gosterin.
9. Kernel log panelinden tum kararlarin sebep-sonuc olarak yazildigini kontrol edin.

## Beklenen Log Ornekleri

```text
[Memory] RAM full -> Killing P3 (priority=2, lowest-priority candidate, selected by pressure handler)
[File] P1 started file operation (delete notes_1.txt)
[File] P1 BLOCKED due to file I/O
[Lock] P3 BLOCKED waiting for storage (held by P1)
[Scheduler] Switched P1 -> P2 (ROUND_ROBIN, quantum expired)
[Priority] Priority inheritance applied: P4 boosted from 1 -> 5
```

## Sorun Giderme

Port 5000 kullaniliyorsa uygulama baslamayabilir. Bu durumda once eski Flask surecini kapatin veya `app.py` icindeki port ayarini degistirin.

Windows PowerShell sanal ortam aktivasyonuna izin vermezse su komutu calistirin:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Sonra tekrar:

```powershell
.venv\Scripts\Activate.ps1
```

## Proje Yapisi

```text
app.py                         Flask backend ve API route'lari
mobile_os_sim/core/models.py   Process, state ve lock modelleri
mobile_os_sim/core/scheduler.py FIFO ve Round Robin scheduler
mobile_os_sim/core/system.py   OS simulasyon motoru
templates/index.html           Web arayuzu
static/app.js                  Frontend API ve render logic
static/style.css               UI tasarimi
requirements.txt               Python bagimliliklari
```
