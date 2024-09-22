import unittest
import json
import os
from main import app, db, User, File
from werkzeug.security import generate_password_hash

class FileSharingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        with app.app_context():
            db.create_all()

            # Create a test user and ops user
            self.regular_user = User(
                email='regularuser@example.com',
                password=generate_password_hash('regularpassword'),
                is_verified=True,
                is_ops=False
            )
            self.ops_user = User(
                email='opsuser@example.com',
                password=generate_password_hash('opspassword'),
                is_verified=True,
                is_ops=True
            )
            db.session.add(self.regular_user)
            db.session.add(self.ops_user)
            db.session.commit()

            # Add a test file for download tests
            test_file = File(
                filename='test_file.pptx',
                uploaded_by=self.regular_user.id
            )
            db.session.add(test_file)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_signup(self):
        response = self.app.post('/signup', json={
            'email': 'newuser@example.com',
            'password': 'newpassword',
            'is_ops': False
        })
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertIn('User created', data['message'])

    def test_login_verified_user(self):
        response = self.app.post('/login', json={
            'email': 'regularuser@example.com',
            'password': 'regularpassword'
        })
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', data)

    def test_upload_file(self):
        # Login as Ops user
        login_response = self.app.post('/login', json={
            'email': 'opsuser@example.com',
            'password': 'opspassword'
        })
        token = json.loads(login_response.data)['token']

        # Test file upload
        data = {
            'file': (open('test_file.pptx', 'rb'), 'test_file.pptx')
        }
        response = self.app.post('/upload', headers={
            'Authorization': f'Bearer {token}'
        }, content_type='multipart/form-data', data=data)

        self.assertEqual(response.status_code, 201)
        self.assertIn('File successfully uploaded', json.loads(response.data)['message'])

    def test_file_download(self):
        # Login as regular user
        login_response = self.app.post('/login', json={
            'email': 'regularuser@example.com',
            'password': 'regularpassword'
        })
        token = json.loads(login_response.data)['token']

        # Attempt to download the test file
        response = self.app.get('/download/1', headers={
            'Authorization': f'Bearer {token}'
        })
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('download_link', data)

    def test_ops_cannot_download_files(self):
        # Login as Ops user
        login_response = self.app.post('/login', json={
            'email': 'opsuser@example.com',
            'password': 'opspassword'
        })
        token = json.loads(login_response.data)['token']

        # Ops user tries to download the test file
        response = self.app.get('/download/1', headers={
            'Authorization': f'Bearer {token}'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('Operation users are not allowed to download files', json.loads(response.data)['message'])

if __name__ == '__main__':
    unittest.main()
