import requests
import json
from datetime import datetime,timedelta
import mysql.connector
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys


# Gathers new responses from typeform
def get_new_responses(id, interval, token):
    base_url = 'https://api.typeform.com/forms/'
    now = (datetime.utcnow() - timedelta(minutes=interval)).isoformat()
    payload = {"since": (now)}
    headers = {"Authorization": "Bearer " + token}
    new_forms = requests.get(base_url + id + '/responses', params=payload, headers=headers)
    print(datetime.utcnow(), ": Recieved", new_forms.json()['total_items'], "new responses")
    return new_forms.json()

#Writes new matches to the database, then checks for a match. In case of a match, sends a mail and updates db to reflect situation
def match(new_responses, db_keys, version, password):
    # Connect to database
    mydb = mysql.connector.connect(
        host="34.68.68.217",
        user="peer_review",
        passwd="Extraordinary2014!",
        database='peer_review'
    )
    mycursor = mydb.cursor()

    #Insert every new response
    for response in new_responses['items']:

        # Check if response has already been written to db
        mycursor.execute('SELECT * FROM responses WHERE response_id = "' + response['response_id'] + '";')
        is_new = mycursor.fetchall()
        if is_new == []:
            # Prepare insert statement that will recond the response to the db
            insert = 'INSERT INTO responses' + db_keys + 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s);'
            val = [response['response_id']]
            for answer in response['answers']:
                val.append(str(answer[answer['type']]))
            val.append(response['submitted_at'])
            val.append(0)
            val.append(version)
            mycursor.execute(insert, val)
            mydb.commit()
            print(datetime.utcnow(), ":", mycursor.rowcount, "record added to db.")

            # Check for matches
            query = 'SELECT response_id, email, name from responses WHERE matched = 0 and response_id not like %s and assignment = %s' \
                    ' and grade <= %s + 0.3 and grade >= %s - 0.3 order by date'
            match_values = (val[0], val[3], val[4], val[4]) #response_id, assignment name, grade, grade
            mycursor.execute(query, match_values)
            match = mycursor.fetchone() #The first record (oldest) will be matched
            if match is not None:
                print(datetime.utcnow(), ": Match found for ", val[2], "! It is ", match[2])
                # Gets rid of the rest of the matches. They must be read or errors will occur
                row = mycursor.fetchone()
                while row is not None:
                    row = mycursor.fetchone()

                #Send mails to announce the match
                send_mail(val[1], val[2], match[1], match[2], password)
                send_mail(match[1], match[2], val[1], val[2], password)

                # Update database to reflect that those submissions have been matched
                mycursor.execute('UPDATE responses SET matched = 1 WHERE response_id = "' + match[0] + '";')
                mycursor.execute('UPDATE responses SET matched = 1 WHERE response_id = "' + val[0] + '";')
                mydb.commit()


# Sends mail to people who have been matched
def send_mail(receiver_email, receiver_name, match_email, match_name, password):
    port = 465
    sender_email = "minervapeerreview@gmail.com"
    #Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Peer Review Match Found!"
    body = """Hello {},

You have been matched with {} for peer review. Please send them your assignment. Thier email is {} 
It is recommended to upload your assignment to google docs and give your match review or edit access

Good luck!""".format(receiver_name,match_name,match_email)
    msg.attach(MIMEText(body, 'plain'))
    # Connect with SSL to gmail smtp server
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print(datetime.utcnow(), ": Message sent to", receiver_email)

def main():
    # Set some variables
    db_keys = "(response_id, email , name, assignment, grade, date, matched, version)"
    form_id = "Vm9kJN"
    interval = 3
    password = sys.argv[1] #Gmail password
    token = sys.argv[2] # Token for Typeform
    new_responses = get_new_responses(form_id, interval, token)
    match(new_responses, db_keys, 1, password)

if __name__ == '__main__':
    main()
