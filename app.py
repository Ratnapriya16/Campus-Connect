from flask import Flask, render_template, redirect, session, request, flash, jsonify, url_for
import psycopg2
import os
from database import DB_CONFIG
from flask import Flask, request, jsonify
from io import StringIO
import csv
from psycopg2.extras import DictCursor
import io


template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.secret_key = "test123"

# Hardcoded admin credentials for testing
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Update your DB_CONFIG with correct credentials
DB_CONFIG = {
    'dbname': 'campus_connect',
    'user': 'postgres',  # Changed from 'postgre' to 'postgres'
    'password': 'indhu0504',  # Make sure this matches your PostgreSQL password
    'host': 'localhost',
    'port': '5432'
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin-login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin-panel')
        else:
            flash('Invalid credentials')
            return redirect('/admin-login')
    
    return render_template("admin_login.html")

@app.route("/admin-panel")
def admin_panel():
    if not session.get('admin'):
        return redirect('/admin-login')
    return render_template("admin_panel.html")

# Add this route for adding faculty
@app.route("/add-faculty", methods=['POST'])
def add_faculty():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    faculty_name = request.form.get('faculty_name')
    if not faculty_name:
        return jsonify({'error': 'Faculty name is required'}), 400
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Insert the faculty
        cur.execute(
            "INSERT INTO faculty (name) VALUES (%s) RETURNING id",
            (faculty_name,)
        )
        faculty_id = cur.fetchone()[0]
        conn.commit()
        
        # Return success response
        return jsonify({
            'success': True,
            'id': faculty_id,
            'name': faculty_name
        })
        
    except psycopg2.Error as e:
        # If there's an error, rollback the transaction
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        # Always close cursor and connection
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route("/get-faculty")
def get_faculty():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("SELECT id, name FROM faculty ORDER BY name")
        faculties = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
        return jsonify(faculties)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
@app.route("/search-faculty", methods=['POST'])
def search_faculty():
    faculty_name = request.form.get('faculty_name')
    search_day = request.form.get('day')
    search_start = request.form.get('start_time')
    search_end = request.form.get('end_time')
    
    print(f"Search parameters: faculty={faculty_name}, day={search_day}, start={search_start}, end={search_end}")
    
    if not all([faculty_name, search_day, search_start, search_end]):
        return jsonify({
            'available': False,
            'message': 'All fields are required'
        })
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # First verify faculty exists
        cur.execute("SELECT id FROM faculty WHERE name = %s", (faculty_name,))
        faculty_result = cur.fetchone()
        
        if not faculty_result:
            return jsonify({
                'available': False,
                'message': f'Faculty "{faculty_name}" not found'
            })
        
        faculty_id = faculty_result[0]
        
        # Check if the time slot exactly matches one of the available slots
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM schedules 
                WHERE faculty_id = %s 
                AND day = %s 
                AND start_time = %s::time 
                AND end_time = %s::time
            )
        """, (faculty_id, search_day, search_start, search_end))
        
        is_exact_match = cur.fetchone()[0]
        
        if is_exact_match:
            return jsonify({
                'available': True,
                'message': f'{faculty_name} is available on {search_day} from {search_start} to {search_end}'
            })
        else:
            # Get all available slots for that day
            cur.execute("""
                SELECT start_time::text, end_time::text, room
                FROM schedules
                WHERE faculty_id = %s AND day = %s
                ORDER BY start_time
            """, (faculty_id, search_day))
            
            available_slots = cur.fetchall()
            return jsonify({
                'available': False,
                'message': f'{faculty_name} is not available during the requested time',
                'free_slots': [{
                    'start_time': s[0],
                    'end_time': s[1],
                    'room': s[2]
                } for s in available_slots]
            })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({
            'available': False,
            'message': f'Error: {str(e)}'
        }), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Add this debug route to verify data in database
@app.route("/verify-data")
def verify_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Check faculty table
        cur.execute("SELECT * FROM faculty")
        faculty = cur.fetchall()
        
        # Check schedules table
        cur.execute("""
            SELECT f.name, s.day, s.start_time::text, s.end_time::text, s.room
            FROM schedules s
            JOIN faculty f ON s.faculty_id = f.id
            ORDER BY f.name, s.day, s.start_time
        """)
        schedules = cur.fetchall()
        
        return jsonify({
            'faculty': faculty,
            'schedules': schedules
        })
    finally:
        cur.close()
        conn.close()

@app.route("/get-schedules")
def get_schedules():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT s.id, f.name, s.day, s.start_time, s.end_time, s.room, s.is_temporary
            FROM schedules s
            JOIN faculty f ON s.faculty_id = f.id
            ORDER BY f.name, s.day, s.start_time
        """)
        
        schedules = [{
            'id': row[0],
            'faculty_name': row[1],
            'day': row[2],
            'start_time': row[3].strftime('%H:%M'),
            'end_time': row[4].strftime('%H:%M'),
            'room': row[5],
            'is_temporary': row[6]
        } for row in cur.fetchall()]
        
        return jsonify(schedules)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Add route to save schedule
@app.route("/save-schedule", methods=['POST'])
def save_schedule():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    faculty_id = request.form.get('faculty')
    day = request.form.get('day')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    room = request.form.get('room')
    is_temporary = request.form.get('is_temporary') == 'true'
    valid_until = request.form.get('valid_until')
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO schedules 
            (faculty_id, day, start_time, end_time, room, is_temporary, valid_until)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (faculty_id, day, start_time, end_time, room, is_temporary, valid_until))
        
        schedule_id = cur.fetchone()[0]
        conn.commit()
        
        return jsonify({
            'success': True,
            'id': schedule_id
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

# Add route to delete schedule
@app.route("/delete-schedule/<int:schedule_id>", methods=['POST'])
def delete_schedule(schedule_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # First get the schedule details
        cur.execute("""
            SELECT faculty_id, day, start_time, end_time, room
            FROM schedules 
            WHERE id = %s
        """, (schedule_id,))
        
        schedule = cur.fetchone()
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404

        # Insert into deleted_schedules
        cur.execute("""
            INSERT INTO deleted_schedules 
            (faculty_id, day, start_time, end_time, room)
            VALUES (%s, %s, %s, %s, %s)
        """, schedule)

        # Delete from schedules
        cur.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Schedule deleted successfully'
        })
        
    except Exception as e:
        conn.rollback()
        print(f"Delete error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

# Add route to get deleted schedules
@app.route("/get-deleted-schedules")
def get_deleted_schedules():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute("""
            SELECT ds.id, f.name as faculty_name, ds.day, 
                   ds.start_time::text, ds.end_time::text, 
                   ds.room, ds.deleted_at::text
            FROM deleted_schedules ds
            JOIN faculty f ON ds.faculty_id = f.id
            ORDER BY ds.deleted_at DESC
        """)
        deleted_schedules = cur.fetchall()
        return jsonify([dict(row) for row in deleted_schedules])
    except Exception as e:
        print(f"Error fetching deleted schedules: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Add route to restore deleted schedule
@app.route("/restore-schedule/<int:deleted_id>", methods=['POST'])
def restore_schedule(deleted_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Get the deleted schedule details
        cur.execute("""
            SELECT faculty_id, day, start_time, end_time, room
            FROM deleted_schedules
            WHERE id = %s
        """, (deleted_id,))
        
        schedule = cur.fetchone()
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
            
        # Restore the schedule
        cur.execute("""
            INSERT INTO schedules (faculty_id, day, start_time, end_time, room)
            VALUES (%s, %s, %s, %s, %s)
        """, schedule)
        
        # Remove from deleted_schedules
        cur.execute("DELETE FROM deleted_schedules WHERE id = %s", (deleted_id,))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@app.route("/bulk-upload", methods=['POST'])
def bulk_upload():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
        
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400
        
    try:
        # Read the CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_data = csv.DictReader(stream)
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row in csv_data:
            try:
                # Get faculty ID or create new faculty
                cur.execute("SELECT id FROM faculty WHERE name = %s", (row['name'],))
                faculty_result = cur.fetchone()
                
                if faculty_result:
                    faculty_id = faculty_result[0]
                else:
                    cur.execute("INSERT INTO faculty (name) VALUES (%s) RETURNING id", (row['name'],))
                    faculty_id = cur.fetchone()[0]
                
                # Insert schedule
                cur.execute("""
                    INSERT INTO schedules (faculty_id, day, start_time, end_time, room)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    faculty_id,
                    row['day'],
                    row['start_time'],
                    row['end_time'],
                    row['room']
                ))
                success_count += 1
            except Exception as row_error:
                error_count += 1
                errors.append(f"Error in row {success_count + error_count}: {str(row_error)}")
                print(f"Error in row: {row}, Error: {str(row_error)}")
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'Upload complete. {success_count} schedules added, {error_count} errors.',
            'errors': errors if errors else None
        })
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Upload error: {str(e)}")
        return jsonify({
            'error': f'Error uploading file: {str(e)}'
        }), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route("/logout")
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))
        
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute("""
            SELECT s.*, f.name as faculty_name 
            FROM schedules s
            JOIN faculty f ON s.faculty_id = f.id
            ORDER BY f.name, s.day, s.start_time
        """)
        schedules = cur.fetchall()
        return render_template('admin/dashboard.html', schedules=schedules)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        cur.close()
        conn.close()

@app.route("/edit-schedule/<int:schedule_id>", methods=['GET', 'POST'])
def edit_schedule(schedule_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
        
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        if request.method == 'POST':
            # Get form data
            faculty_id = request.form.get('faculty_id')
            day = request.form.get('day')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            room = request.form.get('room')
            
            print(f"Updating schedule: {faculty_id}, {day}, {start_time}, {end_time}, {room}")  # Debug print
            
            # Update the schedule
            cur.execute("""
                UPDATE schedules 
                SET faculty_id = %s, 
                    day = %s, 
                    start_time = %s::time, 
                    end_time = %s::time, 
                    room = %s
                WHERE id = %s
            """, (faculty_id, day, start_time, end_time, room, schedule_id))
            
            conn.commit()
            flash('Schedule updated successfully', 'success')
            return redirect(url_for('admin_dashboard'))
            
        # GET request - show edit form
        cur.execute("""
            SELECT s.*, f.name as faculty_name 
            FROM schedules s
            JOIN faculty f ON s.faculty_id = f.id
            WHERE s.id = %s
        """, (schedule_id,))
        schedule = cur.fetchone()
        
        if not schedule:
            flash('Schedule not found', 'error')
            return redirect(url_for('admin_dashboard'))
            
        # Get all faculty for dropdown
        cur.execute("SELECT id, name FROM faculty ORDER BY name")
        faculty_list = cur.fetchall()
        
        return render_template('admin/edit_schedule.html', 
                             schedule=schedule, 
                             faculty_list=faculty_list)
                             
    except Exception as e:
        conn.rollback()
        print(f"Error in edit_schedule: {str(e)}")  # Debug print
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        cur.close()
        conn.close()

@app.route("/get-schedule/<int:schedule_id>")
def get_schedule(schedule_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute("""
            SELECT s.*, f.name as faculty_name 
            FROM schedules s
            JOIN faculty f ON s.faculty_id = f.id
            WHERE s.id = %s
        """, (schedule_id,))
        
        schedule = cur.fetchone()
        
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
            
        return jsonify({
            'id': schedule['id'],
            'faculty_id': schedule['faculty_id'],
            'faculty_name': schedule['faculty_name'],
            'day': schedule['day'],
            'start_time': schedule['start_time'].strftime('%H:%M'),
            'end_time': schedule['end_time'].strftime('%H:%M'),
            'room': schedule['room'],
            'is_temporary': schedule['is_temporary'],
            'valid_until': schedule['valid_until'].strftime('%Y-%m-%d') if schedule['valid_until'] else None
        })
        
    except Exception as e:
        print(f"Error getting schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/update-schedule/<int:schedule_id>", methods=['POST'])
def update_schedule(schedule_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get form data including temporary schedule fields
        faculty_id = request.form.get('faculty')
        day = request.form.get('day')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        room = request.form.get('room')
        is_temporary = request.form.get('is_temporary') == 'true'
        valid_until = request.form.get('valid_until') if is_temporary else None
        
        print(f"Received data: faculty={faculty_id}, day={day}, start={start_time}, end={end_time}, room={room}, temp={is_temporary}, valid_until={valid_until}")
        
        # Validate required fields
        if not all([faculty_id, day, start_time, end_time, room]):
            return jsonify({'error': 'All fields are required'}), 400
            
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Update the schedule with temporary fields
        cur.execute("""
            UPDATE schedules 
            SET faculty_id = %s, 
                day = %s, 
                start_time = %s::time, 
                end_time = %s::time, 
                room = %s,
                is_temporary = %s,
                valid_until = %s::date
            WHERE id = %s
            RETURNING id
        """, (faculty_id, day, start_time, end_time, room, is_temporary, valid_until, schedule_id))
        
        updated = cur.fetchone()
        conn.commit()
        
        if updated:
            return jsonify({
                'success': True,
                'message': 'Schedule updated successfully'
            })
        else:
            return jsonify({'error': 'Schedule not found'}), 404
            
    except Exception as e:
        print(f"Error updating schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    app.run(debug=True)