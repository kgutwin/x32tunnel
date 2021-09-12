import socket
import select
import random
import logging

from x32tunnel import utils

logger = logging.getLogger('x32tunnel')


class TunnelConnections(utils.MultiConnections):
    def __init__(self, address='0.0.0.0', port=10024):
        super().__init__()
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind((address, port))
        self.lsock.listen(2)

    def accept(self):
        # a connection is waiting on lsock
        sock, address = self.lsock.accept()
        self.conns[address] = sock
        self.addresses[sock] = address

    def open_socket(self):
        raise Exception("should not get here")
        
    def on_receive(self, address, sock):
        header = sock.recv(4)
        message_len = utils.decode_header(header)
        message = sock.recv(message_len)
        utils.log_message('Tun recv', address, header + message)
        return address, message

    def on_send(self, sock, message):
        encoded_message = utils.encode_message(message)
        utils.log_message('Tun send', sock.getpeername(), encoded_message)
        sock.send(encoded_message)
        
        

class UdpClient(utils.MultiConnections):
    def __init__(self, mixer_address, mixer_port=10023):
        super().__init__()
        self.mixer = (mixer_address, mixer_port)

    def open_socket(self):
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        sock.bind(('', random.randint(10000, 10512)))
        return sock
        
    def on_send(self, sock, message):
        sock.sendto(message, self.mixer)
    
    def on_receive(self, address, sock):
        message, _ = sock.recvfrom(8192)
        return address, message
        

def main_loop(args):
    logger.info('Starting mixer side')
    cln = UdpClient(args.mixer_host)
    tun = TunnelConnections('0.0.0.0', args.tunnel_port)

    filters = [f.encode() for f in args.filter or []]

    while True:
        ready = select.select([tun.lsock] + cln.sockets + tun.sockets, [], [])[0]
        #logger.debug('Ready: {}'.format(ready))
        for sock in ready:
            if sock == tun.lsock:
                # instantiate a new connection
                tun.accept()
            elif sock in cln.sockets:
                # downstream path, towards client via tunnel
                address, message = cln.receive(sock)
                if any(f in message for f in filters):
                    continue
                tun.send(address, message)
            else:
                # upstream path, towards mixer
                address, message = tun.receive(sock)
                cln.send(address, message)
