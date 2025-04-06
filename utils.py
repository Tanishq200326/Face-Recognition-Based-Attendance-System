import os
import cv2
import joblib
import numpy as np
from datetime import date, datetime
from sklearn.neighbors import KNeighborsClassifier
import face_recognition
from models import User, Attendance, db

datetoday = date.today().strftime("%d-%m-%Y")
datetoday2 = date.today().strftime("%d-%B-%Y")

face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

if not os.path.isdir('static'):
    os.makedirs('static')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')


def totalreg():
    return User.query.count()


def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []


def get_face_embedding(img):
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_img)
    if encodings:
        return encodings[0]
    return None


def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    distances, indices = model.kneighbors([facearray], n_neighbors=1)
    print("Distance:", distances[0][0])
    
    if distances[0][0] > 0.5:  # fine-tune this threshold as needed
        return ['Unknown']
    return model.predict([facearray])


def train_model():
    embeddings = []
    labels = []
    users = User.query.all()
    for user in users:
        user_folder = f'static/faces/{user.name}_{user.roll_number}'
        for imgname in os.listdir(user_folder):
            img_path = os.path.join(user_folder, imgname)
            img = cv2.imread(img_path)
            embedding = get_face_embedding(img)
            if embedding is not None:
                embeddings.append(embedding)
                labels.append(f'{user.name}_{user.roll_number}')
    if embeddings:
        knn = KNeighborsClassifier(n_neighbors=3)
        knn.fit(embeddings, labels)
        joblib.dump(knn, 'static/face_recognition_model.pkl')


def extract_attendance():
    records = Attendance.query.filter_by(date=datetoday).all()
    rolls = [record.roll_number for record in records]
    names = [User.query.filter_by(roll_number=roll).first().name for roll in rolls]
    times = [record.time for record in records]
    l = len(records)
    return names, rolls, times, l


def add_attendance(roll_number):
    current_time = datetime.now().strftime("%H:%M:%S")
    if not Attendance.query.filter_by(roll_number=roll_number, date=datetoday).first():
        attendance = Attendance(roll_number=roll_number, date=datetoday, time=current_time)
        db.session.add(attendance)
        db.session.commit()


def getallusers():
    users = User.query.all()
    names = [user.name for user in users]
    rolls = [user.roll_number for user in users]
    l = len(users)
    return users, names, rolls, l


def deletefolder(user_id):
    user = User.query.get(user_id)
    if not user:
        return
    user_folder = f'static/faces/{user.name}_{user.roll_number}'
    if os.path.isdir(user_folder):
        for pic in os.listdir(user_folder):
            os.remove(os.path.join(user_folder, pic))
        os.rmdir(user_folder)
    db.session.delete(user)
    db.session.commit()
