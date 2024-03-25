import configparser
import multiprocessing
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from Bot import Bot
from booking_logic import get_start_hour, click_next_button, click_start_time, select_end_time, submit_times, enter_email, enter_password, click_continue_button, click_submit_booking_button, get_formatted_date, format_hour, conn

c = conn.cursor()
bots = {} # email : Bot object
ROOM_LINK = "https://jhu.libcal.com/space/7913"
ROOM_NUMBER = "2006"

def main():
    init_timeslots_table()
    init_bots_table()
    config = configparser.ConfigParser()
    config.read('config2.ini')

    processes = []

    for info in config.sections():
        name = config[info]['name']
        email = config[info]['email']
        password = config[info]['password']
        initial_hour = config[info]['initial_hour']

        bot = Bot(name, email, password, initial_hour)
        bots[email] = bot
        insert_bot(email)

        process = multiprocessing.Process(target=deploy_bot,
                                          args=(bot,))
        
        processes.append(process)
        process.start()
        time.sleep(1) # sleep to minimize collisions

    # wait for all processes to finish
    for process in processes:
        process.join()

    write_confirmations()

def init_timeslots_table():
    c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='Timeslots';""")
    if c.fetchone():
        # if table already exists, clear entries.
        c.execute("""DELETE from Timeslots;""")
    else:
        # time: starting time
        # booked: 0 or 1
        # email: email of person who booked the slot
        c.execute("""CREATE TABLE Timeslots (
                hour real,
                booked integer,
                email text
            )""")
        
    start_hour = 10
    end_hour = 23.5
    num_slots = int((end_hour - start_hour) * 2) # number of 30 minute slots
    for i in range(num_slots):
        hour = start_hour + (i * 0.5)
        with conn:
            c.execute("INSERT INTO Timeslots VALUES (:hour, :booked, :email)",
                      {'hour': hour, 'booked': 0, 'email': ''})

def init_bots_table():
    c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='Bots';""")
    if c.fetchone():
        # if table already exists, clear entries.
        c.execute("""DELETE from Bots;""")
    else:
        # email: email of bot
        # hoursBooked: # of hours booked, ex 3.5 hours
        c.execute("""CREATE TABLE Bots (
                email text,
                hoursBooked real
            )""")

def insert_bot(email):
    with conn:
        c.execute("INSERT INTO Bots VALUES (:email, :hoursBooked)", {'email': email, 'hoursBooked': 0})

def deploy_bot(bot):
    bot.driver = init_driver()
    while bot.hours_booked < 2:
        functions = [click_next_button,
                        click_start_time,
                        select_end_time,
                        submit_times,
                        enter_email,
                        enter_password,
                        click_continue_button,
                        click_submit_booking_button]
        for f in functions:
            if not f(bot):
                break # break as soon as one of the functions returns False

def init_driver():
    options = Options()
    options.add_experimental_option("detach", True) # keeps browser open after processes are complete 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                            options=options)
    driver.get(ROOM_LINK)
    driver.maximize_window()
    return driver

def write_confirmations():
    formatted_date = get_formatted_date()
    with open(f'Booking Confirmations/{formatted_date}.txt', 'w') as f:
        f.write(f'Brody room confirmations for {formatted_date}:\n')
        c.execute("SELECT * FROM Timeslots WHERE booked=1")
        for row in c.fetchall():
            print(row)
            time = format_hour(row[0])
            name = bots[row[2]].name
            f.write(f'{time:5} {name:10}')



if __name__ == "__main__":
    main()

#TODO: investigate collisions