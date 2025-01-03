import cv2
import os
from flask import Flask, request, render_template, flash, redirect, url_for, session  
from datetime import date, datetime
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib
import re
from flask_sqlalchemy import SQLAlchemy

# Defining Flask App
app = Flask(__name__)
app.secret_key = 'supersecretekey'

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    attendances = db.relationship('Attendance', backref='user', cascade="all, delete-orphan", lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), db.ForeignKey('user.roll_number', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)


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



################## ROUTING FUNCTIONS #########################

# Route to home page
@app.route('/home')
def home():
    if not session.get('logged_in') == 'admin':  # Check if the user is admin
        flash('Please log in as an admin to access this page.')
        return redirect(url_for('login'))

    names, rolls, times, l = extract_attendance()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)


# Route to list all users
@app.route('/listusers')
def listusers():
    users, names, rolls, l = getallusers()
    print(users)
    return render_template('listusers.html', users=users, names=names, rolls=rolls, l=l, totalreg=totalreg(), datetoday2=datetoday2)


# Route to delete a user
@app.route('/deleteuser', methods=['GET'])
def deleteuser():
    user_id = request.args.get('user_id')
    deletefolder(user_id)

    if not os.listdir('static/faces/'):
        if os.path.exists('static/face_recognition_model.pkl'):
            os.remove('static/face_recognition_model.pkl')

    try:
        train_model()
    except:
        pass

    return redirect(url_for('listusers'))


# Predefined admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password123'

# Route for Admin login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Admin username
        password = request.form.get('password')  # Admin password

        # Check for Admin login
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = 'admin'
            return redirect(url_for('home'))  # Redirect to the admin home page

        # Check for Student login (using roll number as username and password)
        student = User.query.filter_by(roll_number=password).first()  # 'username' is roll number for students
        if student and username == student.name and password == student.roll_number:  # Roll number is both the username and password
            session['logged_in'] = 'student'
            session['student_roll'] = student.roll_number
            return redirect(url_for('user_attendance', roll_number=student.roll_number))  # Redirect to student attendance page

        flash('Invalid username or password. Please try again.')
        return redirect(url_for('login'))  # Redirect to login if credentials are incorrect

    return render_template('admin_login.html')



# Route to view attendance of a specific user
@app.route('/user_attendance/<roll_number>', methods=['GET'])
def user_attendance(roll_number):
    # Check if the user is logged in as a student or admin
    if 'logged_in' not in session:
        flash("You are not authorized to access this page.")
        return redirect(url_for('login'))  # Redirect if not logged in

    user_role = session.get('logged_in')
    
    # If admin is logged in, they can view any student's attendance
    if user_role == 'admin':
        user = User.query.filter_by(roll_number=roll_number).first()
        if not user:
            flash("User not found.")
            return redirect(url_for('listusers'))
    
    # If student is logged in, they can only view their own attendance
    elif user_role == 'student' and session.get('student_roll') != roll_number:
        flash("You are not authorized to access this page.")
        return redirect(url_for('login'))  # Redirect if student tries to view someone else's attendance
    
    # Fetch user and attendance records for the correct user
    user = User.query.filter_by(roll_number=roll_number).first()
    if not user:
        flash("User not found.")
        return redirect(url_for('listusers'))

    # Get start and end date parameters from the query string
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Fetch all attendance records for the user
    attendance_records = Attendance.query.filter_by(roll_number=roll_number).all()

    # If start and end dates are provided, filter attendance records by date range
    if start_date and end_date:
    # Convert start and end dates to the Indian format ("%d-%m-%Y")
        start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%m-%Y")

        # Filter records by the new date format
        attendance_records = [
            record for record in attendance_records
            if datetime.strptime(start_date, "%d-%m-%Y") <= datetime.strptime(record.date, "%d-%m-%Y") <= datetime.strptime(end_date, "%d-%m-%Y")
        ]


    return render_template('user_attendance.html', user=user, attendance_records=attendance_records, start_date=start_date, end_date=end_date)


# Route to start the attendance
@app.route('/start', methods=['GET'])
def start():
    names, rolls, times, l = extract_attendance()

    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2, mess='There is no trained model in the static folder. Please add a new face to continue.')

    ret = True
    cap = cv2.VideoCapture(0)
    while ret:
        ret, frame = cap.read()
        if len(extract_faces(frame)) > 0:
            (x, y, w, h) = extract_faces(frame)[0]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (86, 32, 251), 1)
            cv2.rectangle(frame, (x, y), (x+w, y-40), (86, 32, 251), -1)
            face = cv2.resize(frame[y:y+h, x:x+w], (50, 50))
            identified_person = identify_face(face.reshape(1, -1))[0]
            user_name, user_roll = identified_person.split('_')
            if User.query.filter_by(name=user_name, roll_number=user_roll).first():
                add_attendance(user_roll)
            cv2.putText(frame, f'{identified_person}', (x+5, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow('Attendance', frame)
        if cv2.waitKey(1) == 27:
            break
    cap.release()
    cv2.destroyAllWindows()
    names, rolls, times, l = extract_attendance()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)



# Route to add a new user
nimgs = 10

@app.route('/add', methods=['GET', 'POST'])
def add():
    newusername = request.form['newusername']
    newuserid = request.form['newuserid']

    # Validate the user ID format
    if not re.fullmatch(r"[0-9]{4}[A-Za-z]{2}[0-9]{6}", newuserid):
        flash("Invalid User ID format. Please use the format: 0198CS211108.")
        return redirect(url_for('home'))

    if User.query.filter_by(roll_number=newuserid).first():
        flash("User with this Roll Number already exists.")
        return redirect(url_for('home'))

    user = User(name=newusername, roll_number=newuserid)
    db.session.add(user)
    db.session.commit()

    userimagefolder = f'static/faces/{newusername}_{newuserid}'
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)

    i, j = 0, 0
    cap = cv2.VideoCapture(0)
    while 1:
        _, frame = cap.read()
        faces = extract_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
            cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
            if j % 5 == 0:
                name = newusername+'_'+str(i)+'.jpg'
                cv2.imwrite(userimagefolder+'/'+name, frame[y:y+h, x:x+w])
                i += 1
            j += 1
        if j == nimgs*5:
            break
        cv2.imshow('Adding new User', frame)
        if cv2.waitKey(1) == 27:
            break
    cap.release()
    cv2.destroyAllWindows()
    print('Training Model')
    train_model()
    names, rolls, times, l = extract_attendance()
    return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2)


# Route for Admin logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Clear login session
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))


# Route for student logout
@app.route('/student_logout')
def student_logout():
    session.pop('logged_in', None)
    session.pop('student_roll', None)
    return redirect(url_for('login'))  # Redirect to login page after student logout


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
