#!/usr/bin/env python

import sys
import socket
import select
import threading


ENCODING = "utf-16"
BUFFER_SIZE = 4096
DELAY = 0.1
MAX_CONNECTIONS = 100


class ServerConnection:
	"""For server connection and transmission of data"""

	input_list = []
	channels = {}
	usernames = {}
	usernames_reverse = {} # useful for reverse lookup
	
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
			except ConnectionRefusedError:
				print("Client has disconnected!")
			except Exception as e:
				print(e)
				break

	def parse_command(self, dest, line):
		line = line.strip()
		l_line = line.lower()
		if l_line.startswith("/setname ") or l_line.startswith("/setname\t"):
			name = line[9:].lstrip()
			if name not in self.usernames:
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				print("Client {} has identified as '{}'.".format(self.channels[dest], name))
			else:
				# name already taken
				pass
		else:
			print("{}{}".format(self.prompt(self.usernames_reverse[dest], self.channels[dest][0]), line))

	def on_accept(self):
		client_sock, client_addr = self.server.accept()
		self.input_list.append(client_sock)
		self.channels[client_sock] = client_addr
		print("Client {} has connected.".format(client_addr))
		client_sock.sendall(bytes("Welcome.", ENCODING))

	def on_recv(self, dest):
		self.data = self.data.decode(ENCODING)
		self.parse_command(dest, self.data)

	def on_close(self, dest):
		print("Client {} has disconnected.".format(dest.getpeername()))
		self.input_list.remove(dest)
		del self.channels[dest]
		dest.close()

	def start_server(self):
		try:
			self.listening_loop()
		except KeyboardInterrupt:
			print("\nStopping server...")
			self.server.close()
			sys.exit(0)

	def prompt(self, name, addr):
		return "[{}@{}]> ".format(name, addr)


class ClientConnection:
	"""For client connection"""

	input_list = []
	
	def __init__(self, host, port = 9876, username = 'me'):
		self.listen_loop = True
		self.connect_loop = True
		self.host = host
		self.port = int(port)
		self.username = username
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket
		#self.input_list.append(sys.stdin)
		self.input_list.append(self.sock)

	def listen_receive(self):
		readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
		while self.listen_loop:
			if not self.sock:
				break
			for input_ready in readlist:
				if input_ready == self.sock:
					self.data = self.sock.recv(BUFFER_SIZE)
					if self.data:
						print("{}{}".format(self.prompt("Server"), self.data.decode(ENCODING)))
					else:
						break

	def send_name(self):
		self.sock.sendall(bytes("/setname {}".format(self.username), ENCODING))

	def prompt(self, name = ''):
		if not name:
			name = self.username
		return str(name) + "> "

	def parse_command(self, sock, line):
		line = line.strip()
		l_line = line.lower()
		if l_line == "/exit" or l_line == "/quit":
			self.connect_loop = False
		elif l_line == "/list":
			pass
		elif l_line.startswith("/list ") or l_line.startswith("/list\t"):
			args = line[6:].lstrip()
			pass
		elif l_line.startswith("/chat ") or l_line.startswith("/chat\t"):
			args = line[6:].lstrip()
			pass
		elif l_line.startswith("/shell ") or l_line.startswith("/shell\t"):
			args = line[6:].lstrip()
			pass
		elif l_line.startswith("/send ") or l_line.startswith("/send\t"):
			args = line[6:].lstrip()
			pass
		if line and self.connect_loop:
			sock.sendall(bytes(line, ENCODING))

	def connect_to_server(self):
		try:
			print(self.prompt("Client") + "Starting...")
			self.sock.connect((self.host, self.port))
			self.listening_thread = threading.Thread(target=self.listen_receive)
			self.listening_thread.daemon = True
			self.listening_thread.start()
			print("{}Connected to server.".format(self.prompt("Client")))
			self.send_name()
			while self.connect_loop:
				if not self.sock:
					print(self.prompt("Client") + "Server disconnected.")
					break
				line = input(self.prompt())
				self.parse_command(self.sock, line)
			print(self.prompt("Client") + "Disconnecting...")
			self.sock.close()
			self.listen_loop = False
			sys.exit(0)
		except ConnectionRefusedError:
			print(self.prompt("Client") + "Error: Assist-Server not available on this address and/or port!")
			self.listen_loop = False
			sys.exit(1)
		except KeyboardInterrupt:
			print("\n" + self.prompt("Client") + "Exiting...")
			self.sock.close()
			self.listen_loop = False
			sys.exit(0)
		except BrokenPipeError:
			print("{}Server closed the connection.".format(self.prompt("Client")))
			self.listen_loop = False
			sys.exit(1)
		except Exception as e:
			self.listen_loop = False
			print(e)
			sys.exit(1)
