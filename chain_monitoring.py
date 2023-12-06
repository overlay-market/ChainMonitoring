import time
import traceback
from constants import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
# from prometheus_metrics import metrics
from prometheus_client import start_http_server
from metrics.mint import thread as thread_mint
from metrics.upnl import thread as thread_upnl
from utils import send_telegram_message

def main():
    # metrics['mint_gauge'].labels(market='TEST').set(100)
    # Start Prometheus server
    start_http_server(8000)

    # Start the threads
    thread_mint.start()
    thread_upnl.start()

    time.sleep(10)
    # raise Exception("Intentional failure")

    while True:
        try:
            # Keep the main thread alive to let the threads run
            time.sleep(5)  # Adjust the sleep time as needed
        except Exception as e:
            # Log the exception if needed
            error_message = f"Exception occurred: {e}"
            traceback_str = traceback.format_exc()
            print(error_message)
            # Terminate the threads
            thread_mint.join()
            thread_upnl.join()
            # Restart the process after a delay

            send_telegram_message(
                TELEGRAM_BOT_TOKEN,
                TELEGRAM_CHAT_ID,
                f"[ERROR]:\n{error_message}.\n\n[TRACEBACK]\n {traceback_str}"
            )
            print("Restarting...")
            time.sleep(10)  # Delay before restarting

if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            # Log the exception if needed
            error_message = f"Exception occurred in main loop: {e}"
            print(error_message)
            traceback_str = traceback.format_exc()
            send_telegram_message(
                TELEGRAM_BOT_TOKEN,
                TELEGRAM_CHAT_ID,
                f"[ERROR]:\n{error_message}.\n\n[TRACEBACK]\n {traceback_str}"
            )

            # Delay before restarting if an exception occurs in the main loop
            time.sleep(10)
