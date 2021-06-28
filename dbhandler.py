import json

class StudentDB(object):
	def __init__(self, params):
		super(StudentDB, self).__init__()
		self.database_path = params.get("database_path", "student.json")
		try:
			with open(self.database_path, "r") as file:
				self.database = json.load(file)
		except FileNotFoundError as e:
			self.database = {}

	def create_entry(self, key, value):
		if key in self.database:
			print(f"{key} already exists in the Database.")
			return
		self.database[key] = value

	def read_entry(self, key, value):
		if not key in self.database:
			print(f"{key} does not exist in the Database.")
			return
		return self.database[key]

	def update_entry(self, key, value):
		if not key in self.database:
			print(f"{key} does not exist in the Database.")
			return
		self.database[key] = value

	def delete_entry(self, key, value):
		if not key in self.database:
			print(f"{key} does not exist in the Database.")
			return
		del self.database[key]

	def save_changes(self):
		try:
			with open(self.database_path, "w") as file:
				json.dump(self.database, file)
			print(f"The changes are saved successfully.")
		except Exception as e:
			print(e)
			print(f"Could not save the changes.")

def main():
	params = {
		"database_path": "student.json"
	}
	studentdb = StudentDB(params)
	# key = 'email'
	# value = {
	# 	'roll_no': '<roll-no>',
	# 	'card_no': '<card-no>',
	# }
	# studentdb.create_entry(key, value)
	# studentdb.delete_entry(key, value)
	studentdb.save_changes()

if __name__ == "__main__":
	main()