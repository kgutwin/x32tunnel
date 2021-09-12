import zlib
import socket
import string
import struct
import logging

logger = logging.getLogger('x32tunnel')


def encode_message(message):
    message = zlib.compress(message)
    return b'=' + struct.pack('>H', len(message)) + b'=' + message


def decode_header(header):
    try:
        assert header[0] == header[3] == b'='[0]
    except AssertionError:
        raise Exception('Malformed message header: {}'.format(header))
    except IndexError:
        raise EOFError('Read {} bytes'.format(len(header)))
    return struct.unpack('>H', header[1:3])[0]


def read_message(sock):
    header = sock.recv(4)
    message_len = decode_header(header)
    message = sock.recv(message_len)
    message = zlib.decompress(message)
    return message


def osc_parse(msg):
    buf = ''
    nulls = 0
    for c in msg:
        if c == 0:
            nulls += 1
            if (len(buf) + nulls) % 4 == 0:
                yield buf
                buf = ''
                nulls = 0
        else:
            buf += chr(c)

def osc_join(parts):
    return b''.join([c.encode() + (b'\x00' * (4 - len(c) % 4)) for c in parts])

def patch_message(message):
    if message.startswith(b'/xinfo\x00\x00,ssss\x00\x00\x00'):
        mparts = list(osc_parse(message))
        mparts[2] = socket.gethostbyname(socket.gethostname())
        message = osc_join(mparts)
        log_message('Patched:', None, message)
    elif message.startswith(b'/status\x00,sss\x00\x00\x00\x00'):
        mparts = list(osc_parse(message))
        mparts[3] = socket.gethostbyname(socket.gethostname())
        message = osc_join(mparts)
        log_message('Patched:', None, message)
    return message


printable_chars = [c for c in string.printable if c not in '\t\n\r\x0b\x0c']

def log_message(text, address, message):
    message = ''.join('~' if chr(c) not in printable_chars else chr(c)
                      for c in message)
    #message = repr(message)
    logger.debug('{} {} {}'.format(text, address, message))


class MultiConnections:
    def __init__(self):
        self.conns = {}
        self.addresses = {}
        self.threads = {}

    def open_socket(self):
        raise NotImplemented()

    def on_send(self, sock, message):
        raise NotImplemented()

    def on_receive(self, address, sock):
        raise NotImplemented()
        
    @property
    def sockets(self):
        return list(self.conns.values())

    def send(self, address, message):
        if address not in self.conns:
            sock = self.open_socket()
            self.conns[address] = sock
            self.addresses[sock] = address

        return self.on_send(self.conns[address], message)
    
    def receive(self, sock):
        address = self.addresses[sock]
        return self.on_receive(address, sock)
        
