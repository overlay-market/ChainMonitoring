import json
import datetime
import requests
import threading
import traceback
from constants import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)

def write_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump({"data": data}, json_file, indent=4)


def format_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime(
        '%Y-%m-%d %H:%M:%S')


def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'parse_mode': 'HTML',
        'text': message,
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Failed to send message: {e}")


def handle_error(error_message):
    traceback_str = traceback.format_exc()
    send_telegram_message(
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        f"[ERROR]:\n{error_message}.\n\n[TRACEBACK]\n {traceback_str}"
    )


class CMThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exc = None
        self._traceback = None

    def run(self):
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
        except Exception as e:
            self._traceback = traceback.format_exc()
            self._exc = e

    def get_exception(self):
        if self._traceback and self._exc:
            return f"[ERROR]\n{self._exc}\n\n[TRACEBACK]\n{self._traceback}"

    def send_exceptions_to_tg(self):
        exception = self.get_exception()
        if exception:
            send_telegram_message(
                TELEGRAM_BOT_TOKEN,
                TELEGRAM_CHAT_ID,
                f"Error on thread.\n\n{exception}"
            )

def send_alert(
    alert_level,
    alert_name,
    rule_formula,
    metric_label,
):
    alert_level_icon_map = {
        'green': '🟢',
        'orange': '🟠',
        'red': '🔴',
    }
    message = (
        f"{alert_level_icon_map[alert_level]} {alert_name}\n" +
        f"alert_level={alert_level}\n" +
        # f"alert_name={alert_name}\n"
        f"rule_formula={rule_formula}\n" +
        f"metric_label={metric_label}\n"
    )
    print('message', message)
    send_telegram_message(
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        message,
    )
