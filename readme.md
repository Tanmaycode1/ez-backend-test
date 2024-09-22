## Secure File Sharing API

This API is a secure file-sharing platform built with Flask, JWT for authentication, and SQLite for data persistence. It allows user registration, email verification, file upload by operations (Ops) users, and secure file download for regular users. 

### Features
- **User Registration and Email Verification:** New users must verify their email to access services.
- **User Roles:** Two roles exist: 
  - **Ops users** (operations users) who can upload files.
  - **Regular users** who can download files.
- **File Upload & Download:** Files can be uploaded and downloaded securely. Only specific file types (`.pptx`, `.docx`, `.xlsx`) are allowed for upload.
- **JWT Authentication:** All routes except signup, login, and email verification require a valid JWT token.
- **Secure Download Links:** File download links are temporary and expire after 5 minutes.

### Requirements

- Python 3.x
- Flask
- SQLAlchemy
- JWT
- smtplib (for sending emails)

### Setup

1. Clone the repository.
   
2. Install the dependencies:

```bash
pip install flask flask_sqlalchemy itsdangerous jwt werkzeug
```

3. Set up a Gmail account for sending verification emails. Update the credentials in the `send_verification_email()` function:

```python
server.login('tanmayarora118@gmail.com', 'your_app_password')
```

4. Create the SQLite database and start the server:

```bash
python app.py
```

5. The server will be running at `http://127.0.0.1:5000`.

### Endpoints

#### Signup

**POST** `/signup`

- Registers a new user and sends an email verification link.
- Payload:

```json
{
  "email": "user@example.com",
  "password": "password123",
  "is_ops": false  // Optional, default is false
}
```

#### Email Verification

**GET** `/verify/<token>`

- Verifies the user's email via the token received in the verification email.
  
#### Login

**POST** `/login`

- Logs in a user after verifying their email. Returns a JWT token.
- Payload:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### File Upload (Ops users only)

**POST** `/upload`

- Uploads a file (only `.pptx`, `.docx`, `.xlsx` allowed). Must be an Ops user.
- Use `Authorization: Bearer <token>` header to provide the JWT token.
- Form Data:

```json
{
  "file": "<file_to_upload>"
}
```

#### List Files

**GET** `/files`

- Lists all uploaded files.
- Use `Authorization: Bearer <token>` header to provide the JWT token.

#### Download File (Regular users only)

**GET** `/download/<file_id>`

- Returns a secure download link for the file.
- Use `Authorization: Bearer <token>` header to provide the JWT token.

#### Secure Download

**GET** `/secure-download/<token>`

- Provides access to the file for download. The token expires after 5 minutes.
