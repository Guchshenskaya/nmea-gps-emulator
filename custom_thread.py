import logging
import threading
import time
import socket

from auxiliary_funcs import exit_script

class NmeaSrvThread(threading.Thread):
    """
    A class that represents a thread dedicated for TCP (telnet) server-client connection.
    """
    def __init__(self, ip_add, nmea_object, conn=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heading = None
        self.speed = None
        self._heading_cache = 0
        self._speed_cache = 0
        self.conn = conn
        self.ip_add = ip_add
        self.nmea_object = nmea_object
        self._lock = threading.RLock()

    def set_speed(self, speed):
        with self._lock:
            self.speed = speed

    def set_heading(self, heading):
        with self._lock:
            self.heading = heading

    def run(self):
        while True:
            timer_start = time.perf_counter()
            with self._lock:
                # Nmea object speed and heading update
                if self.heading and self.heading != self._heading_cache:
                    self.nmea_object.heading_targeted = self.heading
                    self._heading_cache = self.heading
                if self.speed and self.speed != self._speed_cache:
                    self.nmea_object.speed_targeted = self.speed
                    self._speed_cache = self.speed
                # The following commands allow the same copies of NMEA data is sent on all threads
                # Only first thread in a list can iterate over NMEA object (the same nmea output in all threads)
                thread_list = [thread.name for thread in threading.enumerate() if thread.name.startswith('nmea_srv')]
                current_thread_name = threading.current_thread().name
                if len(thread_list) > 1 and current_thread_name != thread_list[0]:
                    nmea_list = [f'{_}' for _ in self.nmea_object.nmea_sentences]
                else:
                    nmea_list = [f'{_}' for _ in next(self.nmea_object)]
                try:
                    for nmea in nmea_list:
                        self.conn.sendall(nmea.encode())
                        time.sleep(0.05)
                except (BrokenPipeError, OSError):
                    self.conn.close()
                    # print(f'\n*** Connection closed with {self.ip_add[0]}:{self.ip_add[1]} ***')
                    logging.info(f'Connection closed with {self.ip_add[0]}:{self.ip_add[1]}')
                    # Close thread
                    exit_script()
            time.sleep(1 - (time.perf_counter() - timer_start))


class NmeaStreamThread(NmeaSrvThread):
    """
    A class that represents a thread dedicated for TCP or UDP stream connection.
    """
    def __init__(self, proto, port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proto = proto
        self.port = port

    def run(self):
        if self.proto == 'tcp':
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.ip_add, self.port))
                    print(f'\n*** Sending NMEA data - TCP stream to {self.ip_add}:{self.port}... ***\n')
                    while True:
                        timer_start = time.perf_counter()
                        with self._lock:
                            # Nmea object speed and heading update
                            if self.heading and self.heading != self._heading_cache:
                                self.nmea_object.heading_targeted = self.heading
                                self._heading_cache = self.heading
                            if self.speed and self.speed != self._speed_cache:
                                self.nmea_object.speed_targeted = self.speed
                                self._speed_cache = self.speed
                            nmea_list = [f'{_}' for _ in next(self.nmea_object)]
                            for nmea in nmea_list:
                                s.send(nmea.encode())
                                time.sleep(0.05)
                            # Start next loop after 1 sec
                        time.sleep(1 - (time.perf_counter() - timer_start))
            except (OSError, TimeoutError, ConnectionRefusedError, BrokenPipeError) as err:
                print(f'\n*** Error: {err.strerror} ***\n')
                exit_script()
        elif self.proto == 'udp':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                print(f'\n*** Sending NMEA data - UDP stream to {self.ip_add}:{self.port}... ***\n')
                while True:
                    timer_start = time.perf_counter()
                    with self._lock:
                        # Nmea object speed and heading update
                        if self.heading and self.heading != self._heading_cache:
                            self.nmea_object.heading_targeted = self.heading
                            self._heading_cache = self.heading
                        if self.speed and self.speed != self._speed_cache:
                            self.nmea_object.speed_targeted = self.speed
                            self._speed_cache = self.speed
                        nmea_list = [f'{_}' for _ in next(self.nmea_object)]
                        for nmea in nmea_list:
                            try:
                                s.sendto(nmea.encode(), (self.ip_add, self.port))
                                time.sleep(0.05)
                            except OSError as err:
                                print(f'*** Error: {err.strerror} ***')
                                exit_script()
                        # Start next loop after 1 sec
                    time.sleep(1 - (time.perf_counter() - timer_start))



