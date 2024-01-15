import psycopg2

# เปิดการเชื่อมต่อกับฐานข้อมูล PostgreSQL
conn = psycopg2.connect(dbname='DB-Face', user='postgres', password='Beam12345', host='127.0.0.1', port=5432)

# สร้าง cursor
cursor = conn.cursor()

# สั่ง execute คำสั่ง SQL
cursor.execute("create extension if not exists cube;")
cursor.execute("drop table if exists vectors")
cursor.execute("create table vectors (id serial, file varchar, image_id numeric, vec_low cube, vec_high cube);")
cursor.execute("create index vectors_vec_idx on vectors (vec_low, vec_high);")

# commit การเปลี่ยนแปลง
conn.commit()

# ปิด cursor และ connection
cursor.close()
conn.close()
