import schedule
import time
import subprocess

def run_daily_task():
    subprocess.Popen(['python', 'main.py'])
    time.sleep(120)
    subprocess.Popen(['python', 'main.py'])
    time.sleep(120)
    subprocess.Popen(['python', 'main.py'])
    print("Task running")

schedule.every().day.at("00:00").do(run_daily_task)
print("Running schedule_task.py")

while True:
    schedule.run_pending()
    time.sleep(1) # check every ... seconds
