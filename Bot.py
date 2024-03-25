class Bot:
    def __init__(self, name, email, password, initial_hour):
        self.name = name
        self.email = email
        self.password = password
        self.initial_hour = initial_hour
        self.start_hour = None
        self.end_hour = None
        self.hours_booked = 0
        self.driver = None

    def __str__(self):
        return f'Bot(name={self.name}, email={self.email})'