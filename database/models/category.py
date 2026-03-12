from database.db import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), nullable=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    jobs_count = db.Column(db.Integer, default=0)

    # Relationships
    jobs = db.relationship('Job', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'slug': self.slug,
            'description': self.description,
            'jobs_count': self.jobs.filter_by(is_active=True).count(),
        }

    def __repr__(self):
        return f'<Category {self.name}>'