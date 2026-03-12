from datetime import datetime
from database.db import db


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Content
    text = db.Column(db.Text, nullable=False)
    attachment = db.Column(db.String(255), nullable=True)

    # Status
    is_read = db.Column(db.Boolean, default=False, index=True)
    is_deleted_sender = db.Column(db.Boolean, default=False)
    is_deleted_receiver = db.Column(db.Boolean, default=False)

    # Thread (conversation key)
    conversation_id = db.Column(db.String(50), nullable=True, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self, current_user_id=None):
        data = {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'text': self.text,
            'attachment': self.attachment,
            'is_read': self.is_read,
            'conversation_id': self.conversation_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }
        if self.sender:
            data['sender'] = {
                'id': self.sender.id,
                'name': self.sender.name,
                'avatar': self.sender.avatar,
            }
        if current_user_id:
            data['is_mine'] = self.sender_id == current_user_id
        return data

    def __repr__(self):
        return f'<Message from={self.sender_id} to={self.receiver_id}>'


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(50), unique=True, nullable=False)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    last_message = db.Column(db.Text, nullable=True)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    unread_count_user1 = db.Column(db.Integer, default=0)
    unread_count_user2 = db.Column(db.Integer, default=0)

    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])

    def get_other_user(self, current_user_id):
        if self.user1_id == current_user_id:
            return self.user2
        return self.user1

    def get_unread_count(self, current_user_id):
        if self.user1_id == current_user_id:
            return self.unread_count_user1
        return self.unread_count_user2

    def to_dict(self, current_user_id):
        other_user = self.get_other_user(current_user_id)
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'other_user': {
                'id': other_user.id,
                'name': other_user.name,
                'avatar': other_user.avatar,
                'role': other_user.role,
            } if other_user else None,
            'last_message': self.last_message,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'unread_count': self.get_unread_count(current_user_id),
        }