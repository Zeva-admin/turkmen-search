from datetime import datetime
from database.db import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Content
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False, default='info')
    # info | application | message | invitation | system

    # Link
    link = db.Column(db.String(255), nullable=True)
    link_text = db.Column(db.String(100), nullable=True)

    # Status
    is_read = db.Column(db.Boolean, default=False, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def get_type_icon(self):
        icons = {
            'info': 'bell',
            'application': 'briefcase',
            'message': 'message',
            'invitation': 'check-circle',
            'system': 'settings',
        }
        return icons.get(self.type, 'bell')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'text': self.text,
            'type': self.type,
            'type_icon': self.get_type_icon(),
            'link': self.link,
            'link_text': self.link_text,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }

    @staticmethod
    def create_notification(user_id, title, text, type='info', link=None, link_text=None):
        notification = Notification(
            user_id=user_id,
            title=title,
            text=text,
            type=type,
            link=link,
            link_text=link_text,
        )
        db.session.add(notification)
        return notification

    def __repr__(self):
        return f'<Notification user={self.user_id} type={self.type}>'
    