from datetime import datetime
from database.db import db


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Basic Info
    title = db.Column(db.String(200), nullable=False)
    desired_position = db.Column(db.String(200), nullable=True)
    desired_salary = db.Column(db.Integer, nullable=True)
    salary_currency = db.Column(db.String(10), default='TMT')

    # Personal
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)

    # Summary
    about = db.Column(db.Text, nullable=True)

    # Skills (JSON string)
    skills = db.Column(db.Text, nullable=True)

    # Employment preferences
    employment_type = db.Column(db.String(50), nullable=True)
    schedule = db.Column(db.String(50), nullable=True)
    relocation = db.Column(db.Boolean, default=False)
    business_trip = db.Column(db.Boolean, default=False)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    views_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    experiences = db.relationship(
        'Experience', backref='resume', lazy='dynamic',
        cascade='all, delete-orphan', order_by='Experience.start_date.desc()'
    )
    educations = db.relationship(
        'Education', backref='resume', lazy='dynamic',
        cascade='all, delete-orphan', order_by='Education.end_year.desc()'
    )
    languages = db.relationship(
        'Language', backref='resume', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def get_full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    def get_salary_display(self):
        if self.desired_salary:
            return f'{self.desired_salary:,} {self.salary_currency}'
        return 'По договорённости'

    def to_dict(self, full=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'desired_position': self.desired_position,
            'salary': self.get_salary_display(),
            'desired_salary': self.desired_salary,
            'salary_currency': self.salary_currency,
            'full_name': self.get_full_name(),
            'first_name': self.first_name,
            'last_name': self.last_name,
            'city': self.city,
            'employment_type': self.employment_type,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'views_count': self.views_count,
            'skills': self.skills,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if full:
            data.update({
                'middle_name': self.middle_name,
                'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'gender': self.gender,
                'phone': self.phone,
                'email': self.email,
                'about': self.about,
                'schedule': self.schedule,
                'relocation': self.relocation,
                'business_trip': self.business_trip,
                'experiences': [e.to_dict() for e in self.experiences],
                'educations': [e.to_dict() for e in self.educations],
                'languages': [l.to_dict() for l in self.languages],
                'user': self.user.to_dict() if self.user else None,
            })
        return data

    def __repr__(self):
        return f'<Resume {self.title}>'


class Experience(db.Model):
    __tablename__ = 'experiences'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'company_name': self.company_name,
            'position': self.position,
            'city': self.city,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_current': self.is_current,
            'description': self.description,
        }


class Education(db.Model):
    __tablename__ = 'educations'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    institution = db.Column(db.String(200), nullable=False)
    faculty = db.Column(db.String(200), nullable=True)
    specialty = db.Column(db.String(200), nullable=True)
    degree = db.Column(db.String(100), nullable=True)
    start_year = db.Column(db.Integer, nullable=True)
    end_year = db.Column(db.Integer, nullable=True)
    is_current = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'institution': self.institution,
            'faculty': self.faculty,
            'specialty': self.specialty,
            'degree': self.degree,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'is_current': self.is_current,
        }


class Language(db.Model):
    __tablename__ = 'languages'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    # beginner | elementary | intermediate | upper | fluent | native

    def get_level_display(self):
        levels = {
            'beginner': 'Начинающий',
            'elementary': 'Базовый',
            'intermediate': 'Средний',
            'upper': 'Выше среднего',
            'fluent': 'Свободный',
            'native': 'Родной',
        }
        return levels.get(self.level, self.level)

    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'name': self.name,
            'level': self.level,
            'level_display': self.get_level_display(),
        }