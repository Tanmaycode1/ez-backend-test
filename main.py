from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import jwt
import datetime
import os
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] =  'fallback_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///file_sharing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


db = SQLAlchemy(app)


# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_ops = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)


# File model
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Create tables
with app.app_context():
    db.create_all()


# Utility functions
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)

    return decorated


def send_verification_email(email, token):
    msg = MIMEMultipart()
    msg['From'] = 'tanmayarora118@gmail.com'
    msg['To'] = email
    msg['Subject'] = 'Verify your email'

    body = f'Click the following link to verify your email: http://127.0.0.1:5000/verify/{token}'
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('tanmayarora118@gmail.com', 'dojw hrrg ecol jank')
    text = msg.as_string()
    server.sendmail('your_email@example.com', email, text)
    server.quit()


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    is_ops = data.get('is_ops', False)  # Default to False unless specified

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password=hashed_password, is_ops=is_ops)
    db.session.add(new_user)
    db.session.commit()

    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = serializer.dumps(email, salt='email-verify')

    send_verification_email(email, token)

    encrypted_url = f'/verify/{token}'
    return jsonify(
        {'message': 'User created. Please check your email for verification.', 'encrypted_url': encrypted_url}), 201

@app.route('/verify/<token>', methods=['GET'])
def verify_email(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verify', max_age=3600)
    except SignatureExpired:
        return jsonify({'message': 'The verification link has expired'}), 400
    except:
        return jsonify({'message': 'The verification link is invalid'}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        user.is_verified = True
        db.session.commit()
        return jsonify({'message': 'Email verified successfully'}), 200
    else:
        return jsonify({'message': 'User not found'}), 404


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        if not user.is_verified and not user.is_ops:
            return jsonify({'message': 'Please verify your email before logging in'}), 401

        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'])

        return jsonify({'token': token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    if not current_user.is_ops:
        return jsonify({'message': 'Only operations users can upload files'}), 403

    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected for uploading'}), 400

    if file and file.filename.split('.')[-1].lower() in ['pptx', 'docx', 'xlsx']:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_file = File(filename=filename, uploaded_by=current_user.id)
        db.session.add(new_file)
        db.session.commit()

        return jsonify({'message': 'File successfully uploaded'}), 201
    else:
        return jsonify({'message': 'Allowed file types are pptx, docx, xlsx'}), 400


@app.route('/files', methods=['GET'])
@token_required
def list_files(current_user):
    files = File.query.all()
    return jsonify({'files': [{'id': file.id, 'filename': file.filename} for file in files]}), 200


@app.route('/download/<int:file_id>', methods=['GET'])
@token_required
def download_file(current_user, file_id):
    if current_user.is_ops:
        return jsonify({'message': 'Operation users are not allowed to download files'}), 403

    file = File.query.get(file_id)
    if not file:
        return jsonify({'message': 'File not found'}), 404

    # Generate a secure download link
    token = jwt.encode({
        'file_id': file.id,
        'user_id': current_user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
    }, app.config['SECRET_KEY'])

    encrypted_url = f"/secure-download/{token}"
    return jsonify({'download_link': encrypted_url, 'message': 'success'}), 200


@app.route('/secure-download/<token>', methods=['GET'])
def secure_download(token):
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        file = File.query.get(data['file_id'])
        user = User.query.get(data['user_id'])

        if not file or not user or user.is_ops:
            return jsonify({'message': 'Invalid download link or unauthorized user'}), 400

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        return send_file(file_path, as_attachment=True)
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Download link has expired'}), 400
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid download link'}), 400


if __name__ == '__main__':
    app.run(debug=True)

