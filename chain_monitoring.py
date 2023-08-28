from prometheus_client import start_http_server

from metrics.mint import thread as thread_mint
from metrics.upnl import thread as thread_upnl

# Start Prometheus server
start_http_server(8000)


if __name__ == '__main__':
    # Start the threads
    thread_mint.start()
    thread_upnl.start()


try:
    # Keep the main thread alive to let the threads run
    while True:
        pass
except KeyboardInterrupt:
    # Terminate the threads when the main thread is interrupted (Ctrl+C)
    thread_mint.join()
    thread_upnl.join()
