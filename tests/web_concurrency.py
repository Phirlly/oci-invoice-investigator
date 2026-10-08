"""Bounded real-connection coordination, shared only by transaction tests."""

import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Barrier

from django.db import connection, connections


def simultaneously(*calls):
    barrier = Barrier(len(calls), timeout=5)

    def run(call):
        connections.close_all()
        try:
            barrier.wait()
            return call()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(calls)) as executor:
        futures = [executor.submit(run, call) for call in calls]
        return [future.result(timeout=8) for future in futures]


def submit_connection(executor, call):
    started = Queue(maxsize=1)

    def run():
        connections.close_all()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                started.put(cursor.fetchone()[0])
            return call()
        finally:
            connections.close_all()

    future = executor.submit(run)
    return future, started.get(timeout=3)


def wait_for_row_lock(pid):
    deadline = time.monotonic() + 3
    with connection.cursor() as cursor:
        while time.monotonic() < deadline:
            cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", [pid])
            row = cursor.fetchone()
            if row and row[0] == "Lock":
                return
            cursor.execute("SELECT pg_stat_clear_snapshot()")
    raise AssertionError("The competing service did not wait on a PostgreSQL row lock.")
