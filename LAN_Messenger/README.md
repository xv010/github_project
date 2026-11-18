# LAN Messenger

Python 3.11+ uchun lokal tarmoqdagi TCP Client–Server messenjer.

## Xususiyatlar
- `asyncio` TCP server; bir vaqtda kamida 30 mijoz uchun mo‘ljallangan.
- 4 baytli unsigned big-endian uzunlik prefiksi + UTF-8 JSON.
- Umumiy va shaxsiy xabarlar.
- Onlayn foydalanuvchilar ro‘yxati, system xabarlari va chat tarixi.
- SQLite (`messenger.db`) saqlash; WAL rejimi va tranzaksiyalar.
- Tkinter GUI; tarmoq alohida event loop/thread ichida, GUI yangilanishi `queue` orqali asosiy oqimda.
- O‘zbekcha Unicode matnlar.

## Talablar va ishga tushirish
Python 3.11 yoki yangiroq versiya kerak. Qo‘shimcha pip kutubxonasi shart emas.
Windows'da Tkinter Python o‘rnatilishi bilan birga keladi.

Server kompyuterida loyiha papkasida:
```powershell
py -3.11 server.py --host 0.0.0.0 --port 5000
```
Mijoz kompyuterlarida:
```powershell
py -3.11 client.py
```
GUI'da server kompyuterining LAN IP manzilini (masalan `192.168.1.100`), port `5000` va noyob username kiriting.

Server IP manzilini topish:
```powershell
ipconfig
```
Faol Ethernet/Wi-Fi adapteridagi `IPv4 Address` qiymatidan foydalaning. Server IP'sini `0.0.0.0` qilib client'ga kiritmang; bu faqat serverning barcha interfeyslarda tinglashi uchun.

## Windows Firewall
Administrator PowerShell oynasida:
```powershell
New-NetFirewallRule -DisplayName "LAN Messenger TCP 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Private
```
Faqat ishonchli Private LAN profilida ishlating. Kerak bo'lmaganda qoidani olib tashlash:
```powershell
Remove-NetFirewallRule -DisplayName "LAN Messenger TCP 5000"
```

## Protokol
Har bir frame: 4 bayt network byte order (big-endian) payload uzunligi, so‘ng UTF-8 JSON payload.
Server mijozni login paytida tasdiqlaydi; keyingi xabarlardagi `sender` maydoni e'tiborga olinmaydi — yuboruvchi serverdagi autentifikatsiya qilingan socket bilan bog‘lanadi.
Turlari: `login`, `logout`, `broadcast`, `private_message`, `user_list`, `system_message`, `error`. Qo‘shimcha boshqaruv turlari: `user_list_request`, `history_request`, serverdan `history` javobi.

## Ma'lumotlar bazasi
`users`: id, username, connected_at, last_seen.
`messages`: id, sender, receiver, message, message_type, timestamp.
Umumiy xabarlar va shaxsiy xabarlar saqlanadi. Tarixga umumiy xabarlar hamda foydalanuvchining o‘zi yuborgan/qabul qilgan shaxsiy xabarlar kiradi.

## Xavfsizlik chegaralari
Bu dastlabki versiya ishonchli LAN uchun. Username bilan kirish **haqiqiy autentifikatsiya emas**: parol, hisob egasini tekshirish, TLS shifrlash va server sertifikatini tekshirish mavjud emas. Shu sababli maxfiy yoki sezgir ma'lumot yubormang va internetga ochmang. Kuchliroq foydalanish uchun TLS, parol xeshlash, rate limiting va administrator nazorati qo‘shilishi kerak.

## Testlar
Loyiha papkasida:
```powershell
py -3.11 -m unittest discover -s tests -v
```
Testlar framing/UTF-8 va bir nechta client bilan broadcast/private, duplicate username hamda SQLite saqlashni tekshiradi.
