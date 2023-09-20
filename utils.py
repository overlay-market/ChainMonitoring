import json
import datetime


def write_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump({"data": data}, json_file, indent=4)


def format_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime(
        '%Y-%m-%d %H:%M:%S')
