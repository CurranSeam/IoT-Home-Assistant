# Utility to create the tables for the database. Run one of these functions
# before inserting any data into the database.

from application import database
from application.models.user import User

# Create all initial tables
def create_tables():
    with database:
        database.create_tables([User])

# Create or add a given table
def create_table(table):
    with database:
        database.create_tables([table])
