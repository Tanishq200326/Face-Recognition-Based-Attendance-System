import os
import cv2
import joblib
import numpy as np
from datetime import date, datetime
from sklearn.neighbors import KNeighborsClassifier
from models import User, Attendance, db

# Saving Date today in 2 different formats
datetoday = date.today().strftime("%d-%m-%Y")
datetoday2 = date.today().strftime("%d-%B-%Y")

# Initializing VideoCapture object to access WebCam
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# If these directories don't exist, create them
if not os.path.isdir('static'):
    os.makedirs('static')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')


# Get total registered users
def totalreg():
    return User.query.count()


# Extract the face from an image
def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []


# Identify face using ML model
def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    return model.predict(facearray)

# Train the model on all faces available in faces folder
def train_model():
    faces = []
    labels = []
    users = User.query.all()
    for user in users:
        user_folder = f'static/faces/{user.name}_{user.roll_number}'
        for imgname in os.listdir(user_folder):
            img = cv2.imread(f'{user_folder}/{imgname}')
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(f'{user.name}_{user.roll_number}')
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces, labels)
    joblib.dump(knn, 'static/face_recognition_model.pkl')


# Extract attendance records
def extract_attendance():
    records = Attendance.query.filter_by(date=datetoday).all()
    rolls = [record.roll_number for record in records]
    names = [User.query.filter_by(roll_number=roll).first().name for roll in rolls]
    times = [record.time for record in records]
    l = len(records)
    return names, rolls, times, l


# Add attendance of a specific user
def add_attendance(roll_number):
    current_time = datetime.now().strftime("%H:%M:%S")
    if not Attendance.query.filter_by(roll_number=roll_number, date=datetoday).first():
        attendance = Attendance(roll_number=roll_number, date=datetoday, time=current_time)
        db.session.add(attendance)
        db.session.commit()

# Get all users
def getallusers():
    users = User.query.all()
    names = [user.name for user in users]
    rolls = [user.roll_number for user in users]
    l = len(users)
    return users, names, rolls, l

# Delete a user folder and remove from database
def deletefolder(user_id):
    user = User.query.get(user_id)
    if not user:
        return  # Handle case if user does not exist
    
    user_folder = f'static/faces/{user.name}_{user.roll_number}'
    if os.path.isdir(user_folder):
        pics = os.listdir(user_folder)
        for pic in pics:
            os.remove(f'{user_folder}/{pic}')
        os.rmdir(user_folder)
    
    db.session.delete(user)
    db.session.commit()
