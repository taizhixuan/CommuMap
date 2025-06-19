# CommuMap - Working Software Prototype
## Installation and Run Instructions

### 📋 Project Overview
CommuMap is a Django-based community service mapping platform that helps users discover and manage local community services. The application features user authentication, service management, feedback systems, and administrative tools.

### 🔧 System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Git**: Latest version
- **Storage**: Minimum 500MB free space
- **Memory**: 4GB RAM recommended

### 📦 Installation Instructions

#### Step 1: Extract the Project Files
```bash
# Extract the CommuMap.zip file to your desired location
# Navigate to the extracted CommuMap directory
cd CommuMap
```

#### Step 2: Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# For Git Bash/Linux/macOS:
source .venv/bin/activate

# For Windows Command Prompt:
.venv\Scripts\activate
```
**Note**: Ensure you see `(.venv)` at the beginning of your command prompt, indicating the virtual environment is active.

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Create Required Directories
```bash
mkdir logs
```

#### Step 5: Database Setup
```bash
# Apply database migrations
python manage.py migrate
```
**Note**: The SQLite database (`db.sqlite3`) is included with sample data for immediate testing.

### 🚀 Running the Application

#### Start the Development Server
```bash
python manage.py runserver
```

#### Access the Application
- **Main Application**: http://127.0.0.1:8000/

### 👤 Test Account Details

The database includes pre-populated test accounts for immediate evaluation. Use these credentials to test different user roles:

#### 🔐 Login Credentials

**System Administrator**
- **Email**: admin@commumap.com
- **Password**: admin123
- **Access**: Full system control, admin panel access

**Regular User**
- **Email**: usertesting@gmail.com
- **Password**: user@123
- **Access**: Service discovery, feedback submission, profile management

**Service Manager**
- **Email**: smtest@gmail.com
- **Password**: manager@123
- **Access**: Service creation/management, analytics, user feedback monitoring

**Community Moderator**
- **Email**: cmtest@gmail.com
- **Password**: moderator@123
- **Access**: Content moderation, comment management, user reports

### 🔍 Testing Workflow

1. **Access the Homepage**: Navigate to http://127.0.0.1:8000/
2. **Test User Registration**: Create a new account to test signup process
3. **Login with Test Accounts**: Use provided credentials to test different user roles
4. **Service Discovery**: Browse and search for services as a regular user
5. **Admin Features**: Log into admin panel with admin credentials
6. **Role-specific Features**: Test manager and moderator dashboards
7. **Responsive Design**: Test on different screen sizes

