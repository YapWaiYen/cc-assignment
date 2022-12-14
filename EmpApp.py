from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from datetime import datetime
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('AddEmp.html')

@app.route("/home", methods=['GET', 'POST'])
def main():
    return render_template('main.html')

@app.route("/payroll", methods = ['GET', 'POST']) 
def payroll(): 
    return render_template('Payroll.html')
    
@app.route("/payroll/results", methods = ['GET', 'POST']) 
def cal_Payroll():
    select_statement = "SELECT total_working_hours FROM attendance WHERE emp_id = %(emp_id)s" 
    cursor = db_conn.cursor()
    
    if 'emp_id' in request.form and 'basic' in request.form and 'days' in request.form: 
        emp_id = int(request.form.get('emp_id'))
        basic_salary = int(request.form.get('basic'))
        workday_per_week = int(request.form.get('days'))
        
        #Get employee working hours + OT time
        try: 
            cursor.execute(select_statement, {'emp_id': emp_id})
            WorkHour = cursor.fetchall() 
            Final = 0 
            
            for row in WorkHour:
                Hour = row[0] 
                NewHour = datetime.strptime(Hour, '%H:%M:%S.%f') 
                
                total_seconds = NewHour.second + NewHour.minute*60 + NewHour.hour*60*60 
                Final += total_seconds
                Final - Final/3600 
                working_hour = round(Final, 2) 
                print (Final) 
                
        except Exception as e:
            return str(e)
        
        
        pay = round((basic_salary * workday_per_week * working_hour), 2) 
        annual = float(pay) * 12 
        annual = int(annual) 
        
        Bonus = annual * 0.1 
        
    else: 
        print("Something Missing") 
        return render_template('Payroll.html')
    
    return render_template('PayrollOutput.html', emp_id = emp_id, MonthlySalary = pay, 
                          AnnualSalary = annual, WorkingHours = working_hour, Bonus = Bonus) 


@app.route("/add", methods=['GET', 'POST'])
def addTemplate():
    return render_template('AddEmp.html')

@app.route("/about", methods=['GET', 'POST'])
def about():
    return render_template('about_us.html')

@app.route("/faq", methods=['GET', 'POST'])
def faq():
    return render_template('faq.html')

@app.route("/progress", methods=['GET', 'POST'])
def progress():
    return render_template('progress.html')


@app.route("/addemp", methods=['POST'])
def AddEmp():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['education']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']
    check_in = ''

    insert_sql = "INSERT INTO employee(first_name,last_name,education,location,check_in) VALUES (%s, %s, %s, %s,%s)"
    max="SELECT MAX(emp_id) from employee"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (first_name, last_name, pri_skill, location,check_in))
        db_conn.commit()
        emp_id=cursor.execute(max)
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
		emp_image_file_name_in_s3 = "emp-" + emp_name + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

@app.route("/get")
def get():
    return render_template("GetEmp.html") 


#Get Employee Results
@app.route("/employeeDetails", methods = ['GET', 'POST'])
def getEmp():
    emp_id = request.form['emp_id']
    select_statement = "SELECT * FROM employee WHERE emp_id = %(emp_id)s"
    
    cursor = db_conn.cursor()
    
    try:
        cursor.execute(select_statement, {'emp_id':int(emp_id)})
        for result in cursor: 
            print(result)
            
    except Exception as e:
        return str(e)
    
    finally:
        cursor.close() 
        
    return render_template("GetEmpOutput.html", result = result)


@app.route("/attendance")
def attendance():
    return render_template("CheckIn.html")

@app.route("/attendance/CheckIn", methods=['GET', 'POST'])
def checkIn():
    emp_id = request.form['emp_id']
    
    #UPDATE Statement 
    update_statement = "UPDATE employee SET check_in =(%(check_in)s) WHERE emp_id = %(emp_id)s"
    
    cursor = db_conn.cursor()
    
    LoginTime = datetime.now()
    formatted_login = LoginTime.strftime('%Y-%m-%d %H:%M:%S')
    print ("Check in time:{}", formatted_login)
    
    try:
        cursor.execute(update_statement, { 'check_in': formatted_login, 'emp_id':int(emp_id)})
        db_conn.commit()
        print(" Data Updated into MySQL")
    except Exception as e:
        return str(e)
    
    finally:
        cursor.close() 
        
    return render_template('CheckOut.html', LoginTime = formatted_login)

@app.route("/attendance/CheckOut", methods=['GET', 'POST'])
def checkOut():
    emp_id = request.form['emp_id']
    
    #UPDATE Statement 
    select_statement = "SELECT check_in FROM employee WHERE emp_id = %(emp_id)s"
    insert_statement = "INSERT INTO attendance VALUES (%s, %s, %s, %s)"
    
    cursor = db_conn.cursor()
    
    try:
        cursor.execute(select_statement, {'emp_id':int(emp_id)})
        LoginTime = cursor.fetchall()
        
        for row in LoginTime:
            formatted_login = row 
            print(formatted_login[0])
            
        CheckOutTime = datetime.now()
        LoginDate = datetime.strptime(formatted_login[0], '%Y-%m-%d %H:%M:%S')
        
        formatted_checkOut = CheckOutTime.strftime('%Y-%m-%d %H:%M:%S')
        total_working_hours = CheckOutTime - LoginDate
        print(total_working_hours)
        
        try:
            cursor.execute(insert_statement, (emp_id, formatted_login[0], formatted_checkOut, total_working_hours))
            db_conn.commit()
            print(" Data Updated into MySQL")
            
        except Exception as e:
            return str(e)
        
    except Exception as e:
        return str(e)
    
    finally:
        cursor.close() 
        
    return render_template('CheckOut.html', checkOut = formatted_checkOut, LoginTime = formatted_login[0], totalWorkingHours = total_working_hours)

@app.route("/employee", methods=['GET', 'POST'])
def display():
    cursor = db_conn.cursor()
    try:
        cursor.execute("SELECT * from employee")
        all_result = cursor.fetchall()

    except Exception as e:
        return str(e)

    finally:
        cursor.close() 
    
    return render_template("attendance.html",data=all_result)  


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
