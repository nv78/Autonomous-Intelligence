import mysql.connector

from subprocess import Popen, PIPE

dbName = "agents"
root_password = 'my password'
process = Popen(['mysql', dbName, '-u', 'root', f'-p{root_password}'],
                stdout=PIPE, stdin=PIPE)
output = process.communicate(b'source ' + b'schema.sql')[0]

connection = mysql.connector.connect(
    user='root',
    password=root_password,      
    unix_socket='/var/run/mysqld/mysqld.sock',  
    database=dbName,
)

# Create a cursor
cur = connection.cursor()

# Close the connection
connection.close()