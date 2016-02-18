class Utils:
	"""common utility functions of different purposes"""

	@staticmethod
	def split(line, sep, n):
		parts = []
		t_parts = line.split(sep)
		if len(t_parts) > n+1:
			for i in range(1, n):
				parts.append(t_parts[i])
			parts.append(sep.join(t_parts[n:]))
		else:
			parts = t_parts[1:]
		return parts
