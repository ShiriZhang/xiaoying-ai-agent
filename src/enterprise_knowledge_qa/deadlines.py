"""Injectable monotonic deadlines and bounded waits without late publication."""

from datetime import datetime
from queue import Empty, Queue
from threading import Thread
import time


class Clock:
    def monotonic(self) -> float:
        return time.monotonic()

    def now(self) -> datetime:
        return datetime.now().astimezone()


def bounded_call(function, timeout: float):
    """Worker owns scratch results only; caller alone publishes accepted results.

    A timed-out daemon may continue computing/being billed; it cannot append to
    the caller's trace or commit an accepted read-set. No forced OS cancellation.
    """
    if timeout <= 0:
        raise TimeoutError
    queue = Queue(maxsize=1)

    def work():
        try:
            queue.put((True, function()))
        except Exception as error:
            queue.put((False, error))

    Thread(target=work, daemon=True).start()
    try:
        success, value = queue.get(timeout=timeout)
    except Empty:
        raise TimeoutError from None
    if not success:
        raise value
    return value
