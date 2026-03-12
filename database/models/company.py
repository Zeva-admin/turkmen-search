from datetime import datetime
from database.db import db


class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    short_description = db.Column(db.String(300), nullable=True)

    # Details
    industry = db.Column(db.String(100), nullable=True)
    company_type = db.Column(db.String(50), nullable=True)
    # government | private | foreign | startup
    employees_count = db.Column(db.String(50), nullable=True)
    # 1-10 | 11-50 | 51-200 | 201-500 | 500+
    founded_year = db.Column(db.Integer, nullable=True)
    website = db.Column(db.String(255), nullable=True)

    # Location
    city = db.Column(db.String(100), nullable=True, index=True)
    address = db.Column(db.String(255), nullable=True)

    # Media
    logo = db.Column(db.String(255), nullable=True)
    cover = db.Column(db.String(255), nullable=True)

    # Contact
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    reviews_count = db.Column(db.Integer, default=0)

    # Owner
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs = db.relationship('Job', backref='company', lazy='dynamic', cascade='all, delete-orphan')

    def get_active_jobs_count(self):
        return self.jobs.filter_by(is_active=True).count()

    def get_employees_display(self):
        counts = {
            '1-10': '1–10 сотрудников',
            '11-50': '11–50 сотрудников',
            '51-200': '51–200 сотрудников',
            '201-500': '201–500 сотрудников',
            '500+': 'Более 500 сотрудников',
        }
        return counts.get(self.employees_count, self.employees_count or 'Не указано')

    def get_type_display(self):
        types = {
            'government': 'Государственная',
            'private': 'Частная',
            'foreign': 'Иностранная',
            'startup': 'Стартап',
        }
        return types.get(self.company_type, self.company_type or 'Не указано')

    def to_dict(self, full=False):
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'short_description': self.short_description,
            'industry': self.industry,
            'city': self.city,
            'logo': self.logo,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'active_jobs': self.get_active_jobs_count(),
            'employees_count': self.employees_count,
            'employees_display': self.get_employees_display(),
            'company_type': self.company_type,
            'type_display': self.get_type_display(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if full:
            data.update({
                'description': self.description,
                'website': self.website,
                'address': self.address,
                'phone': self.phone,
                'email': self.email,
                'cover': self.cover,
                'founded_year': self.founded_year,
            })
        return data

    def __repr__(self):
        return f'<Company {self.name}>'