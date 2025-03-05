from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:/// expense.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
expenses = []
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, default=datetime)
    expense = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def __repr__(self) -> str:
        return f"{self.id} - {self.date} - {self.expense} - {self.category} - {self.amount}"
@app.route("/")
def login():
    return render_template("login.html")
@app.route("/signup")
def signup():
    return render_template("signup.html")
@app.route("/header")
def hello():
    allExpense = Expense.query.all()
    return render_template("header.html", allExpense = allExpense)

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date']
        expenses.append({'title': title, 'amount': amount, 'category': category, 'date': date})

        new_expense = Expense(date=datetime.strptime(date, "%Y-%m-%d"), expense=title,category=category,amount=amount)
        db.session.add(new_expense)
        db.session.commit() 
        return redirect(url_for('reports'))
    return render_template('add_expense.html')

@app.route('/reports')
def reports():
    allExpense = Expense.query.all()
    return render_template('reports.html', allExpense=allExpense)

@app.route('/delete/<int:id>')
def delete(id):
    allExpense = Expense.query.filter_by(id=id).first()
    db.session.delete(allExpense)
    db.session.commit()
    return redirect("/reports")

@app.route('/update/<int:id>', methods= ['GET','POST'])
def update(id):
    allExpense = Expense.query.filter_by(id=id).first()
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']
        new_expense = Expense(date=datetime.strptime(date, "%Y-%m-%d"), expense=title,category=category,amount=amount)
        db.session.add(new_expense)
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

