import schedule
import sys
import time
import subprocess

def run_daily_task():
    global task_executed
    subprocess.Popen(['python', 'main.py'])
    print("Task running")
    task_executed = True

schedule.every().day.at("23:59:57").do(run_daily_task)
print("Running schedule_task.py")

animation = ['', '.', '..', '...']
while True:
    for char in animation:
        schedule.run_pending() # check if it's time to run the task. All other code in this loop is for aesthetics.
        if (task_executed):
            break
        sys.stdout.write('\rWaiting' + char)
        sys.stdout.flush()
        time.sleep(0.5)
    sys.stdout.write('\r' + ' ' * 15)  # Add spaces to clear the ellipses
    sys.stdout.flush()
