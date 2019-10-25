from flask import request, Flask, jsonify, redirect, url_for
from flask_cors import CORS
import psycopg2 as pg
from psycopg2 import Error
from datetime import datetime
import json 
from flask_mail import Message, Mail
import time
import pytz

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


    checklist_query = f"INSERT INTO checklist (isonboarding, company, checklist_name)\
        VALUES (%s, %s, %s) RETURNING checklist_id"
    cursor.execute(checklist_query, (isOnboarding, company, name))
    checklist_id = cursor.fetchone()[0]
    connection.commit()


    #Inserting into Consultant Table
    email = request.json['email']
    name = email.split('.')
    name_2 = name[1].split("@")
    first_name = name[0].capitalize()
    last_name = name_2[0].capitalize()

    consultant_query = f"INSERT INTO consultant (first_name, last_name, email)\
        VALUES (%s, %s, %s) RETURNING consultant_id"
    cursor.execute(consultant_query, (first_name, last_name, email))
    consultant_id = cursor.fetchone()[0]
    connection.commit()

    #Inserting into Task Table and status table
    Task = request.json['tasks']
    tidList = []
    date = (datetime.now()).astimezone(pytz.timezone("Etc/GMT"))
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        try:
            html = Task[x]['html']
        except:
            html = 'null'
        taskquery = f"INSERT INTO task (description, reminder, html) VALUES (%s, %s, %s) RETURNING task_id"
        cursor.execute(taskquery, (description, reminder, html))
        task_id = cursor.fetchone()[0]
        tidList.append({"task_id":task_id, "description":description, "html":html})
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
        print(tidList[index]['html'])
        if (tidList[index]['html'] is 'null') or (tidList[index]['html'] is None):
            task_string += f"<tr><td style= 'font-family:arial,helvetica,sans-serif; width: 250px;'>\
                <p style='list-style:disc outside none; display:list-item'>{tidList[index]['description']}</p></td>\
                <td> </td>\
                <td style= 'font-family:arial,helvetica,sans-serif; width: 250px;'>\
                <a href='http://127.0.0.1:5000/progress/{checklist_id}/{tidList[index]['task_id']}'>Click here to mark as complete.</a></td></tr>"
        else:
            task_string += f"<tr><td style= 'font-family:arial,helvetica,sans-serif; width: 250px;'>\
                <p style='list-style:disc outside none; display:list-item'>{tidList[index]['description']}</p></td>\
                <td style= 'font-family:arial,helvetica,sans-serif; width: 250px; '><a href='{tidList[index]['html']}'>'{tidList[index]['html']}'</a></td>\
                <td style= 'font-family:arial,helvetica,sans-serif; width: 250px;'><a href='http://127.0.0.1:5000/progress/{checklist_id}/{tidList[index]['task_id']}'>Click here to mark as complete.</a></td></tr>"


    try:
        msg = Message(f"{company} {transition} Checklist for {first_name} {last_name}", sender="donotreply.daughertytransitions@gmail.com", recipients=[f"{email}"])
        msg.html = f'<h2 style="text-align: center; font-family:arial,helvetica,sans-serif;">{company} {transition} Checklist for {first_name} {last_name}</h2>\
            <p style="text-align: center; font-family:arial,helvetica,sans-serif;">To smooth the transition between engagements your team manager has compiled \
            a list of the following tasks that must be completed.&nbsp;</p>\
            <p style="text-align: center; font-family:arial,helvetica,sans-serif;">Please complete each task and click the link to mark the task as completed.</p>\
            <p>&nbsp;</p><table><tbody>{task_string}</tbody></table>\
            <p style="text-align: center; font-family:arial,helvetica,sans-serif;">&nbsp;\
                <a href="http://localhost:4200/confirm/{checklist_id}">Click here to view checklist details webpage.</a></p>\
            <p style="text-align: center; font-family:arial,helvetica,sans-serif;">&nbsp;Thank you,</p>\
            <p><img style="float: left:" src="https://github.com/doks17808/TeamWon/blob/master/daugherty_stacked.jpg?raw=true" alt="" width="238" height="74" /></p>'
        mail.send(msg)
        return json.dumps({"Status Code":200})
    except:
        return("error") 



@app.route('/progress/<int:checklist_id>/<int:task_id>', methods = ["GET"])
def progressUpdate(checklist_id, task_id):
    connection = connectPG()
    cursor = connection.cursor()
    date = (datetime.now()).astimezone(pytz.timezone("Etc/GMT"))
    update = f"UPDATE progress SET iscomplete = true WHERE checklist_id = {checklist_id} and task_id = {task_id}"
    date = f"UPDATE progress SET date_complete = '{date}' where checklist_id = {checklist_id} and task_id = {task_id}"
    cursor.execute(update)
    cursor.execute(date)
    connection.commit()
    return redirect(f"http://localhost:4200/confirm/{checklist_id}")















##################################################################
################ HOME PAGE AND CHECKLIST DETAILS #################
##################################################################


@app.route('/home', methods = ["GET", "PATCH"])
def home():
    connection = connectPG()
    cursor = connection.cursor()
    if (request.method == 'PATCH'):
        checklist_id = request.json["cid"]
        remove = f"UPDATE checklist SET remove = true WHERE checklist_id = {checklist_id}"
        cursor.execute(remove)
        connection.commit()
        cursor.close()
        connection.close()
        return json.dumps({"Status Code":200})
    else:
        query = "SELECT consultant.consultant_id as consultant_id, concat(first_name, ' ', last_name) Consultant, checklist_task_join.checklist_id as cid, checklist.company as Client, checklist.isOnboarding as Transition, checklist_task_join.date_sent as DateSent, COUNT(CASE WHEN isComplete THEN 1 END) * 100 / count(checklist_task_join.task_id) AS progress \
                FROM consultant \
                    JOIN checklist_task_join ON checklist_task_join.consultant_id = consultant.consultant_id \
                    JOIN progress ON progress.checklist_id = checklist_task_join.checklist_id \
                    JOIN checklist ON checklist.checklist_id = checklist_task_join.checklist_id \
                    WHERE checklist.remove = false\
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
    detailquery = f"SELECT first_name, last_name, company, isonboarding, date_sent, description, reminder, iscomplete, date_complete, t.task_id, t.html\
        from checklist_task_join ct\
        join progress p on ct.checklist_id = p.checklist_id and ct.task_id = p.task_id\
        join task t on ct.task_id = t.task_id\
        join checklist c on c.checklist_id = ct.checklist_id\
        join consultant co on co.consultant_id = ct.consultant_id\
        where p.checklist_id = {checklist_id}"

    cursor.execute(detailquery)
    records = cursor.fetchall()
    tasklist = []
    for x in range(len(records)):
        task = {}
        task['description'] = records[x][5]
        task['reminder'] = records[x][6]
        task['isComplete'] = records[x][7]
        task['date_complete'] = records[x][8]
        task['task_id'] = records[x][9]
        task['html'] =records[x][10]
        tasklist.append(task)
    ChecklistDetails = {"checklist_id": checklist_id, "first_name":records[0][0], "last_name":records[0][1], "company":records[0][2], "isOnboarding":records[0][3], "date_sent":records[0][4]}
    ChecklistDetails['tasks'] = tasklist
    return jsonify(ChecklistDetails)



@app.route('/detailprogress/<int:checklist_id>/<int:task_id>/<complete>', methods = ["PATCH"])
def detailprogress(checklist_id, task_id, complete):
    connection = connectPG()
    cursor = connection.cursor()
    date = (datetime.now()).astimezone(pytz.timezone("Etc/GMT"))
    print(date)
    if complete == 'true':
        update = f"UPDATE progress SET iscomplete = true WHERE checklist_id = {checklist_id} and task_id = {task_id}"
        date = f"UPDATE progress SET date_complete = '{date}' where checklist_id = {checklist_id} and task_id = {task_id}"
        cursor.execute(update)
        cursor.execute(date)
    else:
        update = f"UPDATE progress SET iscomplete = false WHERE checklist_id = {checklist_id} and task_id = {task_id}"
        date = f"UPDATE progress SET date_complete = null where checklist_id = {checklist_id} and task_id = {task_id}"
        cursor.execute(update)
        cursor.execute(date)
    connection.commit()
    return json.dumps({"Status Code":200})












##################################################################
################# Saving and Pulling Templates ###################
##################################################################
@app.route('/savetemplate', methods = ["POST"])
def savetemplate():
    connection = connectPG()
    cursor = connection.cursor()

    #Inserting into Checklist_template Table
    isOnboarding = request.json['isOnboarding']
    company = request.json['company']
    name = request.json['name']
    query = f"Select * from checklist_template where checklist_name = '{name}'"
    cursor.execute(query)
    records = cursor.fetchall()
    if len(records) == 0:
        checklist_query = f"INSERT INTO checklist_template (isonboarding, company, checklist_name)\
            VALUES (%s, %s, %s) RETURNING checklisttemplate_id"
        cursor.execute(checklist_query, (isOnboarding, company, name))
        checklisttemplate_id = cursor.fetchone()[0]
        connection.commit()


        Task = request.json['tasks']
        for x in range(len(Task)):
            description = Task[x]['description']
            reminder = Task[x]['reminder']
            try:
                html = Task[x]['html']
                taskquery = f"INSERT INTO task_template (description, reminder, html) VALUES (%s, %s, %s) RETURNING tasktemplate_id"
                cursor.execute(taskquery, (description, reminder, html))
            except:
                taskquery = f"INSERT INTO task_template (description, reminder) VALUES (%s, %s) RETURNING tasktemplate_id"
                cursor.execute(taskquery, (description, reminder))
            tasktemplate_id = cursor.fetchone()[0]
            joinquery = f"INSERT INTO template_join (checklisttemplate_id, tasktemplate_id) VALUES ({checklisttemplate_id},{tasktemplate_id})"
            cursor.execute(joinquery)
            connection.commit()
        cursor.close()
        connection.close()
        return json.dumps({"Status Code":200})



    else:
        checklist_query = f"UPDATE checklist_template\
            SET isonboarding = (%s),\
                company = (%s)\
            WHERE checklist_name = '{name}'\
            RETURNING checklisttemplate_id"
        cursor.execute(checklist_query, (isOnboarding, company))
        checklisttemplate_id = cursor.fetchone()[0]
        print(checklisttemplate_id)
        connection.commit()
        findtaskid = f"Select tasktemplate_id from template_join where checklisttemplate_id = {checklisttemplate_id}"
        cursor.execute(findtaskid)
        taskidtodelete = cursor.fetchall()
        connection.commit()
        deletejoins = f"DELETE from template_join where checklisttemplate_id = {checklisttemplate_id}"
        cursor.execute(deletejoins)
        connection.commit()
        print(taskidtodelete)
        for x in taskidtodelete:
            deletetasks = f"DELETE from task_template where tasktemplate_id = {x[0]}"
            cursor.execute(deletetasks)
            connection.commit()


        Task = request.json['tasks']
        for x in range(len(Task)):
            description = Task[x]['description']
            reminder = Task[x]['reminder']
            try:
                html = Task[x]['html']
                taskquery = f"INSERT INTO task_template (description, reminder, html) VALUES (%s, %s, %s) RETURNING tasktemplate_id"
                cursor.execute(taskquery, (description, reminder, html))
            except:
                taskquery = f"INSERT INTO task_template (description, reminder) VALUES (%s, %s) RETURNING tasktemplate_id"
                cursor.execute(taskquery, (description, reminder))
            tasktemplate_id = cursor.fetchone()[0]
            joinquery = f"INSERT INTO template_join (checklisttemplate_id, tasktemplate_id) VALUES ({checklisttemplate_id},{tasktemplate_id})"
            cursor.execute(joinquery)
            connection.commit()
        cursor.close()
        connection.close()
        return json.dumps({"Status Code":200})




@app.route('/alltemplates', methods = ["GET"])
def alltempaltes():
    connection = connectPG()
    cursor = connection.cursor()
    query = "Select ct.checklisttemplate_id, checklist_name\
                from checklist_template ct where isarchived = false"
    cursor.execute(query)
    records = cursor.fetchall()
    colnames = ['checklisttemplate_id', 'name']
    results = []
    for row in records:
            results.append(dict(zip(colnames, row)))
    cursor.close()
    connection.close()
    return jsonify(results)



@app.route('/searchtemplates', methods = ["GET"])
def searchtempaltes():
    connection = connectPG()
    cursor = connection.cursor()
    qstring = request.json['query']
    query = f"Select ct.checklisttemplate_id, checklist_name\
                from checklist_template ct where isarchived = false and checklist_name ILIKE '%{qstring}%'"
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
    query = f"select ct.checklisttemplate_id, ct.checklist_name, isonboarding, company, description, reminder, html\
        from checklist_template ct\
        join template_join tj on ct.checklisttemplate_id = tj.checklisttemplate_id\
        join task_template tt on tt.tasktemplate_id = tj.tasktemplate_id\
        where ct.checklisttemplate_id = {checklisttemplate_id} and ct.isarchived = false"
    cursor.execute(query)
    records = cursor.fetchall()
    if len(records) == 0:
        return 'template does not exist'
    else:
        tasklist = []
        for x in range(len(records)):
            task = {}
            task['description'] = records[x][4]
            task['reminder'] = records[x][5]
            task['html'] = records[x][6]
            tasklist.append(task)
        savedChecklist = {"name":records[0][1], "isOnboarding":records[0][2], "company":records[0][3]}
        savedChecklist['tasks'] = tasklist
        print(savedChecklist)
        return jsonify(savedChecklist)



@app.route('/archivetemplate/<int:checklisttemplate_id>/<archive>', methods = ["PATCH"])
def archivetemplate(checklisttemplate_id, archive):
    connection = connectPG()
    cursor = connection.cursor()
    if archive == 'true':
        update = f"UPDATE checklist_template SET isarchived = true WHERE checklisttemplate_id = {checklisttemplate_id}"
        cursor.execute(update)
    else:
        update = f"UPDATE cehcklist_template SET isarchived = false WHERE checklisttemplate_id = {checklisttemplate_id}"
        cursor.execute(update)
    connection.commit()
    return json.dumps({"Status Code":200})


if __name__ == "__main__":

    app.run(debug=True)