from flask import Flask, render_template, request, redirect, session, make_response
from pymongo import MongoClient
from bson.binary import Binary
import base64
from bson.objectid import ObjectId
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PIL import Image as PILImage
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY')
client=MongoClient(os.environ.get('MONGO_URI'))
db = client['Employee']
client = MongoClient()
collection1 = db['Admin'] 
collection2=db['Employee']



@app.template_filter('b64_photo')
def b64_photo(data):
    if isinstance(data, (bytes, Binary)):
        return base64.b64encode(data).decode('utf-8')
    return ''

@app.route('/', methods=["GET", "POST"]) 
def index():
    if request.method == "POST":          
        user = request.form.get('username')
        password = request.form.get('password') 
        data = collection1.find_one({"username": user, "password": password})

        if data:
            session['username'] = user
            return redirect('/index')
        else:
            return render_template('emp/dashboard.html', message="Incorrect Username or Password.")
    
    return render_template('emp/dashboard.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')


@app.route('/index', methods=["GET", "POST"])
def main():
    if 'username' in session:
        data=list(collection2.find())
        return render_template('emp/index.html',data=data)
    else:
        return redirect('/')
    

@app.route('/add_employee', methods=["GET", "POST"])
def add():
    if 'username' not in session:
        return redirect('/')

    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        department = request.form.get('department')
        joining_date = request.form.get('joining_date')
        salary = request.form.get('salary')
        address = request.form.get('address')

        # Read file
        photo = request.files['photo']
        photo_data = Binary(photo.read())  # convert to binary for MongoDB

        data = {
            "Name": name.upper(),
            "Email": email,
            "Phone": phone,
            "Department": department.upper(),
            "Joining Date": joining_date,
            "Salary": salary,
            "Address": address,
            "Photo": photo_data
        }
        collection2.insert_one(data)
        return redirect('/index')

    return render_template('emp/add_employee.html')

from bson.objectid import ObjectId

@app.route('/edit_employee/<string:id>', methods=["GET", "POST"])
def edit(id):
    if 'username' not in session:
        return redirect('/')
    
    if request.method == 'POST':
        updated_data = {
            "Name":(request.form['name']).upper(),
            "Email": request.form['email'],
            "Phone": request.form['phone'],
            "Department": (request.form['department']).upper(),
            "Joining Date": request.form['joining_date'],
            "Salary": request.form['salary'],
            "Address": request.form['address']
        }

        # Update photo if uploaded
        if 'photo' in request.files and request.files['photo'].filename:
           updated_data['Photo'] = Binary(request.files['photo'].read())
        
        collection2.update_one({"_id": ObjectId(id)}, {"$set": updated_data})
        return redirect('/index')
    
    data = collection2.find_one({"_id": ObjectId(id)})
    return render_template('emp/edit_employee.html', data=data)

@app.route('/delete_employee/<string:id>',methods=["GET","POST"])
def delete(id):
    if 'username' not in session:
        return redirect('/')
    collection2.delete_one({"_id":ObjectId(id)})
    return redirect('/index')


@app.route('/search')
def search():
    if 'username' not in session:
        return redirect('/')
    query = request.args.get('query')
    if query=='':
        return redirect('/index')
    if query:
        results = list(collection2.find({
            "$or": [
                {"Name": {"$regex": query, "$options": "i"}},
                {"Department": {"$regex": query, "$options": "i"}}
            ]
        }))
    else:
        results = []

    return render_template('emp/index.html', data=results, query=query)


@app.route('/export_pdf')
def export_pdf():
    if 'username' not in session:
        return redirect('/')

    # Create a buffer to hold the generated PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "Employee Report")
    y -= 30

    p.setFont("Helvetica", 10)

    data = list(collection2.find())  # Replace with actual data fetching from DB
    for emp in data:
        if y < 100:  # New page if space is less
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)

        # Photo
        if emp.get("Photo"):
            image = ImageReader(BytesIO(emp["Photo"]))
            p.drawImage(image, 40, y - 40, width=50, height=50)
        else:
            p.drawString(40, y, "No Photo")

        # Text fields
        p.drawString(100, y, f"Name: {emp.get('Name', '')}")
        p.drawString(100, y - 15, f"Email: {emp.get('Email', '')}")
        p.drawString(100, y - 30, f"Phone: {emp.get('Phone', '')}")
        p.drawString(300, y - 0, f"Dept: {emp.get('Department', '')}")
        p.drawString(300, y - 15, f"Date: {emp.get('Joining Date', '')}")
        p.drawString(300, y - 30, f"Salary: {emp.get('Salary', '')}")
        p.drawString(100, y - 45, f"Address: {emp.get('Address', '')}")

        y -= 80

    # Save the generated PDF to the buffer
    p.save()

    buffer.seek(0)

    # Set the filename for download (browser will handle saving it to the Downloads folder)
    return make_response(buffer.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="employee_data.pdf"'  # This prompts the browser to download the file
    })

if __name__ == "__main__":
    app.run(debug=False)
