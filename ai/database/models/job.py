from datetime import datetime
from database.db import db


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    responsibilities = db.Column(db.Text, nullable=True)
    conditions = db.Column(db.Text, nullable=True)

    # Salary
    salary_from = db.Column(db.Integer, nullable=True)
    salary_to = db.Column(db.Integer, nullable=True)
    salary_currency = db.Column(db.String(10), default='TMT')
    salary_negotiable = db.Column(db.Boolean, default=False)

    # Location
    city = db.Column(db.String(100), nullable=False, index=True)
    address = db.Column(db.String(255), nullable=True)
    remote = db.Column(db.Boolean, default=False)

    # Job details
    employment_type = db.Column(db.String(50), nullable=False, default='full_time')
    # full_time | part_time | contract | internship | remote
    schedule = db.Column(db.String(50), nullable=True)
    # flexible | shift | full_day | remote
    experience = db.Column(db.String(50), nullable=True)
    # no_experience | 1_3 | 3_6 | 6_plus
    education = db.Column(db.String(50), nullable=True)
    # any | secondary | higher | bachelor | master

    # Skills
    skills = db.Column(db.Text, nullable=True)  # JSON string

    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_hot = db.Column(db.Boolean, default=False)
    views_count = db.Column(db.Integer, default=0)
    applications_count = db.Column(db.Integer, default=0)

    # Relations
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    applications = db.relationship('Application', backref='job', lazy='dynamic', cascade='all, delete-orphan')

    def get_salary_display(self):
        if self.salary_negotiable:
            return 'По договорённости'
        if self.salary_from and self.salary_to:
            return f'{self.salary_from:,} – {self.salary_to:,} {self.salary_currency}'
        if self.salary_from:
            return f'от {self.salary_from:,} {self.salary_currency}'
        if self.salary_to:
            return f'до {self.salary_to:,} {self.salary_currency}'
        return 'По договорённости'

    def get_employment_display(self):
        types = {
            'full_time': 'Полная занятость',
            'part_time': 'Частичная занятость',
            'contract': 'Контракт',
            'internship': 'Стажировка',
            'remote': 'Удалённая работа',
        }
        return types.get(self.employment_type, self.employment_type)

    def get_experience_display(self):
        exp = {
            'no_experience': 'Без опыта',
            '1_3': 'От 1 до 3 лет',
            '3_6': 'От 3 до 6 лет',
            '6_plus': 'Более 6 лет',
        }
        return exp.get(self.experience, 'Не указан')

    def to_dict(self, full=False):
        data = {
            'id': self.id,
            'title': self.title,
            'salary': self.get_salary_display(),
            'salary_from': self.salary_from,
            'salary_to': self.salary_to,
            'salary_currency': self.salary_currency,
            'salary_negotiable': self.salary_negotiable,
            'city': self.city,
            'remote': self.remote,
            'employment_type': self.employment_type,
            'employment_display': self.get_employment_display(),
            'experience': self.experience,
            'experience_display': self.get_experience_display(),
            'is_hot': self.is_hot,
            'is_active': self.is_active,
            'views_count': self.views_count,
            'applications_count': self.applications_count,
            'company_id': self.company_id,
            'company': self.company.to_dict() if self.company else None,
            'category_id': self.category_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if full:
            data.update({
                'description': self.description,
                'requirements': self.requirements,
                'responsibilities': self.responsibilities,
                'conditions': self.conditions,
                'address': self.address,
                'schedule': self.schedule,
                'education': self.education,
                'skills': self.skills,
            })
        return data

    def __repr__(self):
        return f'<Job {self.title}>'