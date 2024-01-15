from flask import Flask, render_template, Response
import cv2
import face_recognition
import os
import psycopg2

app = Flask(__name__)

# กำหนดตำแหน่งไดเรกทอรีของไฟล์ที่ทำงาน
directory = os.path.dirname(__file__)

# เชื่อมต่อกับฐานข้อมูล PostgreSQL
db = psycopg2.connect('dbname=DB-Face user=postgres password=Beam12345 host=127.0.0.1 port=5432')

# ฟังก์ชันสำหรับบันทึกใบหน้าลงในฐานข้อมูล
def save_face_to_database(encoding):
    # สร้างคำสั่ง SQL สำหรับการเพิ่มข้อมูลใบหน้าลงในฐานข้อมูล
    insert_query = "INSERT INTO vectors (vec_low, vec_high) VALUES (CUBE(array[{}]), CUBE(array[{}]))".format(
        ','.join(str(s) for s in encoding[0:64]),
        ','.join(str(s) for s in encoding[64:128])
    )

    # เริ่มการเพิ่มข้อมูลในฐานข้อมูล
    with db.cursor() as cursor:
        cursor.execute(insert_query)
    db.commit()

# ฟังก์ชันสำหรับเปิดกล้อง RTSP
def open_cam_rtsp(uri, width, height, latency):
    gst_str = ("rtspsrc location={} latency={} ! application/x-rtp,media=video ! rtph264depay ! h264parse ! nvv4l2decoder ! "
               "nvvidconv ! video/x-raw,width=(int){},height=(int){}, format=(string)BGRx ! videorate ! video/x-raw,framerate=2/1 ! "
               "appsink sync=false").format(uri, latency, width, height)
   
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

camera = cv2.VideoCapture(0)  # เลือกกล้องที่ต้องการ (0 คือกล้องเริ่มต้น)

# กำหนดตัวแปรสำหรับใช้ในการตรวจจับใบหน้า
boxes = ""
weights = os.path.join(directory, r"C:\Users\HP\Desktop\Detect-SQL\Model\face_detection_yunet_2023mar.onnx")
face_detector = cv2.FaceDetectorYN_create(weights, "", (0, 0), 0.8, 0.3, 5000, 5, 6)
currentname = "unknown"

# เซ็ตตัวแปร detected_faces เพื่อเก็บชื่อใบหน้าที่ตรวจจับแล้ว
detected_faces = set()

# กำหนดตัวแปร name เป็น "unknown"
name = "unknown"

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break        
        else:
            # แปลงรูปภาพเป็น RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ดึงขนาดของภาพ
            height, width, _ = frame.shape
            face_detector.setInputSize((width, height))

            # ตรวจจับใบหน้าในภาพ
            _, faces = face_detector.detect(frame)
            faces = faces if faces is not None else []
            print("===============================================")
            
            # Loop สำหรับการประมวลผลทุกใบหน้า
            for face in faces:
                # ดึงข้อมูลของใบหน้า
                box = list(map(int, face[:4]))
                x, y, w, h = box
                confidence = face[14]
            
                # สร้างตัวแปร boxes สำหรับ face_recognition
                boxes = [(y, x + w, y + h, x)]
                
                # ดึงลักษณะของใบหน้า (face encoding)
                encodings = face_recognition.face_encodings(frame, boxes)
                
                # กำหนด threshold สำหรับการตรวจสอบใบหน้าในฐานข้อมูล
                threshold = 0.5
                if len(encodings) > 0 and confidence > 0.6:
                    # สร้าง query สำหรับค้นหาใบหน้าในฐานข้อมูล
                    query = "SELECT id, file, image_id FROM vectors WHERE sqrt(power(CUBE(array[{}]) <-> vec_low, 2) + power(CUBE(array[{}]) <-> vec_high, 2)) <= {} ".format(
                        ','.join(str(s) for s in encodings[0][0:64]),
                        ','.join(str(s) for s in encodings[0][64:128]),
                        threshold,
                    ) + \
                        "ORDER BY sqrt(power(CUBE(array[{}]) <-> vec_low, 2) + power(CUBE(array[{}]) <-> vec_high, 2)) ASC".format(
                            ','.join(str(s) for s in encodings[0][0:64]),
                            ','.join(str(s) for s in encodings[0][64:128])
                        )
                        
                    # เริ่มการค้นหาในฐานข้อมูล
                    with db.cursor() as cursor:
                        cursor.execute(query)
                        face_record = cursor.fetchall()

                    # สร้าง query สำหรับดึงข้อมูลที่เพิ่งถูกบันทึก
                    select_query = "SELECT id, file, image_id FROM vectors ORDER BY id DESC LIMIT 1"

                    # ทำการค้นหาข้อมูลในฐานข้อมูล
                    with db.cursor() as cursor:
                        cursor.execute(select_query)
                        latest_face_record = cursor.fetchone()
                      
                    # ตรวจสอบว่ามีข้อมูลหรือไม่
                    if latest_face_record:
                        print("ข้อมูลใบหน้าล่าสุด:")
                        print("ID:", latest_face_record[0])
                        print("File:", latest_face_record[1])
                        print("Image ID:", latest_face_record[2])
                    else:
                        print("ไม่พบข้อมูลใบหน้าในฐานข้อมูล")
                      
                    # ตรวจสอบว่าใบหน้านี้มีข้อมูลในฐานข้อมูลหรือไม่
                    if len(face_record) > 0:
                        print(face_record)
                        print(len(face_record))
                        i = face_record[0]
                        # ตรวจสอบว่ามี index ที่ 3 หรือไม่
                        if len(i) > 3:
                            name = str(i[3])
                            cv2.putText(frame, name, (x, y), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)
                        else:
                            print("ข้อมูลใบหน้าไม่ถูกต้อง")
                        name = "Unknown"
                    else:
                        # ตรวจสอบว่าใบหน้านี้ได้ถูกตรวจจับและบันทึกลงในฐานข้อมูลแล้วหรือไม่
                        if name not in detected_faces:
                            # บันทึกใบหน้าใหม่ลงในฐานข้อมูล
                            save_face_to_database(encodings[0])

                            # เพิ่มชื่อใบหน้าในเซ็ตเพื่อไม่ต้องแจ้งเตือนซ้ำ
                            detected_faces.add(name)
                            
                    # แสดงผลลัพธ์บนภาพ
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                    cv2.putText(frame, name, (x, y), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)

                    print("===============================================")
                      
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
