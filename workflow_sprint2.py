from flask import request, Flask, jsonify
from flask_cors import CORS
import psycopg2 as pg
from psycopg2 import Error
from datetime import datetime
import json 
from flask_mail import Message, Mail

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

@app.route('/cklist', methods = ["POST"])
def dbentry():
    connection = connectPG()
    cursor = connection.cursor()

    #Inserting into Checklist Table
    isOnboarding = request.json['isOnboarding']
    company = request.json['company']
    try:
        name = request.json['name']
    except: name = "Un-named"


    checklist_query = f"INSERT INTO checklist (isonboarding, company, checklist_name)\
        VALUES ('{isOnboarding}', '{company}', '{name}') RETURNING checklist_id"
    cursor.execute(checklist_query)
    checklist_id = cursor.fetchone()[0]
    connection.commit()


    #Inserting into Consultant Table
    email = request.json['email']
    name = email.split('.')
    name_2 = name[1].split("@")
    first_name = name[0].capitalize()
    last_name = name_2[0].capitalize()

    consultant_query = f"INSERT INTO consultant (first_name, last_name, email)\
        VALUES ('{first_name}', '{last_name}', '{email}') RETURNING consultant_id"
    cursor.execute(consultant_query)
    consultant_id = cursor.fetchone()[0]
    connection.commit()

    #Inserting into Task Table and status table
    Task = request.json['tasks']
    tidList = []
    date = datetime.now()
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        taskquery = f"INSERT INTO task (description, reminder) VALUES ('{description}', '{reminder}') RETURNING task_id"
        cursor.execute(taskquery)
        task_id = cursor.fetchone()[0]
        tidList.append({"task_id":task_id, "description":description})
        progressquery = f"INSERT INTO progress (checklist_id, task_id) VALUES ({checklist_id}, {task_id})"
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
        task_string += f"<br>-{tidList[index]['description']} <a href='http://127.0.0.1:5000/progress/{checklist_id}/{tidList[index]['task_id']}'>Click Here to Mark As Complete</a>"
    print(task_string)

    try:
        msg = Message(f"{company} {transition} Checklist for {first_name} {last_name}", sender="donotreply.daughertytransitions@gmail.com", recipients=[f"{email}"])
        msg.html = f"<h2>{company} {transition} Checklist for {first_name} {last_name}</h2>{task_string}"
        mail.send(msg)
        return json.dumps({"Status Code":200})
    except:
        return("error") 



@app.route('/progress/<int:checklist_id>/<int:task_id>', methods = ["GET"])
def progressUpdate(checklist_id, task_id):
    connection = connectPG()
    cursor = connection.cursor()
    date = datetime.now()
    update = f"UPDATE progress SET iscomplete = true WHERE checklist_id = {checklist_id} and task_id = {task_id}"
    date = f"UPDATE progress SET date_complete = '{date}' where checklist_id = {checklist_id} and task_id = {task_id}"
    cursor.execute(update)
    cursor.execute(date)
    connection.commit()
    return json.dumps({"Status Code 200": "Task has been marked complete"})




@app.route('/details/<int:checklist_id>', methods = ["GET"])
def details(checklist_id):
    connection = connectPG()
    cursor = connection.cursor()
    detailquery = f"SELECT first_name, last_name, company, isonboarding, date_sent, description, iscomplete, date_complete\
        from progress p\
        join task t on p.task_id = t.task_id\
        join checklist c on c.checklist_id = p.checklist_id\
        join checklist_task_join ct on ct.checklist_id = c.checklist_id\
        join consultant co on co.consultant_id = ct.consultant_id\
        where p.checklist_id = {checklist_id}"


    cursor.execute(detailquery)
    record = cursor.fetchall()
    colnames = ['first_name','last_name','company','isOnboarding','date_sent','description','isComplete', "date_complete"]
    results = []
    for row in record:
        results.append(dict(zip(colnames, row)))
    cursor.close()
    connection.close()
    return jsonify(results)

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


    checklist_query = f"INSERT INTO checklist_template (isonboarding, company, checklist_name)\
        VALUES ('{isOnboarding}', '{company}', '{name}') RETURNING checklistTemplate_id"
    cursor.execute(checklist_query)
    checklistTemplate_id = cursor.fetchone()[0]
    connection.commit()

    #Inserting into Task Table and status table
    Task = request.json['tasks']
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        taskquery = f"INSERT INTO task_template (description,reminder) VALUES ('{description}', '{reminder}') RETURNING taskTemplate_id"
        cursor.execute(taskquery)
        taskTemplate_id = cursor.fetchone()[0]
        joinquery = f"INSERT INTO template_join (checklistTemplate_id, taskTemplate_id) VALUES ({checklistTemplate_id},{taskTemplate_id})"
        cursor.execute(joinquery)
        connection.commit()
    cursor.close()
    connection.close()

    return json.dumps({"Status Code":200})


@app.route('/alltemplates', methods = ["GET"])
def alltempaltes():
    connection = connectPG()
    cursor = connection.cursor()
    query = f"Select checklistTemplate_id, checklist_name\
                from checklist_template ct\
                join template_join tj on ct.checklistTemplate_id = tj.checklistTemplate_id\
                join task_template tt on tt.taskTemplate_id = tj.taskTemplate_id"
    cursor.execute(query)
    records = cursor.fetchall()
    colnames = ['checklistTemplate_id', 'name']
    results = []
    for row in records:
            results.append(dict(zip(colnames, row)))
    cursor.close()
    connection.close()
    return jsonify(results)


@app.route('/gettemplate/<int:checklistTemplate_id>', methods = ["GET"])
def gettemplate(checklistTemplate_id):
    connection = connectPG()
    cursor = connection.cursor()
    query = f"select ct.checklistTemplate_id, ct.checklist_name, isonboarding, company, description, reminder\
        from checklist_template ct\
        join template_join on ct.checklistTemplate_id = template_join.checklistTemplate_id\
        join task_template tt on tt.taskTemplate_id = tj.taskTemplate_id\
        where ct.checklistTemplate_id = {checklistTemplate_id}"
    cursor.execute(query)
    records = cursor.fetchall()
    tasklist = []
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