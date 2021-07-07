import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import flask
import datetime
from dateutil.relativedelta import relativedelta

import requests
from bs4 import BeautifulSoup

from random import randint
import json
import os
import re

current_dir_path = os.path.dirname(os.path.abspath(__file__))

class DateTimeUtil(object):
	date_time = datetime.datetime.today()
	today = datetime.datetime(date_time.year, date_time.month, date_time.day)
	today_string = today.date().isoformat()

	def __init__(self, params):
		super(DateTimeUtil, self).__init__()
		from_date = params.get("from_date")
		to_date = params.get("to_date")
		in_depth = params.get("in_depth")
		mock = params.get("mock")
		self.from_to_epochs = []
		self.from_date_epoch = self.to_epoch(from_date)
		self.to_date_epoch = self.to_epoch(to_date)
		if mock or in_depth:
			start = from_date
			end = to_date
			while start <= end:
				self.from_to_epochs.append(self.to_epoch(start))
				start += relativedelta(days=1)
		else:
			start = self.first_day_of_month(from_date)
			end = self.first_day_of_month(to_date)
			while start <= end:
				self.from_to_epochs.append(self.to_epoch(start))
				start += relativedelta(months=1)

	def to_epoch(self, date):
		return int(date.timestamp())

	def first_day_of_month(self, date):
		return date.replace(day=1)


class RequestArgParser(object):
	def __init__(self, sep_char="x"):
		super(RequestArgParser, self).__init__()
		self.sep_char = sep_char
		self.email_regex = "^(.+)@(.+)$"

	def format_date(self, date_string):
		if date_string == None:
			return DateTimeUtil.today_string
		try:
			return datetime.datetime.strptime(date_string, "%Y-%m-%d")
		except ValueError:
			raise ValueError(
				{
					"code": "invalid-date-format",
					"message": f"In the format YYYY-MM-DD, the input date {date_string} is invalid.",
				}
			)

	def decode_moodle_auth(self, auth_token):
		if auth_token == None:
			raise ValueError(
				{
					"code": "no-auth-token",
					"message": f"The authorization token is missing.",
				}
			)
		elif not auth_token.count(self.sep_char) == 1:
			raise ValueError(
				{
					"code": "invalid-auth-token",
					"message": f"In the format _{self.sep_char}_, the input auth token {auth_token} is invalid.",
				}
			)
		username, password = auth_token.split(self.sep_char)
		username = "".join(chr(int(byte)) for byte in username.split(":"))
		password = "".join(chr(int(byte)) for byte in password.split(":"))
		return username, password

	def validate_email(self, email):
		if(re.search(self.email_regex, email)):
			return email
		else:
			raise ValueError(
				{
					"code": "invalid-email-format",
					"message": f"In the format {self.email_regex}, the input {email} is invalid.",
				}
			)


class Moodle(object):
	username = "<username>"
	password = "<password>"
	login_url = "https://learn.iiitb.net/login/index.php"
	day_url = "https://learn.iiitb.net/calendar/view.php?view=day&time="
	month_url = "https://learn.iiitb.net/calendar/view.php?view=month&time="
	fake_moodle_brief_format = {
		"title": "People who have submitted their answers separately opens",
		"url": "https://learn.iiitb.net/mod/choice/view.php?id=1920",
	}

	fake_moodle_in_depth_format = {
		"title": "Hands on - 2 is due",
		"deadline": "12:00 AM",
		"course": "T2-20-EG 301 / Operating Systems",
		"url": "https://learn.iiitb.net/mod/assign/view.php?id=1759",
	}

	def __init__(self, params):
		super(Moodle, self).__init__()
		self.username = params.get("username")
		self.password = params.get("password")
		self.from_date = params.get("from_date")
		self.to_date = params.get("to_date")
		self.in_depth = params.get("in_depth")
		self.mock = params.get("mock")

	def verify_credential(self):
		with requests.session() as sess:
			login_form = sess.get(Moodle.login_url, verify=False)
			login_soup = BeautifulSoup(login_form.text, "html.parser")
			login_token = login_soup.find("input", {"name": "logintoken"}).get("value")
			data = {
				"logintoken": login_token,
				"username": self.username,
				"password": self.password,
			}
			login_attempt = sess.post(Moodle.login_url, data=data, verify=False)
			login_attempt_soup = BeautifulSoup(login_attempt.text, "html.parser")
			login_error_message = login_attempt_soup.find(
				"a", {"id": "loginerrormessage"}
			)
			if login_error_message:
				return False
			else:
				return True

	def scrape_calendar(self):
		events = {"id": 0, "data": {}}
		params = {
		"from_date": self.from_date,
		"to_date": self.to_date,
		"in_depth": self.in_depth,
		"mock": self.mock,
		}
		dt_util = DateTimeUtil(params)
		if self.mock:
			if self.in_depth:
				for epoch in dt_util.from_to_epochs:
					events["data"][epoch] = [
						Moodle.fake_moodle_in_depth_format for _ in range(randint(1, 3))
					]
			else:
				for epoch in dt_util.from_to_epochs:
					events["data"][epoch] = [
						Moodle.fake_moodle_brief_format for _ in range(randint(1, 3))
					]
		else:
			with requests.session() as sess:
				login_form = sess.get(Moodle.login_url, verify=False)
				login_soup = BeautifulSoup(login_form.text, "html.parser")
				login_token = login_soup.find("input", {"name": "logintoken"}).get(
					"value"
				)
				data = {
					"logintoken": login_token,
					"username": self.username,
					"password": self.password,
				}
				login_attempt = sess.post(Moodle.login_url, data=data, verify=False)
				login_attempt_soup = BeautifulSoup(login_attempt.text, "html.parser")
				login_error_message = login_attempt_soup.find(
					"a", {"id": "loginerrormessage"}
				)
				if login_error_message:
					raise ValueError(
						{
							"code": "incorrect-credential",
							"message": f"The username or password is incorrect.",
						}
					)
				else:
					if self.in_depth:
						for epoch in dt_util.from_to_epochs:
							calendar = sess.get(Moodle.day_url + str(epoch))
							calendar_soup = BeautifulSoup(calendar.text, "html.parser")
							calendar_table = calendar_soup.find(
								"div", {"class": "eventlist"}
							).find_all("div", {"data-type": "event"})
							events["data"][epoch] = []
							for event in calendar_table:
								title = (
									event.find("div", {"class": "box"})
									.find("h3", {"class": "name"})
									.get_text()
								)
								description = event.find(
									"div", {"class": "description"}
								).find_all("div", {"class": "row"})
								deadline = (
									description[0]
									.find("span", {"class": "dimmed_text"})
									.get_text()
									.split(",")[-1]
									.lstrip()
								)
								course = description[-1].find("a").get_text()
								link = (
									event.find("div", {"class": "card-footer"})
									.find("a", {"class": "card-link"})
									.get("href")
								)
								events["data"][epoch].append(
									{
										"title": title,
										"deadline": deadline,
										"course": course,
										"url": link,
									}
								)
					else:
						for epoch in dt_util.from_to_epochs:
							calendar = sess.get(Moodle.month_url + str(epoch))
							calendar_soup = BeautifulSoup(calendar.text, "html.parser")
							calendar_table = (
								calendar_soup.find("table", {"class": "calendarmonth"})
								.find("tbody")
								.find_all("tr")
							)
							for week in calendar_table:
								for week_day in week.find_all("td"):
									timestamp = week_day.get("data-day-timestamp")
									if timestamp and (
										dt_util.from_date_epoch
										<= int(timestamp)
										<= dt_util.to_date_epoch
									):
										day_content = week_day.find(
											"div", attrs={"data-region": "day-content"}
										)
										if day_content:
											events["data"][timestamp] = []
											for event in day_content.find_all("a"):
												events["data"][timestamp].append(
													{
														"title": event.get("title"),
														"url": event.get("href"),
													}
												)
		return events


class StudentDB(object):
	def __init__(self, params):
		super(StudentDB, self).__init__()
		self.email = params.get("email")
		database_path = params.get("database_path", current_dir_path+"/student.json")
		try:
			with open(database_path, "r") as file:
				self.database = json.load(file)
		except FileNotFoundError as e:
			self.database = {}

	def exist(self):
		return self.email in self.database

	def getData(self):
		data = self.database.get(self.email)
		if data != None:
			return data
		else:
			raise ValueError(
					{
						"code": "email-does-not-exist",
						"message": f"The email specified does not exist in the database.",
					}
				)


class FoodmenuDB(object):
	def __init__(self, params):
		super(FoodmenuDB, self).__init__()
		self.from_date = params.get("from_date")
		self.to_date = params.get("to_date")
		self.in_depth = True
		self.mock = params.get("mock")
		self.empty_menu = {
			"breakfast": [],
			"lunch": [],
			"snacks": [],
			"dinner": []
		}
		database_path = params.get("database_path", current_dir_path+"/foodmenu.json")
		try:
			with open(database_path, "r") as file:
				self.database = json.load(file)
		except FileNotFoundError as e:
			self.database = {}

	def getData(self):
		params = {
			"from_date": self.from_date,
			"to_date": self.to_date,
			"in_depth": self.in_depth,
			"mock": self.mock,
		}
		dt_util = DateTimeUtil(params)
		foodmenu_data = {}
		for epoch in dt_util.from_to_epochs:
			date_string = str(datetime.datetime.fromtimestamp(epoch).date())
			foodmenu_data[date_string] = self.database.get(date_string, self.empty_menu)
		return foodmenu_data

class EightBitDB(object):
	def __init__(self, params):
		super(EightBitDB, self).__init__()
		self.recent = params.get("recent")
		self.all = params.get("all")
		database_path = params.get("database_path", current_dir_path+"/eightbit.json")
		try:
			with open(database_path, "r") as file:
				self.database = json.load(file)
		except FileNotFoundError as e:
			self.database = []

	def getData(self):
		if(self.recent):
			magazine_data = self.database[-5:]
			return magazine_data
		if(self.all):
			magazine_data = self.database
			return magazine_data			
		return self.database

app = flask.Flask(__name__)

@app.route("/", methods=["GET"])
def welcome():
	hour = DateTimeUtil.date_time.hour
	if hour < 12:
		greeting = "Good Morning!"
	elif hour < 17:
		greeting = "Good Afternoon!"
	else:
		greeting = "Good Evening!"
	return flask.jsonify(greeting), 200

@app.route("/moodle/verify/", methods=["GET"])
def moodle_verify_credential():
	auth_token = flask.request.args.get("auth_token", type=str, default=None)
	req_arg_parser = RequestArgParser()
	username, password = req_arg_parser.decode_moodle_auth(auth_token)
	params = {
		"username": username,
		"password": password,
	}
	moodle = Moodle(params)
	is_verified = moodle.verify_credential()
	return flask.jsonify(is_verified), 200


@app.route("/moodle/events/", methods=["GET"])
def moodle_scrape_calendar():
	auth_token = flask.request.args.get("auth_token", type=str, default=None)
	from_date = flask.request.args.get("from", type=str, default=None)
	to_date = flask.request.args.get("to", type=str, default=None)
	in_depth = flask.request.args.get("in_depth", type=bool, default=False)
	mock = flask.request.args.get("mock", type=bool, default=False)
	try:
		req_arg_parser = RequestArgParser()
		if mock:
			username = Moodle.username
			password = Moodle.password
			if in_depth:
				from_date = req_arg_parser.format_date("2021-05-20")
				to_date = req_arg_parser.format_date("2021-05-21")
			else:
				from_date = req_arg_parser.format_date("2021-05-01")
				to_date = req_arg_parser.format_date("2021-06-30")
		else:
			username, password = req_arg_parser.decode_moodle_auth(auth_token)
			from_date = req_arg_parser.format_date(from_date)
			to_date = req_arg_parser.format_date(to_date)
		params = {
			"username": username,
			"password": password,
			"from_date": from_date,
			"to_date": to_date,
			"in_depth": in_depth,
			"mock": mock,
		}
		moodle = Moodle(params)
		event_data = moodle.scrape_calendar()
		return flask.jsonify(event_data), 200
	except ValueError as error:
		return flask.jsonify(error.args[0]), 400

@app.route("/student/exist/", methods=["GET"])
def student_data_exist():
	try:
		req_arg_parser = RequestArgParser()
		email = flask.request.args.get("email", type=str, default=None)
		email = req_arg_parser.validate_email(email)
		params = {
			"email": email,
		}
		studentdb = StudentDB(params)
		does_exist = studentdb.exist()
		return flask.jsonify(does_exist), 200
	except ValueError as error:
		return flask.jsonify(error.args[0]), 400

@app.route("/student/data/", methods=["GET"])
def student_data_retrieve():
	try:
		req_arg_parser = RequestArgParser()
		email = flask.request.args.get("email", type=str, default=None)
		email = req_arg_parser.validate_email(email)
		params = {
			"email": email,
		}
		studentdb = StudentDB(params)
		student_data = studentdb.getData()
		return flask.jsonify(student_data), 200
	except ValueError as error:
		return flask.jsonify(error.args[0]), 400

@app.route("/foodmenu/data/", methods=["GET"])
def foodmenu_data_retrieve():
	from_date = flask.request.args.get("from", type=str, default=None)
	to_date = flask.request.args.get("to", type=str, default=None)
	mock = flask.request.args.get("mock", type=bool, default=False)
	try:
		req_arg_parser = RequestArgParser()
		if mock:
			from_date = req_arg_parser.format_date("2021-07-04")
			to_date = req_arg_parser.format_date("2021-07-08")
		else:
			from_date = req_arg_parser.format_date(from_date)
			to_date = req_arg_parser.format_date(to_date)
		params = {
			"from_date": from_date,
			"to_date": to_date,
			"mock": mock,
		}
		foodmenudb = FoodmenuDB(params)
		foodmenu_data = foodmenudb.getData()
		return flask.jsonify(foodmenu_data), 200
	except ValueError as error:
		return flask.jsonify(error.args[0]), 400

@app.route("/eightbit/data/", methods=["GET"])
def eight_data_retrieve():
	try:
		req_arg_parser = RequestArgParser()
		recent = flask.request.args.get("recent", type=bool, default=False)
		full = flask.request.args.get("full", type=bool, default=False)
		params = {
			"recent": recent,
			"full": full,
		}
		eightbitdb = EightBitDB(params)
		eightbit_data = eightbitdb.getData()
		return flask.jsonify(eightbit_data), 200
	except ValueError as error:
		return flask.jsonify(error.args[0]), 400

def main():
	username = "<username>"
	password = "<password>"
	in_depth = False
	mock = True
	req_arg_parser = RequestArgParser()
	if in_depth:
		from_date = req_arg_parser.format_date("2021-05-05")
		to_date = req_arg_parser.format_date("2021-05-06")
	else:
		from_date = req_arg_parser.format_date("2021-04-17")
		to_date = req_arg_parser.format_date("2021-08-18")
	params = {
		"username": username,
		"password": password,
		"from_date": from_date,
		"to_date": to_date,
		"in_depth": in_depth,
		"mock": mock,
		"email": "kpiiitb@gmail.com",
		"database_path": "student.json"
	}
	# moodle = Moodle(params)
	## moodle-verify
	# json = moodle.verify_credential()
	## moodle-scrape-calendar
	# json = moodle.scrape_calendar()
	# print(json)
	# studentdb = StudentDB(params)
	# json = studentdb.exist()
	# json = studentdb.getData()
	foodmenudb = FoodmenuDB(params)
	json = foodmenudb.getData()
	print(json)


if __name__ == "__main__":
	main()
