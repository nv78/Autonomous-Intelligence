import mysql.connector
import os

from subprocess import Popen, PIPE
db_password = os.getenv('MYSQL_ROOT_PASSWORD')
dbName = "agents"

process = Popen(['mysql', dbName, '-u', 'root'],
                stdout=PIPE, stdin=PIPE)
output = process.communicate(b'source ' + b'schema.sql')[0]

connection = mysql.connector.connect(
    user='root',
    password=db_password,
    unix_socket='/tmp/mysql.sock',
    database=dbName,
)

# Create a cursor
cur = connection.cursor()

# Close the connection
connection.close()