import string
import struct
import logging

logger = logging.getLogger('x32tunnel')


def encode_message(message):
    return b'=' + struct.pack('>H', len(message)) + b'=' + message


def decode_header(header):
    try:
        assert header[0] == header[3] == b'='[0]
    except AssertionError:
        raise Exception(f'Malformed message header: {header}') from None
    except IndexError:
        raise EOFError(f'Read {len(header)} bytes') from None
    return struct.unpack('>H', header[1:3])[0]


printable_chars = [c for c in string.printable if c not in '\t\n\r\x0b\x0c']

def log_message(text, address, message):
    message = ''.join('~' if chr(c) not in printable_chars else chr(c)
                      for c in message)
    logger.debug(f'{text} {address} {message}')


class MultiConnections:
    def __init__(self):
        self.conns = {}
        self.addresses = {}

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
        
