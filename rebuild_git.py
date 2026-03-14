import os
import shutil
import subprocess
import datetime
from pathlib import Path

# Configuration
PROJECT_DIR = Path(r"C:\Users\viswa\OneDrive\Desktop\on going projects\FSD project")
BACKUP_DIR = Path("C:\\temp\\fsd_backup")
AUTHOR = "Viswajith2005 <viswajith2005@gmail.com>" # Default but will be overridden by git config if exists

# Define stages and the paths they introduce
stages = [
    {
        "message": "Initial project setup: README and requirements",
        "paths": ["README.md", "requirements.txt", ".gitignore"]
    },
    {
        "message": "Setup initial app.py application skeleton",
        "paths": ["app_skeleton"] # Special keyword to write dummy app.py
    },
    {
        "message": "Add database schema and connection settings",
        "paths": ["schema.sql", "database.py"]
    },
    {
        "message": "Add base HTML layout and basic CSS styling",
        "paths": ["templates/base.html", "static/css/style.css"]
    },
    {
        "message": "Create homepage template and structure",
        "paths": ["templates/index.html"]
    },
    {
        "message": "Design login form taking shape",
        "paths": ["templates/login.html"]
    },
    {
        "message": "Complete signup page for new users",
        "paths": ["templates/signup.html"]
    },
    {
        "message": "Create dashboard overview layout",
        "paths": ["templates/dashboard.html"]
    },
    {
        "message": "Design item submission interface",
        "paths": ["templates/item.html"]
    },
    {
        "message": "Add profile and notifications view",
        "paths": ["templates/profile.html", "templates/notifications.html"]
    },
    {
        "message": "Setup backend configuration environments",
        "paths": [".env", "mail_config.py"]
    },
    {
        "message": "Add admin panel and statistical reports",
        "paths": ["templates/admin.html", "templates/report.html"]
    },
    {
        "message": "Integrate comprehensive backend routes with templates",
        "paths": ["app.py", "static/js/"] # Replaces skeleton
    },
    {
        "message": "Final functional polish and deployment ready fixes",
        "paths": ["ALL"] # Special keyword to copy everything missing
    }
]

app_skeleton_code = """from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
"""

def run_git(args, env=None):
    env_vars = os.environ.copy()
    if env:
        env_vars.update(env)
    subprocess.run(["git"] + args, cwd=PROJECT_DIR, env=env_vars, check=True, text=True)

def setup_backup():
    print("Creating backup...")
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    # Ignore .git folder when backing up
    shutil.copytree(PROJECT_DIR, BACKUP_DIR, ignore=shutil.ignore_patterns('.git', 'rebuild_git.py', '__pycache__'))
    print("Backup created.")

def clear_project():
    print("Clearing project directory...")
    for item in PROJECT_DIR.iterdir():
        if item.name == 'rebuild_git.py':
            continue
        if item.is_dir():
            try:
                # Need to use an error handler for read-only git files
                def handle_remove_readonly(func, path, exc):
                    os.chmod(path, 0o777)
                    func(path)
                shutil.rmtree(item, onerror=handle_remove_readonly)
            except Exception as e:
                print(f"Warning: could not delete {item}: {e}")
        else:
            try:
                item.unlink()
            except Exception as e:
                print(f"Warning: could not delete {item}: {e}")
    print("Project directory cleared.")

def get_commit_date(day_offset, is_evening):
    # day_offset: 1 to 7 (where 7 is today, 1 was 6 days ago)
    days_ago = 7 - day_offset
    now = datetime.datetime.now()
    commit_day = now - datetime.timedelta(days=days_ago)
    
    if is_evening:
        # Evening commit between 19:00 and 21:00
        hour = 20
        minute = 15
    else:
        # Afternoon commit between 13:00 and 15:00
        hour = 14
        minute = 30
        
    return commit_day.replace(hour=hour, minute=minute, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S')

def main():
    setup_backup()
    clear_project()
    
    print("Initializing fresh git repository...")
    run_git(["init"])
    run_git(["config", "user.name", "Viswajith2005"])
    run_git(["config", "user.email", "viswajith2005@gmail.com"])
    
    # 14 stages across 7 days
    stage_idx = 0
    for day in range(1, 8):
        for is_evening in [False, True]:
            if stage_idx >= len(stages):
                break
                
            stage = stages[stage_idx]
            commit_date = get_commit_date(day, is_evening)
            print(f"\\n--- Executing Stage {stage_idx + 1} (Day {day} {'Evening' if is_evening else 'Afternoon'}) ---")
            
            # Copy specific paths
            for p in stage['paths']:
                if p == "app_skeleton":
                    # Create skeleton app.py
                    (PROJECT_DIR / "app.py").write_text(app_skeleton_code, encoding="utf-8")
                    continue
                elif p == "ALL":
                    # Copy everything missing from backup
                    for root, dirs, files in os.walk(BACKUP_DIR):
                        rel_path = os.path.relpath(root, BACKUP_DIR)
                        if rel_path == '.':
                            target_dir = PROJECT_DIR
                        else:
                            target_dir = PROJECT_DIR / rel_path
                            target_dir.mkdir(parents=True, exist_ok=True)
                            
                        for f in files:
                            src_file = os.path.join(root, f)
                            dst_file = target_dir / f
                            if not dst_file.exists() or dst_file.name == 'app.py' or dst_file.name == 'lost_found.db':
                                shutil.copy2(src_file, dst_file)
                    continue
                
                # Copy specific path (file or dir)
                src = BACKUP_DIR / p
                dst = PROJECT_DIR / p
                if not src.exists():
                    print(f"Warning: {p} not found in backup.")
                    continue
                    
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            
            # Git add and commit
            run_git(["add", "."])
            env = {
                "GIT_AUTHOR_DATE": commit_date,
                "GIT_COMMITTER_DATE": commit_date
            }
            run_git(["commit", "-m", stage['message']], env=env)
            stage_idx += 1

    print("\\n\\nSuccessfully rewrote git history with 14 commits spanning 7 days!")

if __name__ == "__main__":
    main()
