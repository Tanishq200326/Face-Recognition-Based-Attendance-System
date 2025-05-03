import cv2
import os
from flask import Flask, request, render_template, flash, redirect, url_for, session  
from datetime import date, datetime
import re
from models import db, User, Attendance
from utils import totalreg, extract_faces, get_face_embedding, identify_face, train_model, extract_attendance, add_attendance, getallusers, deletefolder


# Defining Flask App
app = Flask(__name__)
app.secret_key = 'supersecretekey'

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db.init_app(app)

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



################## ROUTING FUNCTIONS #########################

import pandas as pd  # Make sure to install: pip install pandas openpyxl

# Route to download attendance for a specific user
@app.route('/download_attendance/<roll_number>')
def download_attendance(roll_number):
    if 'logged_in' not in session:
        flash("You are not authorized to access this page.")
        return redirect(url_for('login'))

    format = request.args.get('format', 'csv')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    user = User.query.filter_by(roll_number=roll_number).first()
    if not user:
        flash("User not found.")
        return redirect(url_for('listusers'))

    attendance_records = Attendance.query.filter_by(roll_number=roll_number).all()

    # Filter by date if specified
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            attendance_records = [
                record for record in attendance_records
                if start_dt <= datetime.strptime(record.date, "%d-%m-%Y") <= end_dt
            ]
        except ValueError:
            flash("Invalid date format.")
            return redirect(url_for('listusers'))


    # Prepare DataFrame
    data = [{
        'Name': user.name,
        'Roll Number': user.roll_number,
        'Date': record.date,
        'Time': record.time
    } for record in attendance_records]

    df = pd.DataFrame(data)

    if format == 'excel':
        excel_path = f'static/Attendance Records/Attendance_{roll_number}.xlsx'
        output = pd.ExcelWriter(excel_path, engine='openpyxl')
        df.to_excel(output, index=False, sheet_name='Attendance')
        output.close()
        return redirect(f'/{excel_path}')
    else:
        csv_path = f'static/Attendance Records/Attendance_{roll_number}.csv'
        df.to_csv(csv_path, index=False)
        return redirect(f'/{csv_path}')




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



@app.route('/user_attendance/<roll_number>', methods=['GET'])
def user_attendance(roll_number):
    if 'logged_in' not in session:
        flash("You are not authorized to access this page.")
        return redirect(url_for('login'))

    user_role = session.get('logged_in')

    # Access control
    if user_role == 'admin':
        user = User.query.filter_by(roll_number=roll_number).first()
    elif user_role == 'student' and session.get('student_roll') == roll_number:
        user = User.query.filter_by(roll_number=roll_number).first()
    else:
        flash("You are not authorized to access this page.")
        return redirect(url_for('login'))

    if not user:
        flash("User not found.")
        return redirect(url_for('listusers'))

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    attendance_records = Attendance.query.filter_by(roll_number=roll_number).all()

    if start_date and end_date:
        try:
            # Convert to datetime objects
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # Filter attendance records using the original format in DB
            attendance_records = [
                record for record in attendance_records
                if start_dt <= datetime.strptime(record.date, "%d-%m-%Y") <= end_dt
            ]
        except ValueError:
            flash("Invalid date format.")
            return redirect(url_for('user_attendance', roll_number=roll_number))

    return render_template(
        'user_attendance.html',
        user=user,
        attendance_records=attendance_records,
        start_date=start_date,
        end_date=end_date
    )

# Route to start the attendance
@app.route('/start', methods=['GET'])
def start():
    names, rolls, times, l = extract_attendance()

    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template('home.html', names=names, rolls=rolls, times=times, l=l, totalreg=totalreg(), datetoday2=datetoday2, mess='There is no trained model in the static folder.')

    cap = cv2.VideoCapture(1)   # 0 for built-in camera, 1 for external camera
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        faces = extract_faces(frame)
        for (x, y, w, h) in faces:
            face_img = frame[y:y+h, x:x+w]
            embedding = get_face_embedding(face_img)
            if embedding is not None:
                identified_person = identify_face(embedding)[0]
                if identified_person == 'Unknown':
                    text = 'Unknown User'
                else:
                    user_name, user_roll = identified_person.split('_')
                    if User.query.filter_by(name=user_name, roll_number=user_roll).first():
                        add_attendance(user_roll)
                        text = f'{identified_person}'
                    else:
                        text = 'Unknown User'
            else:
                text = 'No Face Detected'

            cv2.rectangle(frame, (x, y), (x+w, y+h), (86, 32, 251), 1)
            cv2.rectangle(frame, (x, y), (x+w, y-40), (86, 32, 251), -1)
            cv2.putText(frame, text, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

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
    cap = cv2.VideoCapture(2)  # 0 for built-in camera, 2 for external camera
    while True:
        _, frame = cap.read()
        faces = extract_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
            cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2)
            if j % 5 == 0:
                name = newusername + '_' + str(i) + '.jpg'
                cv2.imwrite(userimagefolder + '/' + name, frame[y:y+h, x:x+w])
                i += 1
            j += 1
        if j == nimgs * 5:
            break
        cv2.imshow('Adding new User', frame)
        if cv2.waitKey(1) == 27:
            break
    cap.release()
    cv2.destroyAllWindows()

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
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))  # Redirect to login page after student logout


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)