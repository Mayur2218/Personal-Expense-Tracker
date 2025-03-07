from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from wtforms import DateField, DecimalField, SelectField, validators, PasswordField, EmailField, SubmitField,TextAreaField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email,InputRequired, Length

app = Flask(__name__)
app.secret_key = "mayur"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:/// expense.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
expenses = []
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, default=datetime.now)
    expense = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def __repr__(self) -> str:
        return f"{self.id} - {self.date} - {self.expense} - {self.category} - {self.amount}"
    
class LoginForm(FlaskForm):
    name = TextAreaField("Name", [InputRequired()])
    email = EmailField("Email", [DataRequired()])
    password = PasswordField("Password")
    submit = SubmitField("Log In")
    
class Addexpense(FlaskForm):
    expense_name = TextAreaField("Name", [validators.InputRequired(), Length(2,20)])
    amount = DecimalField("Amount", [validators.DataRequired()])
    category = SelectField("Category", [validators.InputRequired("Slect Category")],choices=(
        ('Food','Food'),
        ('Transport','Transport'),
        ('Entertainment','Entertainment'),
        ('Shopping','Shopping'),
        ('Other','Other')))
    date = DateField("Date", format="%Y-%m-%d", default=datetime.today)
    submit = SubmitField("AddExpense")

@app.route("/", methods=['GET','POST'])
def login():
    login_form = LoginForm()
    if request.method== 'POST':
        email = login_form.email.data
        password = login_form.password.data
        print(f"the email {email} and {password}")
        return redirect(url_for('header'))
    return render_template("login.html", form=login_form)

@app.route("/signup")
def signup():
    signup_form = LoginForm()
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template("signup.html", form=signup_form)


@app.route("/header")
def header():
    allExpense = Expense.query.all()
    return render_template("header.html", allExpense = allExpense)

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    form = Addexpense()
    if request.method == 'POST':
        title = form.expense_name.data
        amount = form.amount.data
        category = form.category.data
        date = form.date.data
        if date is None:
            return "Date is requried"
        new_expense = Expense(date=date,expense=title,category=category,amount=amount)
        db.session.add(new_expense)
        db.session.commit() 
        return redirect(url_for('reports'))
    return render_template('add_expense.html', form=form)

@app.route('/reports')
def reports():
    allExpense = Expense.query.all()
    return render_template('reports.html', allExpense=allExpense)

@app.route('/delete/<int:id>')
def delete(id):
    allExpense = Expense.query.get(id)
    db.session.delete(allExpense)
    db.session.commit()
    return redirect("/reports")

@app.route('/update/<int:id>', methods= ['GET','POST'])
def update(id):
    allExpense = Expense.query.get(id)

    if request.method == 'POST':
        allExpense.expense = request.form['title']
        allExpense.category = request.form['category']
        allExpense.amount = request.form['amount']
        allExpense.date = datetime.strptime(request.form['date'], "%Y-%m-%d")  # Convert date string to datetime

        db.session.commit()
        return redirect('/reports')
    return render_template('update.html', data=allExpense)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        budget = request.form['budget']
        return redirect(url_for('home'))
    return render_template('settings.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  #create database in inside the body
        print("database")
    
    app.run(debug=True)    #run the code debug mode to auto-

