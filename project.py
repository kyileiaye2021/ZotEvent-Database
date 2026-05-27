# CS 122A
# ZotEvent Platform Database Management
# Members: Kyi Lei Aye, Chris Guo, Lana Chen, Scarlett Feng

import sys
import mysql.connector
import csv
import os

def connect_db():
    conn = mysql.connector.connect(
        host="localhost",
        user='root',
        password='', # add your own password here
        database='ZotEvent',
        allow_local_infile=True,
        use_pure=True #Scarlett adds one line here
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
def import_data(args, cursor):
    """
    Delete existing tables, and create new tables.
    Then read the csv files in the given folder and import data into the database.
    We can assume that the folder always contains all the necessary CSV files and the files are correct.
    Args:
        folder (str): the folder that contains csv files
    """
    
    folder_path = args[0]
    
    drop_tables(cursor)
    create_tables(cursor)
    
    for csv_file, table_name in CSV_TABLE_MAP.items():
        csv_path = os.path.abspath(os.path.join(folder_path, csv_file))
        load_csv(cursor, csv_path, table_name)
    return True
        
# insert administrator
def insertAdmin(args, cursor):
    """
    Insert a new user and administrator into the related tables.
    """
    uid = args[0]
    email = args[1]
    username = args[2]
    joined = args[3]
    firstname = args[4]
    lastname = args[5]
    
    cursor.execute("""
        INSERT INTO User (uid, email, username, joined)
        VALUES (%s, %s, %s, %s)
    """, (uid, email, username, joined))
    
    cursor.execute("""
        INSERT INTO Administrator (uid, firstname, lastname)
        VALUES(%s,%s,%s)
    """, (uid,firstname,lastname))
    
    return True

# add venue to event
def addVenue(args, cursor):
    """
    Add a venue to an existing event by inserting it into the Hosting relationship.
    The event and venue already exist.  If is_primary = true, the function should ensure this event has no other primary venue.
    If another primary venue already exists, return False.
    
    If the same venue and event are added, the row will not be added as vid and eid are primary keys and should not be duplicated
    """
    eid = args[0]
    vid = args[1]
    is_primary = args[2].lower() == 'true'
    
    if is_primary:
        # ensure that the event has no other primary venue
        # the event should have only one primary venue
        cursor.execute(""" 
            SELECT COUNT(*) FROM Hosting
            WHERE eid = %s AND is_primary = TRUE     
        """, (eid,))
        count = cursor.fetchone()[0]
        if count > 0:
            return False # the event already has primary venue, return false
    
    # if there is no primary venue in that eid, add the incoming venue and set it as primary venue
    try:
        # first try adding the row into hosting
        # if the eid or vid exist in primary tables, return false
        cursor.execute("""
            INSERT INTO Hosting (eid, vid,is_primary)
            VALUES(%s, %s, %s)
        """, (eid, vid, is_primary))
    except mysql.connector.Error:
        return False
    
    return True



# Q4: reserve slot
def reserveSlot(args, cursor):
    """
    Reserve a specific slot for a participant.
    The event, slot, and participant already exist.
    The slot must currently be unreserved.
    """
    eid = args[0]
    snum = args[1]
    uid = args[2]

    try:
        # First check whether this slot is currently unreserved
        cursor.execute("""
            SELECT is_reserved
            FROM Slot
            WHERE eid = %s AND snum = %s
        """, (eid, snum))

        row = cursor.fetchone()

        # If the slot does not exist, fail
        if row is None:
            return False

        # If the slot is already reserved, fail
        if row[0] == 1 or row[0] is True:
            return False

        # Reserve the slot
        cursor.execute("""
            UPDATE Slot
            SET is_reserved = TRUE, uid = %s
            WHERE eid = %s AND snum = %s
        """, (uid, eid, snum))

        return cursor.rowcount == 1

    except mysql.connector.Error:
        return False


# Q5: cancel reservation
def cancelReservation(args, cursor):
    """
    Cancel a participant's reservation for a specific event slot.
    Only cancel if the slot is currently reserved by the given participant.
    """
    eid = args[0]
    snum = args[1]
    uid = args[2]

    try:
        # First check whether this slot is reserved by this participant
        cursor.execute("""
            SELECT is_reserved, uid
            FROM Slot
            WHERE eid = %s AND snum = %s
        """, (eid, snum))

        row = cursor.fetchone()

        # If the slot does not exist, fail
        if row is None:
            return False

        is_reserved = row[0]
        current_uid = row[1]

        # Only cancel if the slot is reserved by this exact participant
        if not (is_reserved == 1 or is_reserved is True):
            return False

        if str(current_uid) != str(uid):
            return False

        # Cancel the reservation
        cursor.execute("""
            UPDATE Slot
            SET is_reserved = FALSE, uid = NULL
            WHERE eid = %s AND snum = %s
        """, (eid, snum))

        return cursor.rowcount == 1

    except mysql.connector.Error:
        return False

# Q6: update event
def updateEvent(args, cursor):
    """
    Update the title and datetime of an event.
    """
    eid = args[0]
    title = args[1]
    event_datetime = args[2]

    try:
        cursor.execute("""
            UPDATE Event
            SET title = %s, datetime = %s
            WHERE eid = %s
        """, (title, event_datetime, eid))

        return cursor.rowcount == 1

    except mysql.connector.Error:
        return False

# Q7: delete organizer
def deleteOrganizer(args, cursor):
    """
    Delete an organizer from the database.
    """
    uid = args[0]

    try:
        cursor.execute("DELETE FROM Organizer WHERE uid = %s", (uid,))
        return cursor.rowcount == 1
    
    except mysql.connector.Error:
        return False
    
# Q8: upcoming events with available slots
def availableEvents(args, cursor):
    """
    List all future events that still have at least one unreserved slot.
    """
    date = args[0]

    cursor.execute("""
        SELECT e.eid, e.title, e.type, e.datetime,
               SUM(CASE WHEN s.is_reserved = FALSE THEN 1 ELSE 0 END) AS availableSlots
        FROM Event e
        JOIN Slot s ON e.eid = s.eid
        WHERE e.datetime > %s
        GROUP BY e.eid, e.title, e.type, e.datetime
        HAVING availableSlots > 0
        ORDER BY e.datetime ASC, e.eid ASC
    """, (date,))

    rows = cursor.fetchall()
    for r in rows:
        print(f"{r[0]},{r[1]},{r[2]},{r[3]},{int(r[4])}")
    return True

# Q9: popular event types
def popularEventTypes(args, cursor):
    """
    For each event type, total number of reserved slots across all events of that type.
    """
    N = args[0]

    cursor.execute("""
        SELECT e.type,
               COALESCE(SUM(CASE WHEN s.is_reserved = TRUE THEN 1 ELSE 0 END), 0) AS reservedCount
        FROM Event e
        LEFT JOIN Slot s ON e.eid = s.eid
        GROUP BY e.type
        HAVING reservedCount >= %s
        ORDER BY reservedCount DESC, e.type ASC
    """, (N,))
    
    rows = cursor.fetchall()
    for r in rows:
        print(f"{r[0]},{int(r[1])}")
    return True

def print_bool(result):
    if result:
        print("Success")
    else:
        print("Fail")


def main():
    conn = connect_db()
    cursor = conn.cursor()
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'import':
            result = import_data(args, cursor)
            print(result)
            conn.commit() # commit it so it saves in the database
        
        elif command == 'insertAdmin':
            result = insertAdmin(args, cursor)
            print(result)
            conn.commit() 
        
        elif command == 'addVenue':
            result = addVenue(args, cursor)
            print(result)
            conn.commit()
        #Q4-6
        elif command == 'reserveSlot':
            result = reserveSlot(args, cursor)
            conn.commit()
            print_bool(result)

        elif command == 'cancelReservation':
            result = cancelReservation(args, cursor)
            conn.commit()
            print_bool(result)

        elif command == 'updateEvent':
            result = updateEvent(args, cursor)
            conn.commit()
            print_bool(result)

        elif command == 'deleteOrganizer':
            result = deleteOrganizer(args, cursor)
            conn.commit()
            print_bool(result)

        elif command == 'availableEvents':
            availableEvents(args, cursor)

        elif command == 'popularEventTypes':
            popularEventTypes(args, cursor)
                
    except mysql.connector.Error as err:
        conn.rollback()
        print(f"MySQL Error: {err}")
        
    finally:
        cursor.close()
        conn.close()
        
if __name__ == '__main__':
    main()    