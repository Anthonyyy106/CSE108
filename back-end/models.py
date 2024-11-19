from flask_login import UserMixin

from config import db


class User(db.Model,UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    person_name = db.Column(db.String(80), nullable=False)

    # Relationship to enrollments
    enrollments = db.relationship('Enrollment', back_populates='user', lazy=True)


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(80), nullable=False)
    course_number = db.Column(db.String(15), nullable=False)
    professor = db.Column(db.String(80), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    enrolled_students = db.Column(db.Integer, default=0)  # Optional default value

    # Relationship to enrollments
    enrollments = db.relationship('Enrollment', back_populates='course', lazy=True)

    def has_capacity(self):
        return self.enrolled_students < self.capacity


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    # Relationships to User and Course
    user = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

    # Relationship to Student
    students = db.relationship('Student', back_populates='enrollment', lazy=True)


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.Integer, nullable=True)  # Optional, e.g., "A", "B+", etc.
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)

    # Relationship to Enrollment
    enrollment = db.relationship('Enrollment', back_populates='students')