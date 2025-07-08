# import mysql.connector

# from subprocess import Popen, PIPE
# from constants.global_constants import dbName, dbHost, dbUser, dbPassword



# import mysql.connector

# connection = mysql.connector.connect(
#     host=dbHost
#     user=dbUser,
#     password=dbPassword,
#     dbName=dbName,
#     port=3306
# )

# print("Connected successfully!")
# connection.close()

# import mysql.connector
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Connect to MySQL using Docker service 'db'
# print("Connecting to MySQL database...")

# options = {
#     "host": os.getenv("DB_HOST", "db"),
#     "user": os.getenv("DB_USER", "root"),
#     "password": os.getenv("DB_PASSWORD", "").strip('"') or None,
#     "database": os.getenv("DB_NAME", "agents"),
#     "port": int(os.getenv("DB_PORT", 3306)),
# }

# connection = mysql.connector.connect(
#     host=options["host"],
#     user=options["user"],
#     password=options["password"],
#     database=options["database"],
#     port=options["port"],
# )

# cur = connection.cursor()

# # Read and execute schema
# project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# schema_path = os.path.join(project_root, "database", "schema.sql")

# with open(schema_path, encoding='utf8') as f:
#     sql_script = f.read()
#     for result in cur.execute(sql_script, multi=True):
#         pass  # Optionally log result

# connection.commit()
# cur.close()
# connection.close()

# print("Database initialized successfully.")


import mysql.connector

from subprocess import Popen, PIPE

dbName = "agents"

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

# Close the connection
connection.close()