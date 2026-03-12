from datetime import datetime
from database.db import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='jobseeker')
    # jobseeker | employer | admin

    # Profile
    phone = db.Column(db.String(30), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    about = db.Column(db.Text, nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resumes = db.relationship('Resume', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    applications = db.relationship('Application', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    company = db.relationship('Company', backref='owner', uselist=False)

    def set_password(self, password):
        from app import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        from app import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self, include_private=False):
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email if include_private else None,
            'role': self.role,
            'city': self.city,
            'avatar': self.avatar,
            'about': self.about,
            'is_active': self.is_active,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_private:
            data.update({
                'phone': self.phone,
                'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'gender': self.gender,
                'is_verified': self.is_verified,
            })
        return {k: v for k, v in data.items() if v is not None or k in ['avatar', 'about', 'city']}

    def __repr__(self):
        return f'<User {self.email}>'