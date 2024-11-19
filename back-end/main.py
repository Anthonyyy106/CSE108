from flask import request, jsonify, render_template, url_for, redirect, flash, session
from config import db, app
from models import User, Course, Enrollment, Student
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

#downgrade wtf froms, pip install wtforms==2.3.3

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Secure ModelView to restrict admin access
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_type == 'Admin'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('index'))

# Customized UserModelView
class UserModelView(SecureModelView):
    column_list = ('id', 'username', 'user_type', 'person_name')
    column_searchable_list = ('username', 'person_name')
    column_filters = ('user_type',)

    # Use 'form_args' to specify field-level arguments properly
    form_choices = {
        'user_type': [
            ('Admin', 'Admin'),
            ('Student', 'Student'),
            ('Teacher', 'Teacher'),
        ]
    }


# Customized CourseModelView
class CourseModelView(SecureModelView):
    column_list = ('id', 'course_name', 'course_number', 'professor', 'capacity', 'enrolled_students')
    column_searchable_list = ('course_name', 'course_number', 'professor')
    column_filters = ('professor',)

# Customized EnrollmentModelView
class EnrollmentModelView(SecureModelView):
    form_columns = ['user_id', 'course_id']  # Ensure only valid fields are used
    inline_models = [
        (User, dict(form_columns=['id', 'username'])),
        (Course, dict(form_columns=['id', 'course_name']))
    ]

    def on_model_change(self, form, model, is_created):
        if not model.user_id or not model.course_id:
            raise ValueError("Both user_id and course_id must be set for an Enrollment.")


# Customized StudentModelView
class StudentModelView(SecureModelView):
    column_list = ('id', 'student_name', 'grade', 'enrollment_id')
    column_searchable_list = ('student_name',)
    column_filters = ('grade',)
    can_delete = True  # Enable deletion
    form_columns = ['student_name', 'grade', 'enrollment_id']

# Initialize Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')
admin.add_view(UserModelView(User, db.session))
admin.add_view(CourseModelView(Course, db.session))
admin.add_view(SecureModelView(Enrollment, db.session))

app.secret_key = 'your_secret_key_here'

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/create_acc_page')
def create_acc_page():
    return render_template('create_acc.html')

@app.route('/all_courses')
def all_courses():
    return render_template('allCourses.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            if user.user_type == "Student":
                return redirect(url_for('studentview', username=username))
            elif user.user_type == "Teacher":
                return redirect(url_for('teacherview', username=username))
            elif user.user_type == "Admin":
                return redirect('/admin')
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/create_acc', methods=['POST'])
def create_account():
    username = request.form.get('username')
    person_name = request.form.get('person_name')
    password = request.form.get('password')
    user_type = request.form.get('user_type')

    if user_type not in ['Admin', 'Student', 'Teacher']:
        flash("Invalid user type selected.", "error")
        return redirect(url_for('create_acc_page'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Account already exists under this Username", "error")
        return redirect(url_for('create_acc_page'))

    new_user = User(username=username, password=password, user_type=user_type, person_name=person_name)
    db.session.add(new_user)
    db.session.commit()
    flash("Account created successfully! Please log in.", "success")
    return redirect(url_for('index'))

@app.route('/student/<username>')
@login_required
def studentview(username):
    user = User.query.filter_by(username=username).first()
    return render_template('studentview.html', person_name=user.person_name)

@app.route('/teacher/<username>')
@login_required
def teacherview(username):
    return render_template('teacherview.html')

@app.route('/get_all_courses', methods=['GET'])
@login_required
def get_all_courses():
    enrolled_course_ids = {
        enrollment.course_id for enrollment in Enrollment.query.filter_by(user_id=current_user.id).all()
    }
    all_courses_list = Course.query.all()
    return render_template('allCourses.html', courses=all_courses_list, enrolled_course_ids=enrolled_course_ids)

@app.route('/register_for_course/<int:course_id>', methods=['POST'])
@login_required
def register_for_course(course_id):
    course = Course.query.get(course_id)
    if course and course.has_capacity():
        course.enrolled_students += 1
        db.session.commit()
        enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        return jsonify({"message": "Successfully registered for the course"})
    else:
        return jsonify({"message": "Course is full or not found"}), 400

@app.route('/drop_course/<int:course_id>', methods=['POST'])
@login_required
def drop_course(course_id):
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        course = Course.query.get(course_id)
        if course:
            course.enrolled_students -= 1
            db.session.commit()
        db.session.delete(enrollment)
        db.session.commit()
        return jsonify({"message": "Successfully dropped the course"})
    else:
        return jsonify({"message": "You are not enrolled in this course"}), 400

# this is the new code from teammate

@app.route('/student_courses', methods=['GET'])
def student_courses():
    # Ensure user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Get the logged-in user's ID
    user_id = session['user_id']

    # Query enrollments and join with courses
    registered_courses = Enrollment.query.filter_by(user_id=user_id).join(Course).with_entities(
        Course.id,
        Course.course_name,
        Course.course_number,
        Course.professor,
        Course.enrolled_students,
    ).all()

    return render_template('student_courses.html', courses=registered_courses)





@app.route( '/teacher/courses', methods=['GET'])
def get_teacher_courses():
    if 'user_id' not in session:
        return redirect(url_for('login')) # Redirect to login if no user session

    user_id = session['user_id']

    # Query the User model to get the person_name (teacher's name) by user_id
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return redirect(url_for('login')) # If no user found, redirect to login

    person_name = user.person_name
    username = user.username

    # Query the courses taught by the teacher (professor)
    courses = Course. query. filter_by(professor=person_name).all()

    return render_template('teacher_courses', person_name=person_name, courses=courses, username=username)


@app.route('/course/<int:course_id>', methods=['GET'])
def view_course(course_id):
    # Query the course by its ID
    course = Course.query.get(course_id)
    if not course:
        return "Course not found", 404

    # Query students and grades for the course
    enrollments = Enrollment.query.filter_by(course_id=course_id).join(Student).with_entities(
        Student.id, #Add the student ID
        Student.student_name,
        Student.grade
    ).all()
    # enrollments = (
    #     Enrollment.query.filter_by(course_id=course_id)
    #     .join(Student, Enrollment.id == Student.enrollment_id)
    #     .with_entities(
    #         Student.id,  # Fetch the student ID
    #         Student.student_name,  # Fetch the student name
    #         Student.grade  # Fetch the student grade
    #     )
    #     .all())
    return render_template('view_course.html', course=course, students=enrollments)

@app.route('/update_grade/<int:student_id>', methods=['POST'])
def update_grade(student_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect to login if no user session

    # Get the new grade from the form
    new_grade = request.form.get('new_grade')

    # Query the student record by student_id
    student = Student.query.get(student_id)
    if student:
        # Update the student's grade
        student.grade = new_grade
        db.session.commit()

        return redirect(url_for('view_course', course_id=student.enrollment.course_id))
    else:
        return jsonify({"message": "Student not found"}), 404

# ends here






@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)