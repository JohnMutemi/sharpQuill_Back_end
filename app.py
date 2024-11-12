import random
from flask import Flask, request, jsonify, make_response, session, redirect, url_for, render_template
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restful import Api, Resource
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from datetime import timedelta, datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config["JWT_SECRET_KEY"] = "fsbdgfnhgvjnvhmvh" + str(random.randint(1, 1000000000000))
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
app.config["SECRET_KEY"] = "JKSRVHJVFBSRDFV" + str(random.randint(1, 1000000000000))
app.json.compact = False
api = Api(app)

from models import db, User, Assignment, Bid

db.init_app(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

# Role-based decorator
def role_required(roles):
    def wrapper(fn):
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()['user_id']
            user = User.query.get(user_id)
            if user and user.role not in roles:
                return {"message": f"{roles} role required"}, 403
            return fn(*args, **kwargs)
        return decorated_function
    return wrapper

# Error handler
@app.errorhandler(NotFound)
def handle_not_found(e):
    response = make_response(
        jsonify({'error': 'NotFound', 'message': 'The requested resource does not exist'}),
        404
    )
    response.headers['Content-Type'] = 'application/json'
    return response

app.register_error_handler(404, handle_not_found)

# Routes and resources
@app.route('/')
def index():
    return render_template('index.html')

class UserResource(Resource):
    @role_required(['admin'])  # Only admin can view all users
    def get(self, user_id=None):
        if user_id:
            user = User.query.get(user_id)
            if user:
                return user.to_dict(), 200
            return {'error': 'User not found'}, 404
        users = User.query.all()
        return [user.to_dict() for user in users], 200

    @jwt_required()  # Only logged-in users can update their own profile
    def patch(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}, 404
        data = request.get_json()
        for key, value in data.items():
            setattr(user, key, value)
        db.session.commit()
        return user.to_dict(), 200

    @role_required(['admin'])  # Only admin can delete users
    def delete(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}, 404
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted successfully'}, 200

class BiddingResource(Resource):
    @role_required(['writer'])  # Only writers can bid on assignments
    def get(self):
        bids = Bid.query.all()
        return [bid.to_dict() for bid in bids], 200

    @role_required(['writer'])  # Only writers can post bids
    def post(self):
        user_id = get_jwt_identity()['user_id']
        data = request.get_json()
        assignment_id = data.get('assignment_id')
        amount = data.get('amount')

        # Validate the assignment exists and is available
        assignment = Assignment.query.get(assignment_id)
        if not assignment or assignment.status != 'available':
            return {"message": "Assignment not available for bidding."}, 400

        bid = Bid(user_id=user_id, assignment_id=assignment_id, amount=amount)
        db.session.add(bid)
        db.session.commit()

        return bid.to_dict(), 201
class AssignmentResource(Resource):
    @jwt_required()
    @role_required(['client'])  # Only clients can create assignments
    def post(self):
        user_identity = get_jwt_identity()
        user_id = user_identity.get('user_id')

        title = request.form.get('title')
        description = request.form.get('description')
        price_tag = request.form.get('price_tag')
        pages = request.form.get('pages')
        reference_style = request.form.get('reference_style')
        due_date = request.form.get('due_date')

        if not all([title, description, price_tag, pages, reference_style, due_date]):
            return {"message": "All fields are required"}, 400

        try:
            price_tag = float(price_tag)
            pages = int(pages)
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return {"message": "Invalid value for price tag, pages, or due date"}, 400

        new_assignment = Assignment(
            title=title,
            description=description,
            price_tag=price_tag,
            pages=pages,
            reference_style=reference_style,
            due_date=due_date,
            user_id=user_id
        )

        db.session.add(new_assignment)
        db.session.commit()

        return new_assignment.to_dict(), 201
    
    @jwt_required()
    def get(self, assignment_id=None):
        if assignment_id:
            assignment = Assignment.query.get(assignment_id)
            if not assignment:
                return {"message": "Assignment not found"}, 404
            return assignment.to_dict(), 200

        status = request.args.get('status')
        query = Assignment.query
        if status:
            query = query.filter_by(status=status)
        assignments = query.all()
        return jsonify([assignment.to_dict() for assignment in assignments])

    @jwt_required()
    @role_required(['client'])  # Only clients can update assignments
    def put(self, assignment_id):
        user_identity = get_jwt_identity()
        user_id = user_identity.get('user_id')

        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return {"message": "Assignment not found"}, 404

        if assignment.user_id != user_id:
            return {"message": "You are not authorized to update this assignment"}, 403

        title = request.form.get('title', assignment.title)
        description = request.form.get('description', assignment.description)
        price_tag = request.form.get('price_tag', assignment.price_tag)
        pages = request.form.get('pages', assignment.pages)
        reference_style = request.form.get('reference_style', assignment.reference_style)
        due_date = request.form.get('due_date', assignment.due_date)

        try:
            if price_tag:
                price_tag = float(price_tag)
            if pages:
                pages = int(pages)
            if due_date:
                due_date = datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return {"message": "Invalid value for price tag, pages, or due date"}, 400

        assignment.title = title
        assignment.description = description
        assignment.price_tag = price_tag
        assignment.pages = pages
        assignment.reference_style = reference_style
        assignment.due_date = due_date

        db.session.commit()
        return assignment.to_dict(), 200

    @jwt_required()
    @role_required(['client'])  # Only clients can delete assignments
    def delete(self, assignment_id):
        user_identity = get_jwt_identity()
        user_id = user_identity.get('user_id')

        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return {"message": "Assignment not found"}, 404

        if assignment.user_id != user_id:
            return {"message": "You are not authorized to delete this assignment"}, 403

        db.session.delete(assignment)
        db.session.commit()
        return {"message": "Assignment deleted successfully"}, 200

    @jwt_required()
    @role_required(['writer', 'client'])
    @app.route('/assignments/upload/<int:assignment_id>', methods=['POST'])  
    def post_file_upload(self, assignment_id):
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return {"message": "Assignment not found"}, 404

        if assignment.status != 'in_progress':
            return {"message": "Files can only be uploaded for assignments in progress."}, 400

        if 'file' not in request.files:
            return {"message": "No file part"}, 400

        file = request.files['file']
        if file.filename == '':
            return {"message": "No selected file"}, 400
        file_path = f"/path/to/save/{file.filename}"  
        file.save(file_path)

        return {"message": "File uploaded successfully"}, 201
class Login(Resource):
    def post(self):
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            access_token = create_access_token(identity={'user_id': user.id, 'role': user.role})
            return {
                'message': f"Welcome {user.username}",
                'access_token': access_token,
                'username': user.username,
                'email': user.email,
                'user_id': user.id,
                'role': user.role  # Include role in response
            }, 200
        return {"error": "Invalid username or password"}, 401

class Register(Resource):
    def post(self):
        data = request.form
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'writer')  # Default to client role if not provided

        if not username or not password or not email:
            return {'message': 'username, password, and email are required'}, 400

        # Check if the user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return {'message': 'User already exists'}, 400

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return {'message': 'User registered successfully'}, 201

class CheckSession(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()['user_id']
        user = User.query.get(user_id)

        if user:
            return jsonify(user.to_dict()), 200
        return jsonify({"error": "User not found"}), 404

class Logout(Resource):
    @jwt_required()
    def post(self):
        session.pop('user_id', None)
        return jsonify({"message": "Logout successful"})

# Register API endpoints
api.add_resource(UserResource, '/users', '/users/<int:user_id>')
api.add_resource(AssignmentResource, '/assignments', '/assignments/<int:assignment_id>', '/assignments/upload/<int:assignment_id>')
api.add_resource(BiddingResource, '/bids')
api.add_resource(Login, '/login')
api.add_resource(Register, '/register')
api.add_resource(CheckSession, '/session')
api.add_resource(Logout, '/logout')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
