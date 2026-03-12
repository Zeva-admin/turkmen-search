# Import all models to ensure they are registered with SQLAlchemy
from database.models.user import User
from database.models.job import Job
from database.models.company import Company
from database.models.resume import Resume, Experience, Education, Language
from database.models.application import Application
from database.models.message import Message, Conversation
from database.models.notification import Notification
from database.models.category import Category

__all__ = [
    'User',
    'Job',
    'Company',
    'Resume',
    'Experience',
    'Education',
    'Language',
    'Application',
    'Message',
    'Conversation',
    'Notification',
    'Category',
]