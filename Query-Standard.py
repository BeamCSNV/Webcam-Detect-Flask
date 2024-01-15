import cv2
import face_recognition
import os
import postgresql

directory = os.path.dirname(__file__)


# db = postgresql.open('pq://socio:socio2014@127.0.0.1:5432/face')
db = postgresql.open('pq://socio:socio2014@124.109.2.123:5432/face')

def open_cam_rtsp(uri, width, height, latency):
    gst_str = ("rtspsrc location={} latency={} ! application/x-rtp,media=video ! rtph264depay ! h264parse ! nvv4l2decoder ! "
               "nvvidconv ! video/x-raw,width=(int){},height=(int){}, format=(string)BGRx ! videorate ! video/x-raw,framerate=2/1 ! "
               "appsink sync=false").format(uri, latency, width, height)
   
    return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

directory = os.path.dirname(__file__)
    #capture = cv2.VideoCapture(os.path.join(directory, "image.jpg")) 
capture = open_cam_rtsp('rtsp://admin:admin@192.168.1.120:8554/live',640,480,10)     
#capture = open_cam_rtsp('rtsp://admin:socio2014@192.168.88.206:554/Streaming/Channels/101',1200,680,10)     

if not capture.isOpened():
        exit()
    
boxes = ""
weights = os.path.join(directory, "face_detection_yunet_2023mar.onnx")
face_detector = cv2.FaceDetectorYN_create(weights, "", (0, 0),0.8,0.3,5000,5,6)
currentname = "unknown"


while True:
        result, frame = capture.read()
        if result is False:
            cv2.waitKey(0)
            break
        
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


       
        
        height, width, _ = frame.shape
        face_detector.setInputSize((width, height))

        _, faces = face_detector.detect(frame)
        faces = faces if faces is not None else []
        print("===============================================")

        for face in faces:
            box = list(map(int, face[:4]))
            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]
            confidence = face[14]
#            print(confidence)

            boxes = [(y, x + w, y + h, x)]
            #boxes = [(y-40, x + w+20, y + h+20, x-20)]

            encodings = face_recognition.face_encodings(frame, boxes)

            threshold = 0.5
            if len(encodings) > 0 and confidence>0.6:
                query = "SELECT id, file, image_id,student_name FROM vectors WHERE sqrt(power(CUBE(array[{}]) <-> vec_low, 2) + power(CUBE(array[{}]) <-> vec_high, 2)) <= {} ".format(
                    ','.join(str(s) for s in encodings[0][0:64]),
                    ','.join(str(s) for s in encodings[0][64:128]),
                    threshold,
                ) + \
                        "ORDER BY sqrt(power(CUBE(array[{}]) <-> vec_low, 2) + power(CUBE(array[{}]) <-> vec_high, 2)) ASC".format(
                            ','.join(str(s) for s in encodings[0][0:64]),
                            ','.join(str(s) for s in encodings[0][64:128])
                        )
                face_record = db.query(query)

                if len(face_record) > 0: 
                   #print(face_record[0]) 
                   #for i in face_record:
                   print(face_record)
                   print(len(face_record))
                   i = face_record[0]
                   name = str(i[3])
                   cv2.putText(frame, name, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    .8, (0, 255, 255), 2)
                   name = "Unknown"


                #face_records.append(process_face_matches(face_record))
                
                else:
                     name="Unknown"
                     cv2.putText(frame, name, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                            .8, (0, 255, 255), 2)
        print("===============================================")




        cv2.imshow("face detection", frame)
        key = cv2.waitKey(10)
        if key == ord('q'):
            break
    
cv2.destroyAllWindows()