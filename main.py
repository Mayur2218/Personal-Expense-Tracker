from flask import Flask, render_template, redirect, flash, url_for, request, session, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_login import login_required, login_user, LoginManager, UserMixin, logout_user, current_user
from itsdangerous import Serializer
from sqlalchemy import desc, func
import psycopg2, io, base64, os,matplotlib, random, calendar
import matplotlib.pyplot as plt
from flask_mail import Message, Mail
from wtforms import DateField, DecimalField, SelectField,EmailField,PasswordField,validators, SubmitField,StringField
from flask_wtf import FlaskForm
from wtforms.validators import Length, DataRequired, InputRequired
from datetime import datetime, date, timedelta
from fpdf import FPDF
from werkzeug.utils import secure_filename
import pandas as pd
from collections import defaultdict
from math import ceil

matplotlib.use('Agg')
ALLOWED_EXTENSIONS = {'txt','pdf','png','jpg','jpeg','gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = "mayur"
bcrypt = Bcrypt(app)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://mayur:Mayur%40223133@localhost/expenses_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/assets'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
expenses = []

#flask login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'strong'
login_manager.login_view = "login"

""" used mail reset password """
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT']=587
app.config['MAIL_USE_TLS']= True
app.config['MAIL_USERNAME'] = 'sodha2210@gmail.com'
app.config['MAIL_PASSWORD']='yinm dslz jjte rvcg'
app.config['MAIL_DEFAULT_SENDER'] = "sodha2210@gmail.com"
mail=Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
""" User information login and signup """
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    otp = db.Column(db.Integer, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    profile_pic = db.Column(db.String(255), nullable=False)

    def __init__(self, name, lastname,phone_number,email, password):
        self.name = name
        self.lastname = lastname
        self.phone_number = phone_number
        self.email = email
        self.password = password
    def check_password(self, password):
        is_valid = bcrypt.check_password_hash(self.password, password)
        return is_valid

    ### mail varify token
    def get_token(self):
        serial = Serializer(app.config['SECRET_KEY'])
        return serial.dumps({'user_id':self.id})
    @staticmethod
    def verify_token(token,expire_sec=300):
        serial=Serializer(app.config['SECRET_KEY'])
        try:
            user_id =serial.loads(token, max_age=expire_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)
class SignupForm(FlaskForm):
    name = StringField("Name", [InputRequired()])
    lastname = StringField("LastName", [InputRequired()])
    phone_number = StringField("Phone Number",[InputRequired(),Length(min=10, max=10)])
    email = EmailField("Email", [InputRequired()])
    password = PasswordField("Password",[InputRequired()])
    confirm_password = PasswordField("Confirm Password",[InputRequired()])
    submit = SubmitField("Sign up")
@app.route("/signup", methods=['GET','POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('header'))
    signup_form = SignupForm()
    if signup_form.validate_on_submit():
        email = signup_form.email.data.strip().lower()
        password = signup_form.password.data
        confirm_password = signup_form.confirm_password.data
        if password != confirm_password:
            flash("Confirm Password are not match. Please enter again!",'danger')
            return redirect(url_for('signup'))
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("You've already signed up with that email, log in instead!","warning")
            return redirect(url_for('login'))
        hw_password = bcrypt.generate_password_hash(signup_form.password.data.strip().lower()).decode('utf-8')
        new_user = User(
            name = signup_form.name.data,
            lastname = signup_form.lastname.data,
            phone_number = signup_form.phone_number.data,
            email = email,
            password = hw_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('header'))
    return render_template("signup.html", form=signup_form, logged_in=current_user.is_authenticated)
class LoginForm(FlaskForm):
    email = EmailField("Email", [DataRequired()])
    password = PasswordField("Password",[DataRequired()])
    submit = SubmitField("Log In")
@app.route ("/", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('header'))
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data.strip().lower()
        # Fetch the user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("That email does not exist, please try again!", "danger")
            return redirect(url_for('login'))
        # Check password correctly
        if not user.check_password(password):
            flash("Password incorrect, please try again!", "danger")
            return redirect(url_for('login'))
        # If authentication successful, log in user
        login_user(user)
        return redirect(url_for("header"))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)
@app.route("/header")
@login_required
def header():
    initial_balance = 25000
    all_expense = Expense.query.filter_by(user_id=current_user.id).order_by(desc(Expense.date)).limit(5).all()
    #chart data
    data_month = get_data_bar() or {}
    data = get_data_pie() or {}
    pie_chart = create_pie_chart(data) if data else None
    bar_chart = create_bar_chart(data_month) if data else None

    expense_data = calculate_expense() or {'month_total':0}
    account_balance = initial_balance - expense_data['month_total']

    return render_template("header.html", allExpense = all_expense,
                           bar_chart=bar_chart,
                           account_balance=account_balance,pie_chart=pie_chart,
                           last_month=expense_data['month_total'],
                           logged_in=current_user.is_authenticated)

""" Expense data update,delete and add """
class Expense(db.Model):
    __tablename__ = 'expense'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Foreign Key
    date = db.Column(db.Date, default=date.today, nullable=False)  # Use date.today() for consistency
    expense = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    user = db.relationship('User', backref=db.backref('expenses', lazy=True))  # Relationship backref particular user all expense data
    #lazy are like select to used to loads expenses only when needed

    def __repr__(self) -> str:
        return f"{self.id} - {self.date} - {self.expense} - {self.category} - {self.amount}"
class AddExpense(FlaskForm):
    expense = StringField("Name", [validators.InputRequired(), Length(2,35)])
    amount = DecimalField("Amount", [validators.DataRequired()])
    category = SelectField("Category", [validators.InputRequired("Select Category")],choices=(
        ('Food','Food'),
        ('Transport','Transport'),
        ('Entertainment','Entertainment'),
        ('Electronic','Electronic'),
        ('Shopping','Shopping'),
        ('Housing','Housing'),
        ('Other','Other')))
    date = DateField("Date", format="%Y-%m-%d")
    submit = SubmitField("Save")
@app.route('/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = AddExpense()
    if request.method == 'POST':
        expense = form.expense.data
        amount = form.amount.data
        category = form.category.data
        date = form.date.data
        new_expense = Expense(
            user_id=current_user.id,
            date=date,
            expense=expense,
            category=category,
            amount=amount
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('history'))
    return render_template('add_expense.html', form=form,logged_in=current_user.is_authenticated)
@app.route('/update/<int:id>', methods= ['GET','POST'])
@login_required
def update(id):
    all_expense = Expense.query.filter_by (id=id, user_id=current_user.id).first ()
    form = AddExpense(obj=all_expense)
    if request.method == 'POST':
        all_expense.expense = form.expense.data
        all_expense.amount = form.amount.data
        all_expense.category = form.category.data
        all_expense.date = form.date.data
        db.session.commit()
        flash ("Expense update successfully.", "success")
        return redirect(url_for('history'))
    return render_template('update.html', form=form, allExpense=all_expense,logged_in=current_user.is_authenticated)
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    all_expense = Expense.query.get(id)
    db.session.delete(all_expense)
    db.session.commit()
    flash("Expense deleted successfully.", "success")
    return redirect("/history")

""" give the weekly, monthly, year and recently(history) expenses """
def calculate_expense():
    today = datetime.now().date()
    # recent expense
    recent = Expense.query.filter_by(user_id=current_user.id).order_by(desc(Expense.date)).limit(10).all()
    #week expense
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)
    week_expense = Expense.query.filter(Expense.user_id == current_user.id, Expense.date >= start_week, Expense.date <= end_week).order_by(desc(Expense.date)).all()
    week_total = sum(expense.amount for expense in week_expense)
    #month expense
    start_month = today.replace(day=1)
    end_month = (start_month + timedelta (days=31)).replace(day=1) - timedelta(days=1)
    month_expense = Expense.query.filter(Expense.user_id == current_user.id, Expense.date >= start_month, Expense.date <= end_month).order_by(desc(Expense.date)).all()
    month_total = sum(expense.amount for expense in month_expense)
    #high category
    high_category = db.session.query(Expense.category, func.sum(Expense.amount).label('total_spent'))\
                     .filter(Expense.user_id == current_user.id, Expense.date >= start_month).group_by(Expense.category)\
                     .order_by(func.sum(Expense.amount).desc()).first()
    if not high_category:
        high_category = {'category': 'No data', 'total_spent':0}
    return {
        'recent': recent,
        'week': week_expense,
        'month': month_expense,
        'month_total': month_total,
        'week_total': week_total,
        'high_category': high_category['category'] if isinstance(high_category, dict) else high_category.category,
    }
@app.route('/monthly', methods=['GET','POST'])
@login_required
def monthly():   #monthly report data
    month_filter = request.args.get('from', '').strip().lower()
    all_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(desc(Expense.date)).all()
    month_expense = defaultdict (list)
    found = False
    for expense in all_expenses:
        month_key = expense.date.strftime('%Y - %B')
        month_name = expense.date.strftime('%B').lower()
        if not month_filter or month_filter in month_name:
            month_expense[month_key].append (expense)
            found =True
    if month_filter and not found:
        flash(f"No expense data found for the month: {month_filter}", "danger")
        return redirect(url_for('monthly'))
    all_expense = dict (month_expense)
    return render_template('monthly.html', allExpense=all_expense, logged_in=current_user.is_authenticated)
@app.route('/weekly', methods=['GET','POST'])
@login_required
def weekly():
    week_filter = request.args.get('from', '').strip().lower()
    all_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(desc(Expense.date)).all()
    week_expense = defaultdict (list)
    found = False
    for expense in all_expenses:
        year, week_num, _ = expense.date.isocalendar()   # _ are represent weekday ignore it mon-1, sun-7
        week_key = f"{year}-W{week_num:02d}"
        week_number = f"W{week_num:02d}".lower()
        if not week_filter or week_filter in week_number:
            week_expense[week_key].append (expense)
            found=True
    if week_filter and not found:
        flash(f"No expense data found check week number:{week_filter}","danger")
        return redirect(url_for('weekly'))
    all_expense = dict (week_expense)
    return render_template('weekly.html',allExpense=all_expense, logged_in=current_user.is_authenticated)
@app.route('/year', methods=['GET','POST'])
@login_required
def year():
    #data print formate
    all_expenses = Expense.query.filter_by(user_id = current_user.id).all()
    year_month = defaultdict(lambda: {calendar.month_name[m]: 0 for m in range(1,13)})
    for exp in all_expenses:
        year = exp.date.year
        month = exp.date.strftime('%B')
        year_month[year][month] += exp.amount
    grouped_data = {}
    for year, month_exp in year_month.items():
        grouped_data[year] = [{'month': f"{month}-{year}", 'amount':amount} for month, amount in month_exp.items()]

    #search button
    year_filter = request.args.get('from','').strip()
    if year_filter:
        if not year_filter.isnumeric():
            flash ("Please enter a valid year(e.g:2025).", "warning")
            return redirect(url_for('year'))
        year_filter = int(year_filter)
        if year_filter in grouped_data:
            grouped_data = {year_filter:grouped_data[year_filter]}
        else:
            flash(f"No expense data found for the year {year_filter}.", "danger")
            return redirect(url_for('year'))
    grouped_data = dict(grouped_data)
    return render_template('year.html',month_data=grouped_data,all_expenses=all_expenses,
                           logged_in=current_user.is_authenticated)
class Search(FlaskForm):
    start_date = DateField("𝐒𝐭𝐚𝐫𝐭 𝐃𝐚𝐭𝐞", format="%Y-%m-%d")
    end_date = DateField("𝐄𝐧𝐝 𝐃𝐚𝐭𝐞", format="%Y-%m-%d")
    submit = SubmitField("𝐒𝐞𝐚𝐫𝐜𝐡")
@app.route('/history', methods=['GET','POST'])
@login_required
def history():
    page = request.args.get('page',1,type=int)
    per_page = 10
    #search button
    form = Search(request.args)
    start = request.args.get('start_date')
    end = request.args.get('end_date')

    if start and end:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d')
            end_date = datetime.strptime (end, '%Y-%m-%d')
        except ValueError:
            flash("Invalid date formate?","danger")
            return redirect(url_for('history'))

        all_data = Expense.query.filter(Expense.user_id == current_user.id, Expense.date >= start_date, Expense.date <= end_date ).order_by(Expense.date)
        total_expense = all_data.count ()
        total_pages = ceil (total_expense / per_page)  #ceil used to return smallest int greater or equal to
        all_expenses = all_data.offset ((page - 1) * per_page).limit (per_page).all ()
        if not all_expenses:
            flash("No expense data found for this date range.","danger")
        return render_template('history.html',expense=None,all_expenses=all_expenses,total_pages=total_pages,
                               logged_in=current_user.is_authenticated, page=page, form=form)

    #by default all data are display
    all_expense = Expense.query.filter_by(user_id=current_user.id).order_by(desc(Expense.date))
    total_expense = all_expense.count()
    total_pages = ceil(total_expense / per_page)
    expense = all_expense.offset((page - 1)*per_page).limit(per_page).all()
    return render_template('history.html',form=form,expense=expense,
                           page=page,total_pages=total_pages,all_expenses=None, logged_in=current_user.is_authenticated)

""" image upload in account page """
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        if 'file' not in request.files:  #check file upload or not
            return redirect(request.url)
        file = request.files['file'] #file upload
        if file.filename == '':  #not select file
            return redirect(request.url)
        if file and allowed_file(file.filename):  #call allowed func to check file valid or not
            filename = secure_filename(file.filename)  #used to prevent file remove dangerous char // ....
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename   # Update user's profile image path
            db.session.commit()
            return redirect(url_for('account'))

    user = User.query.get(current_user.id)
    default_pic = 'download.jpg'
    profile_pic = current_user.profile_pic if current_user.profile_pic else default_pic
    file_url = url_for('uploaded_file', filename=profile_pic)

    initial_balance = 25000
    expense_data = calculate_expense() or {'month_total':0,'week_total':0,'high_category':'No data'} #call function and find data
    account_balance = initial_balance - expense_data['month_total']
    all_expense = Expense.query.filter_by(user_id = current_user.id).all()
    return render_template('account.html',allExpense = all_expense,
                           user=user,
                           initial_balance=initial_balance,file_url=file_url,
                           account_balance=account_balance,
                           last_week = expense_data['week_total'],
                           last_month = expense_data['month_total'],
                           high_category=expense_data['high_category'],
                           logged_in=current_user.is_authenticated)
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

""" Graph represent data """
def get_db_connect():
    conn = psycopg2.connect(
        host='localhost',
        database='expenses_db',
        user='mayur',
        password='Mayur@223133'
    )
    return conn
def get_data_pie():
    conn = get_db_connect()
    cur = conn.cursor()
    cur.execute("SELECT category,SUM(amount)"
                " FROM expense"
                " WHERE user_id = %s AND DATE_TRUNC('week',date)=DATE_TRUNC('week',CURRENT_DATE)"
                " GROUP BY category",(current_user.id,))
    data = cur.fetchall ()
    conn.close()
    return data
def create_pie_chart(data):
    if not data:
        return None
    category = [row[0] for row in data]
    amount = [row[1] for row in data]
    plt.figure(figsize=(6,6))
    plt.pie(amount, labels=category, autopct='%1.1f%%') #create pie chart autopct= are convert image data in percentage 1 decimal no.
    img = io.BytesIO()  # server the chart as an in memory buffer
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return base64.b64encode(img.getvalue()).decode('utf8') #getvalue as binary -> Base64 -> utf-8 string formate
def get_data_bar():
    conn = get_db_connect()
    cur = conn.cursor()
    cur.execute("SELECT TO_CHAR(date,'Month') AS months,SUM(amount) AS Total_expense"
                " FROM expense"
                " WHERE user_id = %s AND EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE)"
                " GROUP BY months, EXTRACT(MONTH FROM date)"
                " ORDER BY EXTRACT(MONTH FROM date)",(current_user.id,))
    data_month = cur.fetchall()
    cur.close()
    conn.close()
    return data_month
def create_bar_chart(data):
    if not data:  #new user can not get error
        return None
    months = [row[0] for row in data]
    total_expense = [row[1] for row in data]
    bars = plt.bar(months,total_expense, color="#1e3a8a")
    #name
    plt.xlabel('Month Name')
    plt.ylabel('Total Expense')
    plt.ylim(3000,30000)
    plt.bar_label(bars, padding=3, fontsize=11, color="#000")
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return base64.b64encode (img.getvalue()).decode ('utf8')

""" Reset password used email"""
def send_mail(user):
    token=user.get_token()
    msg=Message('Password Reset Request',recipients=[user.email])
    msg.body=f''' TO rest your password. Please follow the link below.
    {url_for('reset_token',token=token,_external=True)}
    If you didn't send a password reset request. Please ignore this message
    '''
    mail.send(msg)
class ResetPassword(FlaskForm):
    select = SelectField("Select any one", validators=[DataRequired()], choices=(('email','email'),('OTP','OTP')))
    email = EmailField("Email")
    phone_number = StringField("Phone Number")
    submit = SubmitField("Reset Password")
@app.route('/rest_pwd', methods=['GET','POST'])
def reset_password():
    form = ResetPassword()
    if form.validate_on_submit():
        email = form.email.data
        phone_number = form.phone_number.data
        msg_send_type = form.select.data
        if msg_send_type == 'email':
            user = User.query.filter_by(email=email).first()
            if user:
                send_mail(user)
                flash('Reset request send. Check your email!','success')
                return redirect(url_for('login'))
        elif msg_send_type == 'OTP':
            user = User.query.filter_by(phone_number=phone_number).first()
            if user:
                send_otp_sms (user)
                flash ('OTP sent to your phone via email!', 'success')
                return redirect (url_for ('verify_otp', phone=user.phone_number))
            else:
                flash('Phone number not found. Please enter correct number','danger')
        else:
            flash ("User not found for the given details.", "danger")
    return render_template('reset_pwd.html',title='Reset request',form=form)
class ChangePassword(FlaskForm):
    password = PasswordField("Password",[DataRequired()])
    confirm_password = PasswordField("Confirm Password",[DataRequired()])
    submit = SubmitField("Change Password")
@app.route('/reset_pwd/<token>', methods=['GET','POST'])
def reset_token(token):
    user=User.verify_token(token)
    if user is None:
        flash('That is invalid token or expired. Please try again.','warning')
        return redirect(url_for('reset_password'))
    form=ChangePassword()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash('Password do not match.','danger')
            return redirect(request.url)
        hw_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password=hw_password
        db.session.commit()
        flash('Password changed! Please login.','success')
        return redirect(url_for('login'))
    return render_template('change_pwd.html',form=form)

""" Reset password use OTP"""
def send_otp_sms(user):
    otp = random.randint(100000,999999)
    user.otp = otp  #store in db otp to varify short time
    db.session.commit()

    sms_email = f"{user.phone_number}@airtelmail.com"  # Example: Verizon SMS Gateway
    massage = Message ("Password Reset OTP", recipients=[sms_email])
    massage.body = f"Your password reset OTP is: {otp}. Use this code to reset your password."
    mail.send (massage)
class OTPVerificationForm(FlaskForm):
    otp = StringField("Enter OTP", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify OTP")
@app.route('/verify_otp/<phone>',methods=['GET','POST'])
def verify_otp(phone):
    user = User.query.filter_by(phone_number=phone).first()
    if not user:
        flash('Phone number is Invalid..!','danger')
        return redirect(url_for('reset_otp'))
    form=OTPVerificationForm()
    if form.validate_on_submit():
        if user.otp and int(form.otp.data) == user.otp:
            flash("OTP Verified! Set your new password.", "success")
            return redirect(url_for('new_pwd',phone=phone))
        else:
            flash("Invalid or expired OTP. Try again!", "danger")
            return redirect(url_for('reset_otp',phone=phone))
    return render_template('verify_otp.html',form=form)
@app.route('/new_pwd/<phone>',methods=['GET','POST'])
def new_pwd(phone):
    user = User.query.filter_by(phone_number=phone).first()
    if not user:
        flash('Phone number is Invalid..!','danger')
        return redirect(url_for('reset_otp'))
    form=ChangePassword()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash('Password do not match.','danger')
            return redirect(url_for('new_pwd'))
        hw_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password=hw_password
        user.otp = None  # Clear OTP after successful reset
        db.session.commit()
        flash('Password changed! Please login.','success')
        return redirect(url_for('login'))
    return render_template('change_pwd.html', form=form)

""" session to other user easily used"""
@app.route('/set_session')
def set_session():
    session.permanent = True
    session['user'] = 'mayur'
    session['expiry_time'] = (datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']).strftime('%Y-%m-%d %H:%M:%S')
    return "Session set with expiry time!"
@app.route('/check_expiry')
def check_expiry():
    expiry_time = session.get('expiry_time', 'No session set')
    return f"Session expires at: {expiry_time}"

"""pdf and csv formate download expense data monthly and weekly"""
@app.route('/download')
@login_required
def download():
    user = current_user
    report_type = request.args.get('report_type','monthly')
    expenses = Expense.query.filter_by(user_id=user.id).all()
    month_years = sorted (
        {exp.date.strftime ('%B %Y') for exp in expenses},  #used set to unique month
        key=lambda x: datetime.strptime (x, '%B %Y'), #convert in %B %Y formate
        reverse=True   #current month name first
    )
    year_select = sorted(
        {exp.date.strftime('%Y') for exp in expenses},
        key=lambda x: datetime.strptime(x,'%Y'),reverse=True
    )
    return render_template('download.html',user=user,
                           month_years=month_years,year_select=year_select,
                           report_type=report_type,logged_in=current_user.is_authenticated)
class ExpenseReport (FPDF):
    def header(self):
        self.set_font ("Arial", style='B', size=16)
        self.set_text_color (25, 25, 112)  # Dark blue color
        self.cell (200, 10, "Personal Expense Management System", ln=True, align='C')
        self.ln (5)
        self.set_draw_color (0, 0, 0)
        self.set_line_width (1)
        self.line (10, self.get_y (), 200, self.get_y ())  # Horizontal Line
        self.ln (10)
    def footer(self):
        self.set_y (-15)
        self.set_font ("Arial", size=10)
        self.set_text_color (128)
        self.cell (0, 10, f"Page {self.page_no ()}", align='C')
@app.route('/download-pdf', methods=['POST'])
@login_required
def download_pdf():
    user = current_user
    report_type = request.form.get('report_type')
    month_filter = request.form.get('month_name')
    year_filter = request.form.get('year_name')
    download_type = request.form.get('download_type')

    if report_type == "monthly" and month_filter:
        all_expense = Expense.query.filter_by(user_id=current_user.id).order_by(desc(Expense.date)).all()
        filtered_expense = []
        filter_date = datetime.strptime(month_filter, '%B %Y')

        for exp in all_expense:
            if exp.date.year == filter_date.year and exp.date.month == filter_date.month:
                filtered_expense.append(exp)

        expenses = filtered_expense
        total = sum(exp.amount for exp in expenses)

        if download_type == "pdf":
            pdf = ExpenseReport()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # User Details
            pdf.set_font("Arial", style='B', size=12)
            user_id = f"User ID"
            width_id = pdf.get_string_width(user_id) + 2
            pdf.cell(width_id, 10, f"User ID: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.id}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            name = f"Name"
            width_name = pdf.get_string_width(name) + 2
            pdf.cell(width_name, 10, f"Name: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.name} {user.lastname}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            phone_no = f"Phone Number"
            width_phone_no = pdf.get_string_width(phone_no)+2
            pdf.cell(width_phone_no, 10, f"Phone Number: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.phone_number}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            email = f"Email"
            width_email = pdf.get_string_width(email)+2
            pdf.cell(width_email, 10, f"Email: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.email}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            type_download = f"Download type"
            width_download = pdf.get_string_width(type_download)+2
            pdf.cell(width_download, 10, f"Download type: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{report_type}", ln=True, align='L')


            pdf.set_font("Arial", style='B', size=12)
            month = f"Month"
            width_month = pdf.get_string_width(month)+2
            pdf.cell(width_month, 10, f"Month:", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{month_filter}", ln=True, align='L')
            pdf.ln(10)

            # Table Header
            pdf.set_fill_color(25, 25, 112)
            pdf.set_text_color(255)
            pdf.set_font("Arial", style='B', size=12)
            pdf.cell(45, 10, "Date", border=1, align='C', fill=True)
            pdf.cell(60, 10, "Expense Name", border=1, align='C', fill=True)
            pdf.cell(50, 10, "Category", border=1, align='C', fill=True)
            pdf.cell(35, 10, "Amount", border=1, align='C', fill=True)
            pdf.ln()

            # Table Data
            pdf.set_text_color(0)
            pdf.set_font("Arial", size=12)
            for expense in expenses:
                pdf.cell(45, 10, expense.date.strftime("%Y-%m-%d"), border=1, align='C')
                pdf.cell(60, 10, expense.expense, border=1, align='C')
                pdf.cell(50, 10, expense.category, border=1, align='C')
                pdf.cell(35, 10, f"{expense.amount:,.2f}", border=1, align='C')
                pdf.ln()

            # Total Expense
            pdf.ln(7)
            y_line = pdf.get_y()
            pdf.set_draw_color(0,0,0)
            pdf.set_line_width(1)
            pdf.line(10,y_line,200,y_line)
            pdf.ln(3)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(105, 10, "", border=0)
            pdf.cell(50, 10, "Total Expense:", border=0, align='R')
            pdf.cell(35, 10, f"{total:,.2f}", border=0, align='L')

        elif download_type == "csv":
            data = [{
                'Date': expense.date.strftime("%Y-%m-%d"),
                'Expense Name': expense.expense,
                'Category': expense.category,
                'Amount': expense.amount
            } for expense in expenses]
            df = pd.DataFrame(data)
            csv_output = df.to_csv(index=False)
            return Response(csv_output, mimetype='text/csv',
                            headers={"Content-Disposition": f"attachment; filename={report_type}_expenses.csv"})

    elif report_type == "year" and year_filter:
        selected_year = int(year_filter)
        all_expenses = Expense.query.filter(
            Expense.user_id == current_user.id,
            Expense.date >= datetime(selected_year, 1, 1),
            Expense.date <= datetime(selected_year, 12, 31)
        ).all()

        monthly_expense = {calendar.month_name[m]: 0 for m in range(1, 13)}
        for exp in all_expenses:
            month = exp.date.strftime('%B')
            monthly_expense[month] += exp.amount

        total = sum(exp.amount for exp in all_expenses)
        month_data = [{'month': f'{month}-{selected_year}', 'amount': monthly_expense[month]}
                      for month in calendar.month_name[1:]]

        if download_type == "pdf":
            pdf = ExpenseReport()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # User Details
            pdf.set_font("Arial", style='B', size=12)
            user_id = f"User ID"
            width_id = pdf.get_string_width(user_id) + 2
            pdf.cell(width_id, 10, f"User ID: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.id}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            name = f"Name"
            width_name = pdf.get_string_width(name) + 2
            pdf.cell(width_name, 10, f"Name: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.name} {user.lastname}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            phone_no = f"Phone Number"
            width_phone_no = pdf.get_string_width(phone_no)+2
            pdf.cell(width_phone_no, 10, f"Phone Number: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.phone_number}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            email = f"Email"
            width_email = pdf.get_string_width(email)+2
            pdf.cell(width_email, 10, f"Email: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{user.email}", ln=True, align='L')

            pdf.set_font("Arial", style='B', size=12)
            type_download = f"Download type"
            width_download = pdf.get_string_width(type_download)+2
            pdf.cell(width_download, 10, f"Download type: ", ln=0, align='L')
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"{report_type}", ln=True, align='L')

            # pdf data
            pdf.ln(5)
            pdf.set_fill_color(25, 25, 112)
            pdf.set_text_color(255)
            pdf.set_font("Arial", style='B', size=12)
            pdf.cell(150, 10, "   Month Name", border=1, align='L', fill=True)
            pdf.cell(40, 10, "  Amount", border=1, align='L', fill=True)
            pdf.ln()

            pdf.set_text_color(0)
            pdf.set_font("Arial", size=12)
            for data in month_data:
                pdf.cell(150, 10, f"   {data['month']}", border=1, align='L')
                pdf.cell(40, 10, f"  {data['amount']:,.2f}", border=1, align='L')
                pdf.ln()

            pdf.ln(7)
            y_line = pdf.get_y()
            pdf.set_draw_color(0,0,0)
            pdf.set_line_width(1)
            pdf.line(10,y_line,200,y_line)
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(100, 10, "", border=0)
            pdf.cell(50, 10, "Total Expense:", border=0, align='R')
            pdf.cell(40, 10, f"{total:,.2f}", border=0, align='L')

        elif download_type == "csv":
            data = [{
                'Month Name': data['month'],
                'Amount': f'{data['amount']:,.2f}'
            } for data in month_data]
            df = pd.DataFrame(data)
            csv_output = df.to_csv(index=False)
            return Response(csv_output, mimetype='text/csv',
                            headers={"Content-Disposition": f"attachment; filename={report_type}_{year_filter}_expenses.csv"})

    else:
        flash("Invalid download type. Please select the correct type.", "danger")
        return redirect(url_for('dashboard'))  # Or wherever your redirect should go

    # Common PDF response block for both monthly and yearly
    if download_type == "pdf":
        temp_file_path = "temp_expense_report.pdf"
        pdf.output(temp_file_path)
        with open(temp_file_path, 'rb') as file:
            pdf_output = file.read()
        os.remove(temp_file_path)
        return Response(pdf_output, mimetype='application/pdf',
                        headers={"Content-Disposition": f"attachment; filename={report_type}_expense.pdf"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='192.168.0.140',port=5000,debug=True)
