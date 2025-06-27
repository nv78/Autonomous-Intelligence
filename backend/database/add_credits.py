import mysql.connector
from constants.global_constants import dbName

from subprocess import Popen, PIPE
process = Popen(['mysql', dbName, '-u', 'root'],
                stdout=PIPE, stdin=PIPE)
output = process.communicate(b'source ' + b'schema.sql')[0]

connection = mysql.connector.connect(
    user='root',
    unix_socket='/tmp/mysql.sock',
    database=dbName,
)

# Create a cursor
cur = connection.cursor()
cur.execute("SELECT * FROM users ORDER BY id ASC LIMIT 1")
users = cur.fetchall()
if len(users) == 0:
    print("NO USERS")
else:
    user = users[0]
    print(user["id"])
    cur.execute("INSERT INTO StripeInfo (user_id, stripe_customer_id, anchor_date) VALUES (1, 'id', CURRENT_TIMESTAMP)")
    cur.execute("INSERT INTO Subscriptions (stripe_info_id, subscription_id, start_date, paid_user) VALUES (1, 'id', CURRENT_TIMESTAMP, 3)")
    connection.commit()
# Close the connection
connection.close()