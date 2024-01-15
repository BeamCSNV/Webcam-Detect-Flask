# นำเข้าไลบรารี PostgreSQL
import postgresql

# เปิดการเชื่อมต่อกับฐานข้อมูล PostgreSQL
db = postgresql.open('pq://socio:socio2014@127.0.0.1:5432/face')

# สร้าง extension "cube" ใน PostgreSQL ถ้ายังไม่มีอยู่
db.execute("create extension if not exists cube;")

# ลบตารางชื่อ "vectors" ถ้ามีอยู่เดิม
db.execute("drop table if exists vectors")

# สร้างตาราง "vectors" ใหม่
# มีคอลัมน์ id, file, image_id, vec_low, และ vec_high
db.execute("create table vectors (id serial, file varchar, image_id numeric, vec_low cube, vec_high cube);")

# สร้างดัชนี (index) บนคอลัมน์ vec_low และ vec_high ของตาราง "vectors"
db.execute("create index vectors_vec_idx on vectors (vec_low, vec_high);")
