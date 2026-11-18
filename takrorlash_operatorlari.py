import sqlite3
Ma'lumotlar bazasiga ulanish
conn = sqlite3.connect("qabul_tizimi.db") cursor = conn.cursor()
Foreign Key ni yoqish
cursor.execute("PRAGMA foreign_keys = ON")
1. ABITURIYENT
cursor.execute(""" CREATE TABLE IF NOT EXISTS abituriyent ( id INTEGER PRIMARY KEY AUTOINCREMENT, jshshir VARCHAR(14), passport_seriya VARCHAR(20), ism VARCHAR(50), familiya VARCHAR(50), tugilgan_sana DATE, telefon VARCHAR(20), email VARCHAR(100), manzil TEXT ) """)
2. QABUL_KOMPANIYALARI
cursor.execute(""" CREATE TABLE IF NOT EXISTS qabul_kompaniyalari ( id INTEGER PRIMARY KEY AUTOINCREMENT, nomi VARCHAR(100), oquv_yili VARCHAR(20), boshlanish_sana DATE, tugash_sana DATE, holat VARCHAR(30) ) """)
3. FAKULTETLAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS fakultetlar ( id INTEGER PRIMARY KEY AUTOINCREMENT, nomi VARCHAR(100), qisqartma VARCHAR(20) ) """)
4. YONALISHLAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS yonalishlar ( id INTEGER PRIMARY KEY AUTOINCREMENT, fakultet_id INTEGER, kod VARCHAR(20), nomi VARCHAR(100), talim_shakli VARCHAR(50), talim_tili VARCHAR(30), kvota INTEGER, FOREIGN KEY (fakultet_id) REFERENCES fakultetlar(id) )
""")
5. ARIZALAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS arizalar ( id INTEGER PRIMARY KEY AUTOINCREMENT, abituriyent_id INTEGER, kompaniya_id INTEGER, yonalish_id INTEGER, topshirilgan_sana DATE, tanlov_ustuvorligi VARCHAR(50), holat VARCHAR(30), FOREIGN KEY (abituriyent_id) REFERENCES abituriyent(id), FOREIGN KEY (kompaniya_id) REFERENCES qabul_kompaniyalari(id), FOREIGN KEY (yonalish_id) REFERENCES yonalishlar(id) ) """)
6. HUJJATLAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS hujjatlar ( id INTEGER PRIMARY KEY AUTOINCREMENT, ariza_id INTEGER, hujjat_turi VARCHAR(50), fayl_manzili TEXT, tekshiruv_holati VARCHAR(50), yuklangan_sana DATE, FOREIGN KEY (ariza_id) REFERENCES arizalar(id) ) """)
7. FANLAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS fanlar ( id INTEGER PRIMARY KEY AUTOINCREMENT, nomi VARCHAR(100), maksimal_ball DECIMAL(5,2) ) """)
8. IMTIHON_NATIJALARI
cursor.execute(""" CREATE TABLE IF NOT EXISTS imtihon_natijalari ( id INTEGER PRIMARY KEY AUTOINCREMENT, ariza_id INTEGER, fan_id INTEGER, imtihon_sana DATE, olingan_ball DECIMAL(5,2), holat VARCHAR(30), FOREIGN KEY (ariza_id) REFERENCES arizalar(id), FOREIGN KEY (fan_id) REFERENCES fanlar(id) ) """)
9. YAKUNIY_NATIJALAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS yakuniy_natijalar ( id INTEGER PRIMARY KEY AUTOINCREMENT, ariza_id INTEGER, jami_ball DECIMAL(6,2), reyting_orni INTEGER, qaror VARCHAR(50), elon_sana DATE, FOREIGN KEY (ariza_id) REFERENCES arizalar(id) ) """)
10. TOLOVLAR
cursor.execute(""" CREATE TABLE IF NOT EXISTS tolovlar ( id INTEGER PRIMARY KEY AUTOINCREMENT, ariza_id INTEGER, summa DECIMAL(12,2), tolov_sana DATE, tranzaksiya_kodi VARCHAR(100), holat VARCHAR(30), FOREIGN KEY (ariza_id) REFERENCES arizalar(id) ) """)
11. QABUL_BUYRUGI
cursor.execute(""" CREATE TABLE IF NOT EXISTS qabul_buyrugi ( id INTEGER PRIMARY KEY AUTOINCREMENT, yakuniy_natija INTEGER, buyruq_raqami VARCHAR(50), sana DATE, FOREIGN KEY (yakuniy_natija) REFERENCES yakuniy_natijalar(id) ) """)
O'zgarishlarni saqlash
conn.commit()
print("Abituriyentlarni qabul qilish tizimi muvaffaqiyatli yaratildi!")
Ma'lumotlar bazasini yopish
conn.close()
