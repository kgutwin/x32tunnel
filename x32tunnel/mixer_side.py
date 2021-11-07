import re
import time
import queue
import socket
import select
import random
import logging
import threading

from x32tunnel import utils

logger = logging.getLogger('x32tunnel')


class TunnelConnections(utils.MultiConnections):
    def __init__(self, address='0.0.0.0', port=10024):
        super().__init__()
        self.queues = {}
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind((address, port))
        self.lsock.listen(2)

    def accept(self):
        # a connection is waiting on lsock
        sock, address = self.lsock.accept()
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            8192)
        self.conns[address] = sock
        self.addresses[sock] = address
        self.queues[sock] = queue.LifoQueue(maxsize=8)
        threading.Thread(target=self.send_thread, args=[sock]).start()

    def close(self, sock):
        self.queues[sock].put(None)
        address = self.addresses[sock]
        del(self.addresses[sock])
        del(self.conns[address])
        del(self.queues[sock])

    def open_socket(self):
        raise Exception("should not get here")
        
    def on_receive(self, address, sock):
        message = utils.read_message(sock)
        utils.log_message('Tun recv', address, message)
        return address, message

    def on_send(self, sock, message):
        encoded_message = utils.encode_message(message)
        utils.log_message('Tun send', sock.getpeername(), encoded_message)
        try:
            self.queues[sock].put(encoded_message, block=False)
        except queue.Full:
            pass
        #sock.send(encoded_message)
        
    def send_thread(self, sock):
        q = self.queues[sock]
        while True:
            message = q.get()
            if message is None:
                break
            sock.send(message)
        

class UdpClient(utils.MultiConnections):
    def __init__(self, mixer_address, mixer_port=10023):
        super().__init__()
        self.mixer = (mixer_address, mixer_port)

    def open_socket(self):
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.bind(('', random.randint(10000, 10512)))
        return sock
        
    def on_send(self, sock, message):
        sock.sendto(message, self.mixer)
    
    def on_receive(self, address, sock):
        try:
            message, _ = sock.recvfrom(8192)
            return address, message
        except socket.error:
            return None, None
        

class MessageFilter:
    def __init__(self, filter, rate_limits, rate_limit):
        self.filters = [
            re.compile(f.encode())
            for f in filter
        ]
        self.rate_limit_patterns = [
            re.compile(f.encode())
            for f in rate_limits
        ]
        self.rate_limits = {}
        self.rate_limit = rate_limit

    def allow(self, message):
        if not message:
            return False

        if any(f.search(message) for f in self.filters):
            return False

        for p in self.rate_limit_patterns:
            m = p.search(message)
            if m:
                f = m.group(0)
                self.rate_limits.setdefault(f, time.time())
                if time.time() > self.rate_limits[f] + self.rate_limit:
                    rate_limits[f] = time.time()
                else:
                    return False

        return True


def main_loop(args):
    logger.info('Starting mixer side')
    cln = UdpClient(args.mixer_host)
    tun = TunnelConnections('0.0.0.0', args.tunnel_port)

    message_filter = MessageFilter(
        args.filter or [],
        args.rate_limits or [],
        args.rate_limit
    )

    while True:
        ready = select.select([tun.lsock] + cln.sockets + tun.sockets, [], [])[0]
        #logger.debug('Ready: {}'.format(ready))
        for sock in ready:
            if sock == tun.lsock:
                # instantiate a new connection
                tun.accept()
            elif sock in cln.sockets:
                # downstream path, towards client via tunnel
                try:
                    address, message = cln.receive(sock)
                    if message_filter.allow(message):
                        tun.send(address, message)
                except utils.MalformedMessageException as ex:
                    logger.warn(str(ex))
                except EOFError:
                    tsock = tun.conns[address]
                    logger.warn('Client closed conn, expiring {}'.format(tsock))
                    tun.close(tsock)
            else:
                # upstream path, towards mixer
                try:
                    address, message = tun.receive(sock)
                    cln.send(address, message)
                except utils.MalformedMessageException as ex:
                    logger.warn(str(ex))
                except EOFError:
                    logger.warn('Client closed connection, expiring {}'.format(sock))
                    tun.close(sock)
