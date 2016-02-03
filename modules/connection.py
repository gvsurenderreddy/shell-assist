#!/usr/bin/env python

import sys
import socket
import select


ENCODING = "utf-16"
BUFFER_SIZE = 4096
DELAY = 0.001
MAX_CONNECTIONS = 100


class ForwardServer:
	"""Forward-proxy server"""
	def __init__(self, host, port):
		self.host = host
		self.port = int(port)
		self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def start_server(self):
		try:
			self.forward.connect((self.host, self.port))
			return self.forward
		except Exception as e:
			print(e)
			return False


class ServerConnection:
	"""For server connection and transmission of data"""

	input_list = []
	channels = {}
	
	def __init__(self, host, port = 9876):
		self.host = host
		self.port = int(port)
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.port))
		self.server.listen(MAX_CONNECTIONS)

	def listening_loop(self):
		print("Assist-Server starting...")
		print("Listening to connections...")
		self.input_list.append(self.server)
		while True:
			try:
				readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
			except Exception as e:
				print(e)
				break
			for ready_server in readlist:
				if ready_server == self.server:
					self.on_accept()
					break
				self.data = ready_server.recv(BUFFER_SIZE)
				if len(self.data):
					self.on_recv(ready_server)
				else:
					self.on_close(ready_server)
					break

	def on_accept(self):
		#forward_sock = ForwardServer(self.host, self.port).start_server()
		client_sock, client_addr = self.server.accept()
		self.input_list.append(client_sock)
		self.channels[client_sock] = client_addr
		print("{} has connected.".format(client_addr))
		# if forward_sock:
		# 	print("{} has connected.".format(client_addr))
		# 	self.input_list.append(client_sock)
		# 	self.input_list.append(forward_sock)
		# 	self.channels[client_sock] = forward_sock
		# 	self.channels[forward_sock] = client_sock
		# else:
		# 	print("Could not establish connection with server.")
		# 	print("Closing connection with client {}.".format(client_addr))
		# 	client_sock.close()


	def on_recv(self, dest):
		print("Received from {}: {}".format(self.channels[dest], self.data.decode(ENCODING)))
		dest.sendall(self.data)

	def on_close(self, dest):
		print("{} has disconnected.".format(dest.getpeername()))
		self.input_list.remove(dest)
		#self.input_list.remove(self.channels[dest])
		#self.channels[dest].close()
		#del self.channels[self.channels[out]]
		del self.channels[dest]
		dest.close()

	def start_server(self):
		try:
			self.listening_loop()
		except KeyboardInterrupt:
			print("\nStopping server...")
			self.server.close()
			sys.exit(0)


class ClientConnection:
	"""For client connection"""

	input_list = []
	
	def __init__(self, host, port = 9876, username = 'me'):
		self.host = host
		self.port = int(port)
		self.username = username
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket
		self.input_list.append(0) # stdin
		self.input_list.append(self.sock)

	def prompt(self, name = ''):
		if !name:
			name = self.username
		return str(name) + "> "

	def connect_to_server(self):
		try:
			print("Assist-Client starting...")
			readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
			self.sock.connect((self.host, self.port))
			print("Connected to server.")
			while True:
				print(self.prompt(),)
				for input_ready in readlist:
					if input_ready == 0:
						line = sys.stdin.readline()
						if line:
							self.sock.sendall(bytes(line, ENCODING))
					elif input_ready == self.sock:
						self.data = self.sock.recv(BUFFER_SIZE)
						if data:
							print(self.prompt("Server"), self.data.decode(ENCODING))
						else:
							break
			print("Disconnecting...")
			self.sock.close()
			sys.exit(0)
		except ConnectionRefusedError:
			print("Error: Assist-Server not available on this address and/or port!")
			sys.exit(1)
		except KeyboardInterrupt:
			print("\nStopping client...")
			self.sock.close()
			sys.exit(0)
		except Exception as e:
			print(e)
			sys.exit(1)
