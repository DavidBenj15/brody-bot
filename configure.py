import argparse
import configparser
import sys

def main():
    parser = argparse.ArgumentParser(description="Bot Configuration")

    parser.add_argument("--starthour", type=float, help="Earliest time bot will book from.")
    parser.add_argument("--endhour", type=float, help="Latest time bot will book from.")
    
    args = parser.parse_args()

    # if missing configurations:
    prev_starthour, prev_endhour = load_previous_configs()
    if not args.starthour:
        args.starthour = prev_starthour
    if not args.endhour:
        args.endhour = prev_endhour
    validate_hours(args.starthour, args.endhour)

    configs = vars(args)
    write_configs(configs)


def load_previous_configs(file_path='user_config.ini'):
    config = configparser.ConfigParser()
    config.read(file_path)

    if 'UserSettings' in config:
        starthour = config.getfloat('UserSettings', 'starthour')
        endhour = config.getfloat('UserSettings', 'endhour')
        return starthour, endhour
    else:
        raise ValueError("UserSettings configuration not found in", file_path)


def validate_hours(starthour, endhour):
    if endhour <= starthour:
        print("Error: endhour must be greater than starthour.")
        sys.exit(1)
    if starthour < 0 or starthour > 23.5 or starthour < 0 or starthour > 24:
        print("Error: hours must be in the range 0.0-24.0")
        sys.exit(1)
    if (starthour) % 0.5 != 0 or (endhour) % 0.5 != 0:
        print("Error: hours must be divisible by 0.5.")
        sys.exit(1)

def write_configs(configs):
    user_config = configparser.ConfigParser()
    user_config['UserSettings'] = configs
    with open('user_config.ini', 'w') as f:
        user_config.write(f)


if __name__ == "__main__":
    main()
