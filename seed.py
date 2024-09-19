from app import app
from models import db, User, Assignment, Bid
from datetime import datetime

def seed_data():
    with app.app_context():
        # Drop existing tables and create new ones
        db.drop_all()
        db.create_all()

        # Clear session
        db.session.remove()

        # Sample users with passwords and roles (writer, admin, client)
        users = [
            {'username': 'johndoe', 'email': 'johndoe@example.com', 'password': 'password123', 'role': 'client'},  # Client
            {'username': 'janedoe', 'email': 'janedoe@example.com', 'password': 'securepass', 'role': 'writer'},   # Writer
            {'username': 'scholar', 'email': 'scholar@example.com', 'password': 'scholarpass', 'role': 'admin'}    # Admin (no assignments)
        ]

        # Add users to the session
        for user_data in users:
            user = User(username=user_data['username'], email=user_data['email'], role=user_data['role'])
            user.set_password(user_data['password'])  # Hash and set the password
            db.session.add(user)

        db.session.commit()

        # Sample assignments - Only clients can create assignments
        assignments = [
            Assignment(
                title='Math Homework', description='Algebra exercises', price_tag=20.00, pages=5, 
                reference_style='APA', due_date=datetime(2024, 8, 1), user_id=1  # Created by 'johndoe' (client)
            ),
            Assignment(
                title='History Essay', description='World War II analysis', price_tag=35.00, pages=10, 
                reference_style='MLA', due_date=datetime(2024, 8, 10), user_id=1  # Created by 'johndoe' (client)
            ),
            Assignment(
                title='Science Project', description='Volcano model', price_tag=50.00, pages=15, 
                reference_style='Chicago', due_date=datetime(2024, 8, 5), user_id=1  # Created by 'johndoe' (client)
            ),
        ]

        # Add assignments to the session
        db.session.bulk_save_objects(assignments)
        db.session.commit()

        # Sample bids (only writers can bid)
        bids = [
            Bid(user_id=2, assignment_id=1, amount=18.00),  # JaneDoe (writer) bids on Math Homework
            Bid(user_id=2, assignment_id=2, amount=32.00),  # JaneDoe (writer) bids on History Essay
            Bid(user_id=2, assignment_id=3, amount=45.00),  # JaneDoe (writer) bids on Science Project
        ]

        # Add bids to the session
        db.session.bulk_save_objects(bids)
        db.session.commit()

if __name__ == '__main__':
    seed_data()
    print("Database seeded!")
