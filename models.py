from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import validates
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
})

db = SQLAlchemy(metadata=metadata)

# Reference styles enumeration
class ReferenceStyle:
    APA = 'APA'
    MLA = 'MLA'
    CHICAGO = 'Chicago'
    HARVARD = 'Harvard'

REFERENCE_STYLES = [ReferenceStyle.APA, ReferenceStyle.MLA, ReferenceStyle.CHICAGO, ReferenceStyle.HARVARD]

class User(db.Model, SerializerMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    _password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # New role field
    assignments = db.relationship('Assignment', backref='user', lazy=True)

    # Exclude the 'password_hash' and 'assignments' fields from serialization
    serialize_rules = ('-password_hash', '-assignments')

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def password_hash(self):
        return self._password_hash

    @password_hash.setter
    def password_hash(self, password):
        self._password_hash = generate_password_hash(password)

    def set_password(self, password):
        self.password_hash = password

    def check_password(self, password):
        return check_password_hash(self._password_hash, password)

    @validates('username')
    def validate_username(self, key, username):
        if not username:
            raise ValueError("Username cannot be empty")
        if len(username) > 50:
            raise ValueError("Username must be 50 characters or less")
        return username

    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise ValueError("Email cannot be empty")
        if len(email) > 120:
            raise ValueError("Email must be 120 characters or less")
        # Add more complex validation here if needed (e.g., regex for email format)
        return email

    @validates('role')
    def validate_role(self, key, role):
        valid_roles = ['admin', 'writer', 'client']
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of {valid_roles}")
        return role

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role, 
        }

class Assignment(db.Model, SerializerMixin):
    __tablename__ = 'assignment'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_tag = db.Column(db.Float, nullable=False)  # Price tag for the assignment
    pages = db.Column(db.Integer, nullable=False)  # Number of pages
    reference_style = db.Column(db.String(50), nullable=False)  # Reference style
    due_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Exclude the 'user' field from serialization to avoid recursion
    serialize_rules = ('-user',)

    def __repr__(self):
        return f'<Assignment {self.title}>'

    @validates('title')
    def validate_title(self, key, title):
        if not title:
            raise ValueError("Title cannot be empty")
        if len(title) > 100:
            raise ValueError("Title must be 100 characters or less")
        return title

    @validates('price_tag')
    def validate_price(self, key, price_tag):
        if price_tag <= 0:
            raise ValueError("Price tag must be positive")
        return price_tag

    @validates('pages')
    def validate_pages(self, key, pages):
        if pages <= 0:
            raise ValueError("Number of pages must be positive")
        return pages

    @validates('reference_style')
    def validate_reference_style(self, key, reference_style):
        if reference_style not in REFERENCE_STYLES:
            raise ValueError(f"Invalid reference style. Choose from {REFERENCE_STYLES}")
        return reference_style

    def time_left(self):
        """Returns the time remaining until the assignment is due."""
        now = datetime.utcnow()
        if self.due_date > now:
            time_delta = self.due_date - now
            hours, remainder = divmod(time_delta.seconds, 3600)
            minutes = remainder // 60
            return f"{time_delta.days} days, {hours} hours, {minutes} minutes"
        else:
            return "Assignment overdue"

    def to_dict(self):
        """Convert the assignment to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price_tag': self.price_tag,
            'pages': self.pages,
            'reference_style': self.reference_style,
            'due_date': self.due_date.isoformat(),
            'time_left': self.time_left(),
        }

class Bid(db.Model):
    __tablename__ = 'bids'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    # Define relationships
    user = db.relationship('User', backref='bids', lazy=True)  # Each bid is related to a user
    assignment = db.relationship('Assignment', backref='bids', lazy=True)  # Each bid is related to an assignment

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.username, 
            'assignment_id': self.assignment_id,
            'amount': self.amount
        }
