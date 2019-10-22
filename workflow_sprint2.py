from flask import request, Flask, jsonify, redirect, url_for
from flask_cors import CORS
import psycopg2 as pg
from psycopg2 import Error
from datetime import datetime
import json 
from flask_mail import Message, Mail
import time

app = Flask(__name__)


app.config.update(
	DEBUG=True,
	MAIL_SERVER='smtp.gmail.com',
	MAIL_PORT=465,
	MAIL_USE_SSL=True,
	MAIL_USERNAME = 'donotreply.daughertytransitions@gmail.com',
	MAIL_PASSWORD = 'teamwon1'
	)
mail = Mail(app)
CORS(app)

def connectPG():
    return pg.connect(user = 'postgres',
                    password = "password",
                    dbname = "teamwon",
                    host = 'teamwon.ci1fgenlh3ew.us-east-1.rds.amazonaws.com',
                    port = '5432',
                    connect_timeout = 1)
















#########################################################################
################ Sending Checklist and Marking Progress #################
#########################################################################
@app.route('/cklist', methods = ["POST"])
def dbentry():
    connection = connectPG()
    cursor = connection.cursor()

    #Inserting into Checklist Table
    isOnboarding = f"{request.json['isOnboarding']}"
    company = request.json['company']
    try:
        name = request.json['name']
    except: name = "Un-named"


    checklist_query = f'INSERT INTO checklist (isonboarding, company, checklist_name)\
        VALUES (%s, %s, %s) RETURNING checklist_id'
    cursor.execute(checklist_query, (isOnboarding, company, name))
    checklist_id = cursor.fetchone()[0]
    connection.commit()


    #Inserting into Consultant Table
    email = request.json['email']
    name = email.split('.')
    name_2 = name[1].split("@")
    first_name = name[0].capitalize()
    last_name = name_2[0].capitalize()

    consultant_query = f'INSERT INTO consultant (first_name, last_name, email)\
        VALUES (%s, %s, %s) RETURNING consultant_id'
    cursor.execute(consultant_query, (first_name, last_name, email))
    consultant_id = cursor.fetchone()[0]
    connection.commit()

    #Inserting into Task Table and status table
    Task = request.json['tasks']
    tidList = []
    date = datetime.now()
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        taskquery = f'INSERT INTO task (description, reminder) VALUES (%s, %s) RETURNING task_id'
        cursor.execute(taskquery, (description, reminder))
        task_id = cursor.fetchone()[0]
        tidList.append({"task_id":task_id, "description":description})
        progressquery = f'INSERT INTO progress (checklist_id, task_id) VALUES ({checklist_id}, {task_id})'
        checklist_taskQuery = f"INSERT INTO checklist_task_join (checklist_id, task_id, consultant_id, date_sent) VALUES ({checklist_id}, {task_id}, {consultant_id}, '{date}')"
        cursor.execute(checklist_taskQuery)
        cursor.execute(progressquery)
        connection.commit()
    cursor.close()
    connection.close()


## Sending the email with link to mark as complete
    if isOnboarding == True:
        transition = 'Onboarding'
    else: 
        transition = 'Offboarding'

    name = email.split('.')
    name_2 = name[1].split("@")
    first_name = name[0].capitalize()
    last_name = name_2[0].capitalize()

    task_string = ""
    for index in range(len(tidList)):
        task_string += f"<li style= 'font-family:arial,helvetica,sans-serif;'>{tidList[index]['description']}     \
            <a href='http://127.0.0.1:5000/progress/{checklist_id}/{tidList[index]['task_id']}'>Click Here to Mark As Complete</a></li>"
    print(task_string)

    try:
        msg = Message(f"{company} {transition} Checklist for {first_name} {last_name}", sender="donotreply.daughertytransitions@gmail.com", recipients=[f"{email}"])
        msg.html = f"<h2 style='text-align: center; font-family:arial,helvetica,sans-serif;'>{company} {transition} Checklist for {first_name} {last_name}</h2>\
            <p style='text-align: left; font-family:arial,helvetica,sans-serif;'>To smooth the transition between engagements your team manager has compiled \
            a list of the following task that must be completed.&nbsp;</p>\
            <p style='text-align: left; font-family:arial,helvetica,sans-serif;'>Please complete each task and click the link to mark the task as completed.</p><p>&nbsp;</p><ol>{task_string}</ol>\
            <p style= 'text-align: left; font-family:arial,helvetica,sans-serif;'>&nbsp;Thank you,</p>\
                <p><img style='float: left;' src='https://www.daugherty.com/wp-content/uploads/2016/06/daugherty_stacked.jpg' alt='' width='238' height='74' /></p>"
        mail.send(msg)
        return json.dumps({"Status Code":200})
    except:
        return("error") 



@app.route('/progress/<int:checklist_id>/<int:task_id>', methods = ["GET"])
def progressUpdate(checklist_id, task_id):
    connection = connectPG()
    cursor = connection.cursor()
    date = datetime.now()
    update = f'UPDATE progress SET iscomplete = true WHERE checklist_id = {checklist_id} and task_id = {task_id}'
    date = f'UPDATE progress SET date_complete = "{date}" where checklist_id = {checklist_id} and task_id = {task_id}'
    cursor.execute(update)
    cursor.execute(date)
    connection.commit()
    return redirect(f"http://localhost:4200/confirm/{checklist_id}")













##################################################################
################ HOME PAGE AND CHECKLIST DETAILS #################
##################################################################


@app.route('/home', methods = ["GET"])
def home():
    connection = connectPG()
    cursor = connection.cursor()
    query = "SELECT consultant.consultant_id as consultant_id, concat(first_name, ' ', last_name) Consultant, checklist_task_join.checklist_id as cid, checklist.company as Client, checklist.isOnboarding as Transition, checklist_task_join.date_sent as DateSent, COUNT(CASE WHEN isComplete THEN 1 END) * 100 / count(checklist_task_join.task_id) AS progress \
                FROM consultant \
                    JOIN checklist_task_join ON checklist_task_join.consultant_id = consultant.consultant_id \
                    JOIN progress ON progress.checklist_id = checklist_task_join.checklist_id \
                    JOIN checklist ON checklist.checklist_id = checklist_task_join.checklist_id \
                    GROUP BY consultant.consultant_id, cid, Consultant, Client, Transition, DateSent"
    cursor.execute(query)
    records = cursor.fetchall()
    colnames = ['consultant_id','consultant','cid','company','isOnboarding','date','progress']

    results = []
    for row in records:
            results.append(dict(zip(colnames, row)))
    if(connection):
            cursor.close()
            connection.close()
    try:
        return jsonify(results)
    except:
        return jsonify(0)

@app.route('/details/<int:checklist_id>', methods = ["GET"])
def details(checklist_id):
    connection = connectPG()
    cursor = connection.cursor()
    detailquery = f'SELECT first_name, last_name, company, isonboarding, date_sent, description, reminder, iscomplete, date_complete\
        from checklist_task_join ct\
        join progress p on ct.checklist_id = p.checklist_id and ct.task_id = p.task_id\
        join task t on ct.task_id = t.task_id\
        join checklist c on c.checklist_id = ct.checklist_id\
        join consultant co on co.consultant_id = ct.consultant_id\
        where p.checklist_id = {checklist_id}'

    cursor.execute(detailquery)
    records = cursor.fetchall()
    tasklist = []
    for x in range(len(records)):
        task = {}
        task['description'] = records[x][5]
        task['reminder'] = records[x][6]
        task['isComplete'] = records[x][7]
        task['date_complete'] = records[x][8]
        tasklist.append(task)
    ChecklistDetails = {"first_name":records[0][0], "last_name":records[0][1], "company":records[0][2], "isOnboarding":records[0][3], "date_sent":records[0][4]}
    ChecklistDetails['tasks'] = tasklist
    return jsonify(ChecklistDetails)












##################################################################
################# Saving and Pullin Templates ####################
##################################################################
@app.route('/savetemplate', methods = ["POST"])
def savetemplate():
    connection = connectPG()
    cursor = connection.cursor()

    #Inserting into Checklist_template Table
    isOnboarding = request.json['isOnboarding']
    company = request.json['company']
    try:
        name = request.json['name']
    except: name = "Un-named"


    checklist_query = f'INSERT INTO checklist_template (isonboarding, company, checklist_name)\
        VALUES (%s, %s, %s) RETURNING checklisttemplate_id'
    cursor.execute(checklist_query, (isOnboarding, company, name))
    checklisttemplate_id = cursor.fetchone()[0]
    connection.commit()

    #Inserting into Task Table and status table
    Task = request.json['tasks']
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        taskquery = f'INSERT INTO task_template (description,reminder) VALUES (%s, %s) RETURNING tasktemplate_id'
        cursor.execute(taskquery, (description, reminder))
        tasktemplate_id = cursor.fetchone()[0]
        joinquery = f'INSERT INTO template_join (checklisttemplate_id, tasktemplate_id) VALUES ({checklisttemplate_id},{tasktemplate_id})'
        cursor.execute(joinquery)
        connection.commit()
    cursor.close()
    connection.close()

    return json.dumps({"Status Code":200})


@app.route('/alltemplates', methods = ["GET"])
def alltempaltes():
    connection = connectPG()
    cursor = connection.cursor()
    query = f'Select ct.checklisttemplate_id, checklist_name\
                from checklist_template ct\
                join template_join tj on ct.checklisttemplate_id = tj.checklisttemplate_id\
                join task_template tt on tt.tasktemplate_id = tj.tasktemplate_id'
    cursor.execute(query)
    records = cursor.fetchall()
    colnames = ['checklisttemplate_id', 'name']
    results = []
    for row in records:
            results.append(dict(zip(colnames, row)))
    cursor.close()
    connection.close()
    return jsonify(results)


@app.route('/gettemplate/<int:checklisttemplate_id>', methods = ["GET"])
def gettemplate(checklisttemplate_id):
    connection = connectPG()
    cursor = connection.cursor()
    query = f'select ct.checklisttemplate_id, ct.checklist_name, isonboarding, company, description, reminder\
        from checklist_template ct\
        join template_join tj on ct.checklisttemplate_id = tj.checklisttemplate_id\
        join task_template tt on tt.tasktemplate_id = tj.tasktemplate_id\
        where ct.checklisttemplate_id = {checklisttemplate_id}'
    cursor.execute(query)
    records = cursor.fetchall()
    tasklist = []
    print(records)
    for x in range(len(records)):
        task = {}
        task['description'] = records[x][4]
        task['reminder'] = records[x][5]
        tasklist.append(task)
    savedChecklist = {"name":records[0][1], "isOnboarding":records[0][2], "company":records[0][3]}
    savedChecklist['tasks'] = tasklist
    return jsonify(savedChecklist)

    
if __name__ == "__main__":

    app.run(debug=True)