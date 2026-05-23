# CS 122A
# ZotEvent Platform Database Management
# Members: Kyi Lei Aye, Chris Guo, Lana Chen, Scarlett Feng

import sys
import mysql.connector
import csv
import os

def connect_db():
    conn = mysql.connector.connect(
        host = "localhost",
        user='root',
        password='', # add your own password here
        database='ZotEvent',
        allow_local_infile=True
    )
    return conn

def load_csv(cursor, csv_path, table_name):
    sql = f"LOAD DATA LOCAL INFILE %s INTO TABLE {table_name} FIELDS TERMINATED BY ',' ENCLOSED BY '\"'"
    cursor.execute(sql, (csv_path,))
    
CSV_TABLE_MAP = {
    'User.csv': 'User',
    'Organizer.csv': 'Organizer',
    'Participant.csv': 'Participant',
    'Administrator.csv': 'Administrator',
    'Event.csv': 'Event',
    'Slot.csv': 'Slot',
    'Venue.csv': 'Venue',
    'OnCampus.csv': 'OnCampus',
    'OffCampus.csv': 'OffCampus',
    'Hosting.csv': 'Hosting',
    'Approval.csv': 'Approval',
}

def drop_tables(cursor):
    cursor.execute('SET FOREIGN_KEY_CHECKS = 0') # this doesn't let u to drop the table if the table is parent table to other tables
    
    tables = [
        "Administrator",
        "Approval",
        "Event",
        "Hosting",
        "OffCampus",
        "OnCampus",
        "Organizer",
        "Participant",
        "Slot",
        "User",
        "Venue"
    ]
    
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

def create_tables(cursor):
    cursor.execute("""
        CREATE TABLE User (
            uid INT,
            email TEXT NOT NULL,
            username TEXT NOT NULL,
            joined DATE NOT NULL,
            PRIMARY KEY (uid)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Organizer (
            uid INT,
            department TEXT NOT NULL,
            experience INT NOT NULL,
            PRIMARY KEY (uid),
            FOREIGN KEY (uid) REFERENCES User(uid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Participant (
            uid INT,
            type TEXT,
            PRIMARY KEY (uid),
            FOREIGN KEY (uid) REFERENCES User(uid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Administrator (
            uid INT,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            PRIMARY KEY (uid),
            FOREIGN KEY (uid) REFERENCES User(uid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Event (
            eid INT,
            creator_uid INT NOT NULL,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            datetime DATETIME NOT NULL,
            PRIMARY KEY (eid),
            FOREIGN KEY (creator_uid) REFERENCES Organizer(uid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Slot (
            eid INT,
            snum INT NOT NULL,
            is_reserved BOOLEAN NOT NULL,
            uid INT,
            PRIMARY KEY (eid, snum),
            FOREIGN KEY (eid) REFERENCES Event(eid) ON DELETE CASCADE,
            FOREIGN KEY (uid) REFERENCES Participant(uid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Venue (
            vid INT,
            street TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            zip TEXT NOT NULL,
            PRIMARY KEY (vid)
        )
    """)

    cursor.execute("""
        CREATE TABLE OnCampus (
            vid INT,
            code TEXT NOT NULL,
            PRIMARY KEY (vid),
            FOREIGN KEY (vid) REFERENCES Venue(vid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE OffCampus (
            vid INT,
            distance INT NOT NULL,
            PRIMARY KEY (vid),
            FOREIGN KEY (vid) REFERENCES Venue(vid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Hosting (
            eid INT NOT NULL,
            vid INT NOT NULL,
            is_primary BOOLEAN NOT NULL,
            PRIMARY KEY (eid, vid),
            FOREIGN KEY (eid) REFERENCES Event(eid) ON DELETE CASCADE,
            FOREIGN KEY (vid) REFERENCES Venue(vid) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Approval (
            uid INT NOT NULL,
            vid INT NOT NULL,
            valid_from DATE NOT NULL,
            valid_until DATE NOT NULL,
            PRIMARY KEY (uid, vid),
            FOREIGN KEY (uid) REFERENCES Administrator(uid) ON DELETE CASCADE,
            FOREIGN KEY (vid) REFERENCES OffCampus(vid) ON DELETE CASCADE
        )
    """)

# import data
def import_data(args):
    """
    Delete existing tables, and create new tables.
    Then read the csv files in the given folder and import data into the database.
    We can assume that the folder always contains all the necessary CSV files and the files are correct.
    Args:
        folder (str): the folder that contains csv files
    """
    
    folder_path = args[0]
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        drop_tables(cursor)
        create_tables(cursor)
    
        for csv_file, table_name in CSV_TABLE_MAP.items():
            csv_path = os.path.abspath(os.path.join(folder_path, csv_file))
            load_csv(cursor, csv_path, table_name)
            # print(f"Loaded {csv_file} into {table_name}")
            
        conn.commit()
        # print('Import completed successfully.')
        return True
    
    except mysql.connector.Error as err:
        conn.rollback()
        # print(f"MySQL Error: {err}")
        return False
        
    finally:
        cursor.close()
        conn.close()
        
def main():
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == 'import':
        result = import_data(args)
        print(result)
    
if __name__ == '__main__':
    main()    