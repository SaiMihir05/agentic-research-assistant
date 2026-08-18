import os
import subprocess
from datetime import datetime, timedelta
import random

def run_command(command, env=None):
    subprocess.run(command, shell=True, check=True, env=env)

DUMMY_FILE = 'heatmap.txt'
DAYS_BACK = 365

# Start from 365 days ago
start_date = datetime.now() - timedelta(days=DAYS_BACK)

with open(DUMMY_FILE, 'w') as f:
    f.write('Heatmap dummy file\n')

env = os.environ.copy()
date_str = start_date.isoformat()
env['GIT_AUTHOR_DATE'] = date_str
env['GIT_COMMITTER_DATE'] = date_str

run_command('git add ' + DUMMY_FILE)
run_command('git commit -m "Add heatmap dummy file"', env=env)

for day_offset in range(DAYS_BACK + 1):
    current_date = start_date + timedelta(days=day_offset)
    
    # 2 to 5 commits per day for a dark green color
    commits_today = random.randint(2, 5)
    
    for i in range(commits_today):
        commit_date = current_date + timedelta(hours=random.randint(8, 20), minutes=random.randint(0, 59))
        date_str = commit_date.isoformat()
        
        with open(DUMMY_FILE, 'a') as f:
            f.write(f'Commit on {date_str}\n')
            
        env = os.environ.copy()
        env['GIT_AUTHOR_DATE'] = date_str
        env['GIT_COMMITTER_DATE'] = date_str
        
        run_command('git add ' + DUMMY_FILE)
        run_command('git commit -m "Heatmap update"', env=env)

print("Heatmap commits generated successfully!")
