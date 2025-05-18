import psycopg2
from psycopg2 import Error

DB_CONFIG = {
    'dbname': 'campus_connect',
    'user': 'postgres',
    'password': 'indhu0504',
    'host': 'localhost',
    'port': '5432'
}

def create_tables():
    conn = None  # Initialize conn to None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Create faculty table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            )
        """)
        
        # Updated schedules table with busy flag
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                faculty_id INTEGER REFERENCES faculty(id),
                day VARCHAR(10),
                start_time TIME,
                end_time TIME,
                room VARCHAR(50),
                is_temporary BOOLEAN DEFAULT FALSE,
                is_busy BOOLEAN DEFAULT FALSE,  -- Added busy flag
                original_schedule_id INTEGER,    -- Added reference to original schedule
                original_start_time TIME,
                original_end_time TIME,
                valid_until DATE,
                CONSTRAINT valid_times CHECK (start_time < end_time)
            )
        """)
        
        # Updated deleted_schedules table with deleted_by field
        cur.execute("""
            DROP TABLE IF EXISTS deleted_schedules;
            CREATE TABLE deleted_schedules (
                id SERIAL PRIMARY KEY,
                faculty_id INTEGER,
                day VARCHAR(10),
                start_time TIME,
                end_time TIME,
                room VARCHAR(50),
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason VARCHAR(200),
                deleted_by VARCHAR(100),
                original_schedule_id INTEGER
            )
        """)
        
        conn.commit()
        print("Tables created successfully!")
        
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL:", error)
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_tables()