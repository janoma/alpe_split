import argparse
import codecs
import logging
import os
import re
import socket
import sys
import time

class AlpeChecker:
    current_segment = 1
    prev_timestamp = None
    log_file_path = None
    split_socket = None

    def __init__(self, s, log_path):
        self.split_socket = s
        self.log_file_path = log_path
        logging.info("Waiting for an attempt to Alpe du Zwift to start...")

    def notifyStart(self):
        self.split_socket.send(b"reset\r\n")
        self.split_socket.send(b"starttimer\r\n")

    def notifySplit(self):
        self.split_socket.send(b"split\r\n")

    def check(self):
        with codecs.open(self.log_file_path, 'r', encoding='utf-8',
                errors='ignore') as lines:
            for line in lines:
                start_pattern = re.compile(
                        "crossed arch start line Alpe du Zwift")
                if self.prev_timestamp == None and start_pattern.search(line):
                    self.prev_timestamp = int(time.time())
                    self.notifyStart()
                    logging.info("Alpe attempt started")
                    break
                elif self.prev_timestamp is not None:
                    # Note the typo in 'segmnet', taken verbatim from Zwift
                    # logs. If it's fixed in the future, this will need an
                    # update. Alpe segments have IDs from 2233445501 to
                    # 2233445522 (the last one being the finish banner).
                    segment_pattern = re.compile(
                            "passed finish line of segmnet "
                            + str(2233445500 + self.current_segment))
                    if segment_pattern.search(line):
                        logging.debug("Segment " + str(self.current_segment)
                                + " completed")
                        self.current_segment = self.current_segment + 1
                        self.prev_timestamp = int(time.time())
                        self.notifySplit()
                        break

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
            prog = 'alpe_split',
            description = 'Sends Alpe du Zwift splits to a LiveSplit server.',
            epilog = 'Happy Zwifting!',
            formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host',
            default = 'localhost',
            help = 'The hostname of the server where the splits are notified.')
    parser.add_argument('--port',
            default = 16834,
            type=int,
            help = 'The port of the server where the splits are notified.')
    parser.add_argument('--zwift_dir',
            default = os.path.join(os.path.expanduser("~"), 'Documents',
                'Zwift'),
            help = 'Location of the user\'s Zwift directory.')
    args = parser.parse_args()
    logging.debug(args)

    split_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        split_socket.connect((args.host, args.port))
    except ConnectionRefusedError:
        logging.error("Couldn't connect to {0}:{1}".format(args.host, args.port)
                + ". Did you start LiveSplit's server?")
        sys.exit(1)

    log_path = os.path.join(args.zwift_dir, 'Logs', 'Log.txt')
    alpe_checker = AlpeChecker(split_socket, log_path)
    try:
        while True:
            alpe_checker.check()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping split recording...")
