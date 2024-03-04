# pip3.11 install ...
import configparser
from datetime import datetime, timedelta
import multiprocessing
import time
from colorama import Fore, Style
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

ROOM_LINK = "https://jhu.libcal.com/space/7913"
ROOM_NUMBER = "2006"
# comment out the above and uncomment the below for testing:
# ROOM_LINK = "https://jhu.libcal.com/space/7916"
# ROOM_NUMBER = "3010"
MAX_TIMEOUT = 2

class Bot:
    """
    A class to represent a Sylenium 'Bot' that will attempt to book a study room.

    Attributes:
    bot_number (int): The unique identifier for the bot.
    email (str): The email address the bot will use to sign in.
    password (str): The password the bot will use to sign in.
    start_time (str): The time the bot will start searching at.
    target_date (str): The date the bot is attempting to book slots on.
    """

    def __init__(self, bot_number, email, password, start_time, target_date):
        self.bot_number = bot_number
        self.email = email
        self.password = password
        self.start_time = start_time
        self.target_date = target_date

    def __str__(self):
        
        return f"Bot number: {self.bot_number}; Email: {self.email}; Start time: {self.start_time}"

# TODO: time selection is brute-forcy; optimize.
def run_tasks(bot_number, email, password, start_time, target_date):
    """
    "Driver" to book a timeslot using a single bot.

    Args:
    bot_number (int): The unique identifier for the bot.
    email (str): The email address the bot will use to sign in.
    password (str): The password the bot will use to sign in.
    start_time (str): The time the bot will start searching at.
    target_date (str): The date the bot is attempting to book slots on.
    """
    bot = Bot(bot_number, email, password, start_time, target_date)
    options = Options()
    options.add_experimental_option("detach", True) # keeps browser open after processes are complete 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                            options=options)
    driver.get(ROOM_LINK)
    driver.maximize_window()
    try:
        if bot_number == 6 or bot_number == 8:
            time.sleep(10) # this is our "cleanup bot" that will select stray times after other bots are done.
        close_popup(bot, driver)
        if next_button(bot, driver):
            if select_start_time(bot, driver):
                email_login(bot, driver)
                password_login(bot, driver)
                click_continue_button(bot, driver)
                click_submit_booking_button(bot, driver)
    finally:
        print(f"Task complete for Bot {bot.bot_number}.")

def calc_target_date():
    """
    Calculate and format tomorrow's date.

    Returns:
    str: Tomorrow's formatted date.
    """
    current_date = datetime.now()
    next_day = current_date + timedelta(days=1)
    formatted_date = next_day.strftime("%A, %B %#d, %Y")
    return formatted_date

def close_popup(bot, driver):
    """
    Close the survey popup if it appears.

    Args:
    bot (Bot): The Bot to close the popup for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.
    """
    try:
        # if survery popup, close it
        # MAX_TIMEOUT doubled because this is our first element interaction after page load
        close_button = WebDriverWait(driver, 2 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "eupopup-closebutton"))
        )
        close_button.click()
    except TimeoutException:
        print(f"Error: timed out trying to close survey for Bot {bot.bot_number}")

def next_button(bot, driver):
    """
    Click the 'next' button to move to the next day.

    Args:
    bot (Bot): The Bot to click the 'next' button for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.

    Returns:
    bool: True if the button was clicked, False if it timed out.
    """
    try:
        next_button = WebDriverWait(driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "fc-next-button"))
        )
        next_button.click()
        return True
    except TimeoutException:
        print(f"Error: timed out trying to click 'next button' for Bot {bot.bot_number}")
        return False

def select_start_time(bot, driver):
    """
    Select a start time for the bot.

    Args:
    bot (Bot): The Bot to select a start time for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.

    Returns:
    bool: True if the start time was selected, False if it timed out.
    """
    time_obj = datetime.strptime(bot.start_time, "%I:%M%p")
    latest_time = time_obj.replace(hour=23, minute=30,
                                   second=0, microsecond=0)  # currently set to 11:30 pm
    timeout = MAX_TIMEOUT
    while time_obj <= latest_time:
        formatted_time_str = time_obj.strftime("%#I:%M%p").lower()
        try:
            anchor_tag = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    f"a.fc-timeline-event[title='{formatted_time_str} {bot.target_date} - BLC {ROOM_NUMBER} - Available']"))
                )
            anchor_tag.click()
            print(f"Bot {bot.bot_number} found start time of {time_obj}")
            return select_latest_end_time(bot, driver)
        except TimeoutException:
            print(f"Error: timed out trying to click time slot box for Bot {bot.bot_number}, Time {time_obj}")
            if time_obj == latest_time:
                print(f"Bot {bot.bot_number} has reached the end of the day; resetting search at start_time 7:30am.")
                time_obj = time_obj.replace(hour=10, minute=0) # reset time to 10:00 am; start scanning again.
            else:
                time_obj = time_obj + timedelta(minutes=30) # add 30 min to time
            timeout = 0.001 # timeout should be minimal, since elements should already be on page


def select_latest_end_time(bot, driver):
    """
    Select the latest end time from the dropdown.

    Args:
    bot (Bot): The Bot to select the latest end time for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.

    Returns:
    bool: True if the end time was selected, False if it timed out.
    """
    try:
        end_times_dropdown = WebDriverWait(driver, MAX_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH,
                                        '//select[starts-with(@id, "bookingend_")]'))  # dropdown id changes sometimes
            )
        select = Select(end_times_dropdown)

        # the following is straight from ChatGPT lmao
        # Get all the options from the dropdown
        options = select.options

        latest_time_option = None
        latest_time = datetime.min

        # Iterate through the options to find the one with the latest time value
        for option in options:
            option_text = option.text
            option_time = datetime.strptime(option_text, "%I:%M%p %A, %B %d, %Y") # format time
            if option_time > latest_time:
                latest_time = option_time
                latest_time_option = option

        # Select the option with the latest time value
        if latest_time_option is not None:
            latest_time_option.click()

        return submit_time_block(bot, driver) # submit!

    except TimeoutException:
        print(f"Error: timed out trying to select latest dropdown option for Bot {bot.bot_number}, Start time {bot.start_time}")
        print(f"Bot {bot.bot_number} will try again.")
        return select_start_time(bot, driver) # try again

def submit_time_block(bot, driver):
    """
    Submit the selected time block.

    Args:
    bot (Bot): The Bot to submit the time block for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.

    Returns:
    bool: True if the time block was submitted, False if it timed out.
    """
    try:
        submit_times = WebDriverWait(driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "submit_times"))
        )
        submit_times.click()
        return True
    except TimeoutException:
        print(f"Error: timed out trying to submit time block button for Bot {bot.bot_number}")
        return False

def email_login(bot, driver):
    """
    Enter the bot's email into the email field and call submit_sign_in for email.

    Args:
    bot (Bot): The Bot to enter the email for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.

    Returns:
    bool: True if the email was entered, False if it timed out.
    """
    try:
        print("Trying to send email:", bot.email)
        email_field = WebDriverWait(driver, 10 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.NAME, "loginfmt"))
        )
        email_field.send_keys(bot.email)
        submit_sign_in(bot, driver, "email")
    except TimeoutException:
        print(f"Error: timed out trying to enter email field for Bot {bot.bot_number}")

def password_login(bot, driver):
    """
    Enter the bot's password into the password field and call submit_sign_in for password.

    Args:
    bot (Bot): The Bot to enter the password for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.
    """
    try:
        pswd_field = WebDriverWait(driver, 10 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.NAME, "passwd"))
        )
        pswd_field.send_keys(bot.password)
        submit_sign_in(bot, driver, "password")
    except TimeoutException:
        print(f"Error: timed out trying to enter password field for Bot {bot.bot_number}")

def submit_sign_in(bot, driver, sign_in_type):
    """
    Submit the bot's email or password.

    Args:
    bot (Bot): The Bot to submit the email or password for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.
    sign_in_type (str): The type of sign in to submit (email or password).
    """
    try:
        submit_button = WebDriverWait(driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        submit_button.click()
    except TimeoutException:
        print(f"Error: timed out trying to click {sign_in_type} sign in button for Bot {bot.bot_number}")

def click_continue_button(bot, driver):
    """
    Click the 'continue' button on the page following the email and password submission.

    Args:
    bot (Bot): The Bot to click the 'continue' button for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.
    """
    try:
        continue_button = WebDriverWait(driver, 5 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.NAME, "continue"))
        )
        continue_button.click()
    except TimeoutException:
        print(f"Error: timed out trying to click 'continue' button for Bot {bot.bot_number}")

def click_submit_booking_button(bot, driver):
    """
    Click the 'submit booking' button to finalize the booking.

    Args:
    bot (Bot): The Bot to click the 'submit booking' button for.
    driver (WebDriver): The WebDriver instace used to interact with the webpage.
    """
    try:
        submit_button = WebDriverWait(driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "btn-form-submit"))
        )
        submit_button.click()
        print(Fore.GREEN + f"SUCCESS: Time block booked for Bot {bot.bot_number}" + Style.RESET_ALL)
    except TimeoutException:
        print(f"Error: timed out trying to click 'submit booking' button for Bot {bot.bot_number}")

if __name__ == '__main__':
    # Parse the config.ini file
    config = configparser.ConfigParser()
    config.read('config.ini')
    target_date = calc_target_date()
    # list of processes for mulitprocessing
    processes = []

    # Loop through the sections
    for i, chunk in enumerate(config.sections()):
        email = config[chunk]['email']
        password = config[chunk]['password']
        start_time = config[chunk]['start_time']

        process = multiprocessing.Process(target=run_tasks,
                                          args=(i, email, password, start_time, target_date))
        processes.append(process)
        process.start()

    # wait for all processes to finish
    for process in processes:
        process.join()
