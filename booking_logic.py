import sqlite3
from datetime import datetime, timedelta
from colorama import Fore, Style
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

# cursor contained in this module to eliminate circular import
conn = sqlite3.connect('master.db')
c = conn.cursor()
ROOM_LINK = "https://jhu.libcal.com/space/7913"
ROOM_NUMBER = "2006"
MAX_TIMEOUT = 2

def get_start_hour(bot):
    """
    Returns first available hour for bot to book.
    Will start searching at bot.initial_hour, then get first 
    available unbooked hour if not available.
    Will assign 'booked' to 1 for hour that was found.
    Returns None if there are no available hours to book.
    """
    c.execute("SELECT * FROM Timeslots WHERE hour=:hour",
              {'hour': bot.initial_hour})
    res = c.fetchone()
    if res is None:
        return None
    else:
        if res[1] == 1:
            # if time is booked:
            print("TIME IS BOOKED")
            c.execute("SELECT * FROM Timeslots WHERE booked=0")
            res = c.fetchone() # get first available timeslot
            if res is None:
                return None
        update_booked(res[0], 1)
        return res[0] # return "hour" for timeslot
 
def update_booked(hour, set_booked_to):        
    with conn:
        c.execute("""UPDATE Timeslots SET booked=:booked
        WHERE hour=:hour""",
        {'booked': set_booked_to, 'hour': hour})

def click_next_button(bot):
    try:
        next_button = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "fc-next-button"))
        )
        next_button.click()
        return True
    except TimeoutException:
        print(f"TimeoutException trying to click 'next button' for {bot}")
        return False
    
def click_start_time(bot):
    formatted_date_str = get_formatted_date()
    try:
        bot.start_hour = get_start_hour(bot)
        # 27 is total # of 30 min slots.
        for i in range(27):
            # get the anchor tag, whether it is available or not.
            # '^' denotes 'starts with'
            print(f"Trying to select start_hour for {bot.start_hour}")
            formatted_time_str = format_hour(bot.start_hour)
            anchor_tag = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    f"a.fc-timeline-event[title^='{formatted_time_str} {formatted_date_str}"))
                )
            title = anchor_tag.get_attribute('title')
            if "Unavailable" in title:
                update_booked(bot.start_hour, 1)
                new_start_hour = get_start_hour(bot)
                print("NSH:", new_start_hour)
                if new_start_hour is not None:
                    bot.start_hour = new_start_hour
                else:
                    return False
            else:
                # timeslot is available!
                update_booked(bot.start_hour, 1)
                anchor_tag.click()
                return True
    except TimeoutException:
        print(f"TimeoutException trying to click {formatted_time_str} time slot box for {bot}")
        return False
    
def format_hour(hour):
    """
    Return an hour in a formatted string WRT the website's formatting.
    
    Args:
    hour (float): Hour to format, ex: 14.5
    """
    hours = int(hour)
    minutes = int((hour - hours) * 60)

    time_obj = datetime.strptime(f'{hours}:{minutes}', '%H:%M')
    time_string = time_obj.strftime("%#I:%M%p").lower()

    return time_string

def get_formatted_date():
    current_date = datetime.now()
    next_day = current_date + timedelta(days=1)
    formatted_date = next_day.strftime("%A, %B %#d, %Y")
    return formatted_date

def select_end_time(bot):
    try:
        dropdown = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH,
                '//select[starts-with(@id, "bookingend_")]'))  # dropdown id changes sometimes
            )
        select = Select(dropdown)

        latest_possible_hour_obj = get_latest_possible_hour(bot)

        # Get all the options from the dropdown
        options = select.options

        latest_time_option = None
        latest_time = datetime.min

        # Iterate through all options. Find latest option that bot can still book,
        # given the amount of slots the bot has already booked.
        for option in options:
            option_text = option.text
            option_time = datetime.strptime(option_text, "%I:%M%p %A, %B %d, %Y") # format time
            if option_time > latest_time and option_time <= latest_possible_hour_obj:
                latest_time = option_time
                latest_time_option = option

        # Select the option with the latest possible time value
        if latest_time_option is not None:
            bot.end_hour = datetime_to_hour(latest_time)
            update_time_range_booked(bot, 1, bot.email)
            latest_time_option.click()
            return True
        else:
            return False # return False if nothing was selected

    except TimeoutException:
        print(f"TimeoutException trying to select end time for Bot {bot}")
        return False

def get_latest_possible_hour(bot):
    """
    Calculate the latest possible hour a bot can select for its end time,
    based on its start time and amount of hours already booked.

    Returns:
    datetime object representing the latest possible hour the bot can book.
    """
    hour = bot.start_hour + (2 - bot.hours_booked)
    hours = int(hour)
    minutes = int((hour - hours) * 60)

    now = datetime.now()
    target_day = now + timedelta(days=1) # set day to tomorrow
    time_obj = target_day.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    return time_obj

def datetime_to_hour(datetime_obj):
    return datetime_obj.hour + (datetime_obj.minute / 60)

def update_time_range_booked(bot, set_booked_to, set_email_to):
    num_slots = int((bot.end_hour - bot.start_hour) * 2) # num 30 minute slots bot is attempting to book
    for delta in range(num_slots):
        hour = bot.start_hour + (delta * 0.5)
        with conn:
            c.execute("""UPDATE Timeslots SET booked=:booked, email=:email
            WHERE hour=:hour""",
            {'booked': set_booked_to, 'hour': hour, 'email': set_email_to})

def submit_times(bot):
    """
    Submit the selected time block.

    Args:
    bot (Bot): The Bot to submit the time block for.

    Returns:
    bool: True if the time block was submitted, False if it timed out.
    """
    try:
        submit_times = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "submit_times"))
        )
        submit_times.click()
        return True
    except TimeoutException:
        print(f"TimeOutException trying to submit time block for {bot}")
        return False
    
def enter_email(bot):
    """
    Enter the bot's email into the email field and call submit_login_field for email.

    Args:
    bot (Bot): The Bot to enter the email for.

    Returns:
    bool: True if the email was submitted, False if it timed out.
    """
    try:
        email_field = WebDriverWait(bot.driver, 10 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.NAME, "loginfmt"))
        )
        email_field.send_keys(bot.email)
        return submit_login_field(bot, "email")
    except TimeoutException:
        print(f"TimeoutException trying to enter email field for {bot}")
        return False
    
def enter_password(bot):
    """
    Enter the bot's password into the password field and call submit_login_field for password.

    Args:
    bot (Bot): The Bot to enter the password for.

    Returns:
    bool: True if the password was submitted, False if it timed out.
    """
    try:
        pswd_field = WebDriverWait(bot.driver, 10 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.NAME, "passwd"))
        )
        pswd_field.send_keys(bot.password)
        return submit_login_field(bot, "password")
    except TimeoutException:
        print(f"TimeoutException trying to enter password field for {bot}")
        return False

def submit_login_field(bot, sign_in_type):
    """
    Submit the bot's email or password.

    Args:
    bot (Bot): The Bot to submit the email or password for.
    sign_in_type (str): The type of sign in to submit (email or password).
    """
    try:
        submit_button = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        submit_button.click()
        return True
    except TimeoutException:
        print(f"TimeoutException trying to click {sign_in_type} sign in button for {bot}")
        return False
    
def click_continue_button(bot):
    """
    Click the 'continue' button on the page following the email and password submission.

    Args:
    bot (Bot): The Bot to click the 'continue' button for.

    Return:
    bool: True if button was clicked, false otherwise.
    """
    try:
        continue_button = WebDriverWait(bot.driver, 5 * MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.NAME, "continue"))
        )
        continue_button.click()
        return True
    except TimeoutException:
        print(f"TimeoutException trying to click 'continue' button for {bot}")
        return False

def click_submit_booking_button(bot):
    """
    Click the 'submit booking' button to (try to) finalize the booking.

    Args:
    bot (Bot): The Bot to click the 'submit booking' button for.
    """
    try:
        submit_button = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "btn-form-submit"))
        )
        submit_button.click()
        return validate_booking(bot)
    except TimeoutException:
        print(f"TimeoutException trying to click 'submit booking' button for Bot {bot}")
        return False

def validate_booking(bot):
    """
    Valid the booking was successful by checking for the lack of an error message.
    This error message technically should never pop up, according to the code's logic,
    but this provides a layer of security against bugs.
    """
    try:
        error_message = WebDriverWait(bot.driver, MAX_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "jquery-notification"))
        )
        update_time_range_booked(bot, 0, "") # free time ranges bot tried to book
        return False
    except TimeoutException:
        bot.hours_booked = bot.hours_booked + (bot.end_hour - bot.start_hour)
        print(Fore.GREEN + f"SUCCESS: Time block booked for {bot}" + Style.RESET_ALL)
        return True