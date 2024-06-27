# JHU BrodyBot

This bot allows you to book a specified room in the Johns Hopkins Brody/MSE library for up to an entire day. The bot will run at midnight every night, so you won't have to worry about staying up to book a study room anymore.

## End User Setup Instructions
### 1. Install Dependencies
Download the project directory and ensure Python 3 is installed on your computer.
In the project directory, open your terminal and execute the following command:\
<code>pip install -r requirements.txt</code>

### 2. Configure Program
To customize the bot, run configure.py with any of the following command options:
* <code>--starthour</code>: the earliest time the bot will book from.
* <code>--endhour</code>: the latest time the bot will book to.
* <code>--roomlink</code>: the link to the study room that the bot will book. Visit [here](https://jhu.libcal.com/spaces?lid=1195&gid=2086&c=0) to find a room to book.\
For example, running:\
<code>configure.py --starthour 10 --endhour 22 --roomlink https://jhu.libcal.com/space/7913</code>\
would configure the bot to book room 2006 from 10 AM to 10 PM every day.
