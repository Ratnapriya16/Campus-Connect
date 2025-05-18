from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Faculty(db.Model):
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    schedules = db.relationship('Schedule', backref='faculty', lazy=True)

    def __repr__(self):
        return f'<Faculty {self.name}>'

class Schedule(db.Model):
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(8), nullable=False)
    end_time = db.Column(db.String(8), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    is_temporary = db.Column(db.Boolean, default=False)
    valid_until = db.Column(db.Date, nullable=True)
    is_busy = db.Column(db.Boolean, default=False)
    original_schedule_id = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<Schedule {self.faculty.name} - {self.day} {self.start_time}-{self.end_time}>'

class DeletedSchedule(db.Model):
    __tablename__ = 'deleted_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(8), nullable=False)
    end_time = db.Column(db.String(8), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    deleted_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<DeletedSchedule {self.faculty_id} - {self.day} {self.start_time}-{self.end_time}>'