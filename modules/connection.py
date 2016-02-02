#!/usr/bin/env python

import sys
import socket
import select


class ForwardServer:
	"""Forward-proxy server"""
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def start_server(self):
		try:
			self.forward.connect((self.host, self.port))
			return self.forward
		except Exception as e:
			print(e)


class ServerConnection:
	"""For server connection and transmission of data"""

	BUFFER_SIZE = 1024
	DELAY = 0.001
	MAX_CONNECTIONS = 100
	input_list = []
	channels = {}
	
	def __init__(self, host = "localhost", port = 9876):
		self.host = host
		self.port = port
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((host, port))
		self.server.listen(self.MAX_CONNECTIONS)

	def listening_loop(self):
		self.input_list.append(self.server)
		while True:
			ss = select.select
			readlist, writelist, exceptlist = ss(self.input_list, [], [], self.DELAY)
			for ready_server in readlist:
				if ready_server == self.server:
					self.on_accept()
					break
				self.data = ready_server.recv(self.BUFFER_SIZE)
				if len(self.data):
					self.on_recv(ready_server)
				else:
					self.on_close(ready_server)
					break

	def on_accept(self):
		forward_sock = ForwardServer(self.host, self.port).start_server()
		client_sock, client_addr = self.server.accept()
		if forward_sock:
			print("{} has connected.".format(client_addr))
			self.input_list.append(client_sock)
			self.input_list.append(forward_sock)
			self.channels[client_sock] = forward_sock
			self.channels[forward_sock] = client_sock
		else:
			print("Could not establish connection with server.")
			print("Closing connection with client {}.".format(client_addr))
			client_sock.close()


	def on_recv(self, dest):
		self.channels[dest].send(self.data)

	def on_close(self, dest):
		print("{} has disconnected.".format(dest.getpeername()))
		self.input_list.remove(dest)
		self.input_list.remove(self.channels[dest])
		dest.close()
		self.channels[dest].close()
		del self.channels[self.channels[out]]
		del self.channels[dest]

	def start_server(self):
		try:
			self.listening_loop()
		except KeyboardInterrupt:
			print("\nStopping server...")
			self.server.close()
			sys.exit(0)


class ClientConnection:
	"""For client connection"""
	
	def __init__(self, host = "localhost", port = 9876):
		self.host = host
		self.port = port
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket

	def connect_to_server(self):
		try:
			self.sock.connect((self.host, self.port))
		except KeyboardInterrupt:
			print("\nStopping client...")
			self.sock.close()
			sys.exit(0)
