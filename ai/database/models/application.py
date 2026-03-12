from datetime import datetime
from database.db import db


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True)

    # Cover letter
    cover_letter = db.Column(db.Text, nullable=True)

    # Status
    status = db.Column(db.String(50), default='pending', index=True)
    # pending | viewed | invited | rejected | accepted

    # Employer note
    employer_note = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    viewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    resume = db.relationship('Resume', backref='applications')

    def get_status_display(self):
        statuses = {
            'pending': 'На рассмотрении',
            'viewed': 'Просмотрено',
            'invited': 'Приглашение',
            'rejected': 'Отказ',
            'accepted': 'Принято',
        }
        return statuses.get(self.status, self.status)

    def get_status_color(self):
        colors = {
            'pending': 'warning',
            'viewed': 'info',
            'invited': 'success',
            'rejected': 'danger',
            'accepted': 'success',
        }
        return colors.get(self.status, 'secondary')

    def to_dict(self, include_job=True, include_user=True):
        data = {
            'id': self.id,
            'job_id': self.job_id,
            'user_id': self.user_id,
            'resume_id': self.resume_id,
            'cover_letter': self.cover_letter,
            'status': self.status,
            'status_display': self.get_status_display(),
            'status_color': self.get_status_color(),
            'employer_note': self.employer_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
        }
        if include_job and self.job:
            data['job'] = self.job.to_dict()
        if include_user and self.user:
            data['user'] = self.user.to_dict()
        if self.resume:
            data['resume'] = self.resume.to_dict()
        return data

    def __repr__(self):
        return f'<Application job={self.job_id} user={self.user_id}>'