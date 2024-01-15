# นำเข้าโมดูลและไลบรารีที่จำเป็น
from flask import Flask, request, jsonify, make_response
from werkzeug.utils import secure_filename
import dlib
import cv2
import face_recognition
import os
import postgresql

# สร้างแอปพลิเคชัน Flask
app = Flask(__name__)

# กำหนดค่าขนาดสูงสุดของไฟล์ที่อัปโหลดและนิยามนามสกุลไฟล์ที่ยอมรับ
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.jpeg']
app.config['UPLOAD_PATH'] = '/home/jetson/Documents/db/upload/'

# ฟังก์ชันเพื่อบันทึกข้อมูลใบหน้าลงในฐานข้อมูล PostgreSQL
def save_face_to_db(local_filename, remote_file_url, image_id, name):
    # สร้างตัวตรวจหน้าใบ HOG โดยใช้คลาสที่มีอยู่ใน dlib
    face_detector = dlib.get_frontal_face_detector()
    print(name)
    
    # โหลดรูปภาพ
    image = cv2.imread(local_filename)

    # รันตัวตรวจหน้าใบ HOG บนข้อมูลรูปภาพ
    detected_faces = face_detector(image, 1)
    print("พบ {} ใบหน้าในไฟล์รูปภาพ {}".format(len(detected_faces), local_filename))

    # เชื่อมต่อกับฐานข้อมูล PostgreSQL
    db = postgresql.open('pq://socio:socio2014@124.109.2.123:5432/face')

    # วนลูปผ่านทุกใบหน้าที่พบในรูปภาพ
    face_ids = []
    for i, face_rect in enumerate(detected_faces):
        # ใบหน้าที่พบถูกส่งคืนเป็นออบเจกต์ที่มีพิกัด
        print("- พบใบหน้าที่ #{} ที่ Left: {} Top: {} Right: {} Bottom: {}".format(i, face_rect.left(), face_rect.top(),
                                                                                 face_rect.right(), face_rect.bottom()))
        # ครอบตัดใบหน้าจากรูปภาพ
        crop = image[face_rect.top():face_rect.bottom(), face_rect.left():face_rect.right()]
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        
        # สร้างลักษณะใบหน้า (encodings) โดยใช้ไลบรารี face_recognition
        encodings = face_recognition.face_encodings(crop)
        print(encodings[0])

        if len(encodings) > 0:
            # สร้างคำสั่ง SQL เพื่อแทรกข้อมูลใบหน้าลงในฐานข้อมูล
            query = "INSERT INTO vectors (file, image_id, student_name, vec_low, vec_high) VALUES ('{}', {}, '{}', CUBE(array[{}]), CUBE(array[{}])) RETURNING id".format(
                remote_file_url,
                image_id,
                name,
                ','.join(str(s) for s in encodings[0][0:64]),
                ','.join(str(s) for s in encodings[0][64:128]),
            )

            # ประมวลผลคำสั่งและเก็บรหัสใบหน้าที่ส่งคืน
            response = db.query(query)
            face_ids.append(response[0][0])
    return face_ids

# กำหนดเส้นทางเพื่อจัดการ POST requests สำหรับการอัปโหลดรูปใบหน้า
@app.route("/faces", methods=['POST'])
def faces():
    uploaded_file = request.files['file']
    file_url = request.form.get('url', False)
    name = request.form.get('name', False)
    image_id = request.form.get('image_id', 0)
    filename = secure_filename(uploaded_file.filename)
    
    # ตรวจสอบความถูกต้องของข้อมูลที่รับเข้ามา
    if filename != '' and file_url and image_id:
        file_ext = os.path.splitext(file_url)[1]
        print(file_ext)

        # ตรวจสอบว่านามสกุลไฟล์ได้รับอนุญาตหรือไม่
        if file_ext in app.config['UPLOAD_EXTENSIONS']:
            file_path = os.path.join(app.config['UPLOAD_PATH'], filename)
            print(file_path)
            
            # บันทึกไฟล์ที่อัปโหลดไว้ที่ตำแหน่งที่กำหนด
            uploaded_file.save(file_path)
            
            # เรียกใช้ฟังก์ชันเพื่อบันทึกข้อมูลใบหน้าลงในฐานข้อมูล
            face_added = save_face_to_db(file_path, file_url, image_id, name)
            
            # ลบไฟล์ที่อัปโหลดหลังจากการประมวลผลเสร็จสิ้น
            os.remove(file_path)
            
            # ส่งคำตอบ JSON กลับไปยัง client ระบุสถานะของการประมวลผล
            if face_added:
                return make_response(jsonify(status='PROCESSED', ids=face_added), 201)
            else:
                return make_response(jsonify(status='FAILED'), 500)
    
    # ส่งคำตอบข้อผิดพลาดเมื่อข้อมูลไม่ถูกต้อง
    return make_response(jsonify(error='Invalid file or URL'), 400)

# รันแอปพลิเคชัน Flask ในโหมด debug
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=9000)
