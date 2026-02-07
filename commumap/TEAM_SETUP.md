# CommuMap - Team Setup Guide

## 🚀 Quick Start for Team Members

### Prerequisites
- Python 3.8+ installed
- Git installed

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <your-github-repo-url>
   cd CommuMap
   ```

2. **Create and activate virtual environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate it
   source .venv/bin/activate

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create logs directory**
   ```bash
   mkdir logs
   ```

5. **Database is ready!**
   ```bash
   # Apply any pending migrations
   python manage.py migrate
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Main app: http://127.0.0.1:8000/

### 🔑 Admin Access

If you need admin access, ask the project owner to create an admin account for you, or use the existing admin creation script:

```bash
python create_admin.py
```

### 🛠️ Development Notes

- The database (`db.sqlite3`) is included in this repository for team collaboration
- All existing user accounts and data are preserved
- You can start developing immediately with real data
- **Note:** `psutil` package was removed from requirements due to Windows compilation issues
  - Only affects 2 admin monitoring widgets (disk/memory usage)
  - 99% of functionality remains intact

### 🆘 Troubleshooting

#### **Virtual Environment Issues**
- **Git Bash:** Use `source .venv/bin/activate`
- **Command Prompt:** Use `.venv\Scripts\activate`
- Make sure you see `(.venv)` at the start of your prompt

#### **Installation Issues**
1. Make sure your virtual environment is activated
2. Verify Python version: `python --version` (should be 3.8+)
3. Check if all dependencies installed: `pip list`
4. Try running migrations again: `python manage.py migrate`

#### **Common Fixes**
- **Missing logs directory:** Run `mkdir logs`
- **Static files warning:** Run `mkdir static` (optional)
- **Database errors:** Make sure `db.sqlite3` exists in the project root

#### **If you encounter package compilation errors:**
- Try using Windows Command Prompt instead of Git Bash
- Ensure you have the latest pip: `python -m pip install --upgrade pip`

Happy coding! 🎉

