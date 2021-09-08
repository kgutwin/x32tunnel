import socket
import select
import logging

from x32tunnel import utils

logger = logging.getLogger('x32tunnel')


class TunnelConnections(utils.MultiConnections):
    def __init__(self, mixer_side_address, mixer_side_port):
        super().__init__()
        self.mixer_side_address = mixer_side_address
        self.mixer_side_port = mixer_side_port

    def open_socket(self):
        sock = socket.socket()
        sock.connect((self.mixer_side_address, self.mixer_side_port))
        return sock
        
    def on_send(self, sock, message):
        encoded_message = utils.encode_message(message)
        utils.log_message('Tun send', sock.getpeername(), encoded_message)
        sock.sendall(encoded_message)

    def on_receive(self, address, sock):
        header = sock.recv(4)
        message_len = utils.decode_header(header)
        message = sock.recv(message_len)
        utils.log_message('Tun recv', address, header + message)
        return address, message

        
class UdpServer:
    def __init__(self, address='0.0.0.0', port=10023):
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sock.bind((address, port))

    def receive(self):
        message, address = self.sock.recvfrom(8192)
        return address, message

    def send(self, address, message):
        self.sock.sendto(message, address)


        
def main_loop(args):
    logger.info('Starting client side')
    srv = UdpServer(args.udp_bind_host)
    tun = TunnelConnections(args.tunnel_host, args.tunnel_port)
                 
    while True:
        ready = select.select([srv.sock] + tun.sockets, [], [])[0]
        logger.debug(f'Ready: {ready}')
        for sock in ready:
            if sock == srv.sock:
                # upstream path, towards mixer via tunnel
                address, message = srv.receive()
                tun.send(address, message)
            else:
                # downstream path, towards local client
                address, message = tun.receive(sock)
                srv.send(address, message)
