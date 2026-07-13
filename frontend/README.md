# AI Workspace Frontend

A Streamlit-based frontend for the AI Workspace SaaS backend. This application provides a complete user interface for authentication, organization management, invitations, and file uploads.

## Features

- **Authentication**: User registration and login with JWT token management
- **Organization Management**: Create and manage multiple organizations (tenants)
- **Multi-tenancy**: Switch between organizations with context-aware API calls
- **Invitations**: Create and accept organization invitations
- **File Management**: Upload and view files within organization context
- **User Profile**: View user information and account details

## Prerequisites

- Python 3.8 or higher
- FastAPI backend running on `http://localhost:8000` (or configured via `API_BASE_URL`)
- pip package manager

## Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` to set your backend API URL:
   ```
   API_BASE_URL=http://localhost:8000
   ```

## Running the Application

1. **Ensure the FastAPI backend is running:**
   ```bash
   # From the backend directory
   uvicorn app.main:app --reload
   ```

2. **Start the Streamlit frontend:**
   ```bash
   streamlit run app.py
   ```

3. **Open your browser:**
   Navigate to `http://localhost:8501`

## Project Structure

```
frontend/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── api/                       # API client layer
│   ├── client.py             # Base HTTP client with auth
│   ├── auth.py               # Authentication API
│   ├── organizations.py      # Organizations API
│   ├── invitations.py       # Invitations API
│   └── files.py              # Files API
├── components/               # Reusable components
│   ├── sidebar.py            # Navigation and organization selector
│   └── auth_guard.py         # Authentication guards
├── pages/                    # Page implementations
│   ├── Login.py              # Login page
│   ├── Register.py           # Registration page
│   ├── Dashboard.py          # Dashboard overview
│   ├── Organizations.py      # Organization management
│   ├── Invitations.py        # Invitation management
│   ├── Files.py              # File upload and listing
│   └── Profile.py            # User profile
└── utils/                    # Utility functions
    ├── constants.py          # Application constants
    └── session.py            # Session state management
```

## Usage Guide

### Authentication

1. **Register**: Create a new account on the Register page
2. **Login**: Use your credentials to login
3. **Session**: JWT tokens are stored in Streamlit session state

### Organization Management

1. **Create Organization**: Navigate to Organizations page and create a new workspace
2. **Select Organization**: Use the sidebar dropdown to switch between organizations
3. **Context**: All tenant-scoped operations use the selected organization context

### Invitations

1. **Create Invitation**: Select an organization, enter invitee email, and generate a token
2. **Share Token**: Copy the invitation token and share it with the invitee
3. **Accept Invitation**: Enter the token on the Invitations page to join an organization

### File Management

1. **Select Organization**: Ensure an organization is selected in the sidebar
2. **Upload File**: Use the file uploader on the Files page
3. **View Files**: Browse all files in the current organization

## API Integration

The frontend communicates with the FastAPI backend using the following endpoints:

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Organizations
- `POST /organizations` - Create organization
- `GET /organizations/my` - List user's organizations

### Invitations
- `POST /organizations/{org_id}/invite` - Create invitation
- `POST /invitations/accept` - Accept invitation

### Files
- `POST /files/upload` - Upload file (requires `X-Organization-Id` header)
- `GET /files` - List files (requires `X-Organization-Id` header)

## Authentication Flow

1. User logs in → JWT token stored in session state
2. All API requests include `Authorization: Bearer <token>` header
3. Organization-scoped requests include `X-Organization-Id` header
4. 401 errors redirect to login page

## Error Handling

The frontend handles common API errors:

- **401 Unauthorized**: Redirects to login page
- **403 Forbidden**: Shows permission error message
- **404 Not Found**: Shows resource not found message
- **409 Conflict**: Shows conflict error (e.g., duplicate email)
- **Network Errors**: Shows connection error message

## Development

### Adding New Pages

1. Create a new page file in `frontend/pages/`
2. Implement the `render()` function
3. Add the page constant to `frontend/utils/constants.py`
4. Add navigation entry in `frontend/components/sidebar.py`
5. Add page routing in `frontend/app.py`

### Adding API Endpoints

1. Create a new API client in `frontend/api/`
2. Use the `api_client` base class for HTTP requests
3. Implement error handling with `APIError`
4. Import and use in page components

## Troubleshooting

### Backend Connection Issues

If you see connection errors:
1. Ensure the FastAPI backend is running
2. Check `API_BASE_URL` in `.env` file
3. Verify the backend is accessible at the configured URL

### Authentication Issues

If login fails:
1. Check backend logs for errors
2. Verify user credentials
3. Ensure JWT token generation is working in backend

### Organization Context Issues

If organization-scoped operations fail:
1. Ensure an organization is selected in the sidebar
2. Check that `X-Organization-Id` header is being sent
3. Verify user has membership in the selected organization

## License

This frontend is part of the AI Workspace SaaS application.
