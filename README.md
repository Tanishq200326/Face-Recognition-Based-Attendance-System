# Face Recognition-Based Attendance System

A web-based application that automates attendance tracking using biometric face recognition, built with Flask, OpenCV, and SQLite.

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [Contributors](#contributors)
- [License](#license)

## Project Overview

This project provides a robust solution for efficient, contactless, and automated attendance management for educational institutions and workplaces. It leverages real-time face recognition to accurately record user attendance using only a webcam, thereby reducing errors and the risk of proxy attendance.

## Features

- Admin and student role-based access
- Secure login for both roles
- Add new students with face image capture
- Train and store facial recognition models
- Real-time face recognition attendance marking
- Attendance records export (CSV/Excel)
- Dashboard to view all users, attendance logs, and filter by date

## Technologies Used

- **Frontend:** HTML, CSS, Bootstrap
- **Backend:** Flask (Python)
- **Computer Vision:** OpenCV, Dlib, Face Recognition API
- **Database:** SQLite/MySQL
- **ML Model Storage:** Joblib
- **Other:** Webcam for face capture (HD 720p recommended)

## Installation

1. **Clone the repository:**
- git clone https://github.com/Tanishq200326/Face-Recognition-Based-Attendance-System.git
- cd Face-Recognition-Based-Attendance-System

2. **Install dependencies:**
- pip install -r requirements.txt

3. **Configure database:**
- Default: SQLite (`attendance.db` created at runtime)

4. **Run the application:**
- python app.py

## Usage

- **Admin Login:** Username: `admin`, Password: `password123`
- **Student Login:** Roll number serves as both username and password
- **Register New Users:** Admin can capture face images and register students
- **Mark Attendance:** Click "Take Attendance," system will use webcam for recognition
- **Export Records:** Attendance logs can be downloaded as CSV/Excel

## Contributors

- Tanishq Prajapati 
- Hardik Prajapati 
- Nimish Kothari 
- Harshit Sahu 
- Project Guide: Dr. Parashu Ram Pal

## License

This repository is provided for academic and educational purposes. Please refer to the project documentation for details on usage restrictions and referencing.

