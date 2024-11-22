# redirect used in routing the various pages of your application
# url_for used to define the URLs used in routing
# flash used to show messages to the visitor
from flask import Flask, flash, render_template, request, redirect, url_for, send_file
# handles the creation of accounts and the ability to log in and out
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import logging
# Handles the stream of data for the PDF and places it temporarily into memory
import io
from datetime import datetime
from langchain_openai import ChatOpenAI

# create a formatted PDF of the itinerary:
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# make a request to a web page
import requests
import json
# call an agent into the code
# tool makes the custom tools you build available to the agent.
from langchain.agents import create_json_chat_agent, AgentExecutor, tool
# compare two strings to be sure they match
from fuzzywuzzy import fuzz, process
# access environmental variables to store the API key safely
import os

# These two APIs will be used with Wikipedia built-in tool which makes it easy to access and parse data from Wikipedia
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

# Implements the Runnable Interface and wraps a function within code to let an agent easily work with it
from langchain.tools import StructuredTool
# gives access to LangChain Hub community contributed resources
from langchain import hub
from flask_sqlalchemy import SQLAlchemy

# app will run at: http://127.0.0.1:5000/

#* Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

#* Initialize the Flask application
app = Flask(__name__)

#* Create instance of OpenAI class
llm = ChatOpenAI(
  model="gpt-3.5-turbo",
  temperature=0.5,
  max_tokens=4000
)

#* Set up the database
# database accessed at sqlite:///nature_nook.db
# secret key to manage user sessions
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", 'default-secret-key')
# SQLALCHEMY_DATABASE_URI sets a database connection URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nature_nook.db'
# when set to False, interactions with the database to add, update, and delete are not recorded. This reduces the overhead
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#* Create the database object
db = SQLAlchemy(app)
# create an instance of the LoginManager class
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

#* Define the Park model
class Park(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  code = db.Column(db.String(10), unique=True, nullable=False)

#* Define the User model
class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(150), unique=True, nullable=False)
  password = db.Column(db.String(150), nullable=False)

#* Define the Trip model for the database
class Trip(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  trip_name = db.Column(db.String(150), nullable=False)
  location = db.Column(db.String(150), nullable=False)
  trip_start = db.Column(db.Date, nullable=False)
  trip_end = db.Column(db.Date, nullable=False)
  traveling_with = db.Column(db.String(150), nullable=False)
  lodging = db.Column(db.String(150), nullable=False)
  adventure = db.Column(db.String(150), nullable=False)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  typical_weather = db.Column(db.String(150), nullable=True)
  itinerary = db.Column(db.Text, nullable=True)
  important_things_to_know = db.Column(db.Text, nullable=True)
 
  user = db.relationship('User', backref=db.backref('trips', lazy=True))

#* Authenticate user as they travel between pages
# Flask-Login will authenticate the session token repeatedly as the visitor navigates to different pages and interacts with the database
# this function gets the user’s id from the User table and returns it
@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))

#* Define the /login route
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:
      login_user(user)
      return redirect(url_for('index'))
    else:
      flash('Login Unsuccessful. Please check username and password', 'danger')
  return render_template('login.html')

#* Define the /logout route
@app.route('/logout')
# decorator is added to check that the user is logged in and is a valid user
@login_required
# If so, the logout function is run, logging the user out and routing to the login page
def logout():
   logout_user()
   return redirect(url_for('login'))

#* Define the /signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    flash('Account created!', 'success')
    return redirect(url_for('login'))
  return render_template('signup.html')

#* Define the route for the home page
@app.route("/", methods=["GET"])
@login_required
def index():
    """Renders the main page."""
    # Pass the user to each page in order to validate their authorization
    return render_template("index.html", user=current_user)

#* Define the route for the plan trip page
# If a trip exists, the fields will be pre-filled with the choices from the previously planned trip.
@app.route("/plan_trip", methods=["GET", "POST"])
@login_required
def plan_trip():
  """Renders the trip planning page."""
  trip_id = request.args.get('trip_id')
  trip = None
  # if a trip_id is available, query the Trip table using the trip ID and assign the data about the trip to the variable trip
  if trip_id:
    trip = Trip.query.get_or_404(trip_id)
  #query the database to generate a list of parks and pass that list to the view file
  parks = Park.query.all()
  return render_template("plan-trip.html", parks=parks, user=current_user, trip=trip)

#* Fetch list of parks
def get_parks():
  """Fetches the entire list of national parks from the NPS API."""
  url = "https://developer.nps.gov/api/v1/parks"
  params = {
    "api_key": os.environ.get("NPS_API_KEY"),
    "limit": 75, # Adjust this number based on the API's limit
    "start": 0
  }
  parks = []
  while True:
    response = requests.get(url, params=params)
    if response.status_code == 200:
      data = response.json()
      # extend adds name and code to the list
      parks.extend([{"name": park["fullName"], "code": park["parkCode"]} for park in data["data"]])
      if len(data["data"]) < params["limit"]:
        break
      params["start"] += params["limit"]
    else:
      break
  return parks

#* Define the route for view trip page with the generated trip itinerary
# For refactor: no invoking the chain (since we’re using an agent instead of a chain.)
@app.route("/view_trip", methods=["POST"])
@login_required
def view_trip():
  """Handles the form submission to view the generated trip itinerary."""
  # Check for existing trip id in form data
  trip_id = request.form.get('trip_id')
  # Extract form data
  location = request.form["location-search"]
  trip_start_str = request.form["trip-start"]
  trip_end_str = request.form["trip-end"]
  trip_start = datetime.strptime(trip_start_str, '%Y-%m-%d').date()
  trip_end = datetime.strptime(trip_end_str, '%Y-%m-%d').date()
  traveling_with = ", ".join(request.form.getlist("traveling-with"))
  lodging = ", ".join(request.form.getlist("lodging"))
  adventure = ", ".join(request.form.getlist("adventure"))
  trip_name = request.form["trip-name"]

  # Call generate function and create the input string with the user's unique trip information
  input_data = generate_trip_input(trip_name, location, trip_start_str, trip_end_str, traveling_with, lodging, adventure)
  print('input_data: \n', input_data, '\n')

  # Create a tool for the agent to use that utilizes Wikipedia's run function
  wikipedia_tool = create_wikipedia_tool()

  # Define and register a custom tool for retrieving data from the National Park Service API
  nps_tool = create_nps_tool()

  # Pull a tool prompt template from the hub. View the template at https://smith.langchain.com/hub/hwchase17/react-chat-json
  prompt = hub.pull("hwchase17/react-chat-json")

  # Create our agent that will utilize tools and return JSON
  agent = create_json_chat_agent(llm=llm, tools=[wikipedia_tool, nps_tool], prompt=prompt)

  # Create a runnable instance of the agent
  # Included in the AgentExecutor you’ll add the ability to see an error if the LLM isn’t able to parse the response from different inputs: handle_parsing_errors(https://python.langchain.com/v0.1/docs/modules/agents/how_to/handle_parsing_errors/). 
  # You’ll see the error message as part of the output in the command line.
  agent_executor = AgentExecutor(agent=agent, tools=[wikipedia_tool, nps_tool], verbose=True, handle_parsing_errors="The output from the LLM could not be parsed or is incomplete.")
 
  # Invoke the agent with the input data
  response = agent_executor.invoke({"input": input_data})

  output = response["output"]

  # Query the database for the existing trip or create a new one
  existing_trip = Trip.query.get(trip_id) if trip_id else None
 
  if existing_trip:
    # Update the existing trip
    existing_trip.location = location
    existing_trip.trip_start = trip_start
    existing_trip.trip_end = trip_end
    existing_trip.traveling_with = traveling_with
    existing_trip.lodging = lodging
    existing_trip.adventure = adventure
    existing_trip.typical_weather = output["typical_weather"]
    existing_trip.itinerary = json.dumps(output["itinerary"])
    existing_trip.important_things_to_know = output["important_things_to_know"]
    db.session.commit()
    trip = existing_trip
  else:
    # Create a new trip to be added to the database
    new_trip = Trip(user_id=current_user.id, trip_name=trip_name, location=location, trip_start=trip_start,
      trip_end=trip_end, traveling_with=traveling_with, lodging=lodging, adventure=adventure,
      typical_weather=output["typical_weather"], itinerary=json.dumps(output["itinerary"]),
      important_things_to_know=output["important_things_to_know"])
    db.session.add(new_trip)
    db.session.commit()
    trip = new_trip

  log.info(response["output"])
  
  return render_template("view-trip.html", output=output, user=current_user, trip_id=trip.id)

# inform the LLM what type of response we're looking for and how we want the response to be formatted
# user's form responses will be used as arguments
def generate_trip_input(trip_name, location, trip_start_str, trip_end_str, traveling_with, lodging, adventure):
  """
  Generates a structured input string for the trip planning agent.
  """
  return f"""
    Create an itinerary for a trip to {location}.
    The trip starts on: {trip_start_str}
    The trip ends on: {trip_end_str}
    I will be traveling with {traveling_with}
    I would like to stay in {lodging}
    I would like to do the following activities: {adventure}
 
    Please generate a complete and detailed trip itinerary with the following JSON data structure:
 
    {{
      "trip_name": "String - Name of the trip",
      "location": "String - Location of the trip",
      "trip_start": "String - Start date of the trip",
      "trip_end": "String - End date of the trip",
      "typical_weather": "String - Description of typical weather for the trip",
      "traveling_with": "String - Description of travel companions",
      "lodging": "String - Description of lodging arrangements",
      "adventure": "String - Description of planned activities",
      "itinerary": [
        {{
          "day": "Integer - Day number",
          "date": "String - Date of this day",
          "morning": "String - Description of morning activities",
          "afternoon": "String - Description of afternoon activities",
          "evening": "String - Description of evening activities"
        }}
      ],
      "important_things_to_know": "String - Any important things to know about the park being visited."
    }}
 
    The trip should be appropriate for those listed as traveling, themed around the interests specified, and that last for the entire specified duration of the trip.
    Include realistic and varied activities for each day, considering the location, hours of operation, and typical weather.
    Make sure all fields are filled with appropriate and engaging content.
    Include descriptive information about each day's activities and destination.
    Respond only with a valid parseable JSON object representing the itinerary.
    """

#* Allow the agent to use the WikipediaQueryRun tool
def create_wikipedia_tool():
  """
  Creates a built-in langchain tool for querying Wikipedia.
  """
  wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
  return StructuredTool.from_function(
    func=wikipedia.run,
    name="Wikipedia",
    description="Useful for Wikipedia searches about national parks."
  )

def create_nps_tool():
  """
  Creates a custom tool for retrieving data from the National Park Service (NPS) API.
  """
  base_url = "https://developer.nps.gov/api/v1"
  api_key = os.environ.get("NPS_API_KEY")

  def fetch_data(endpoint, params):
    """
    Fetches data from the NPS API given an endpoint and parameters.
    """
    url = f"{base_url}/{endpoint}"
    params['api_key'] = api_key
    response = requests.get(url, params=params)
    if response.status_code == 200:
      return response.json()
    return {"error": f"Failed to fetch data from {endpoint}, status code: {response.status_code}"}
  print(api_key)

  # takes a park name as an argument and uses the fetch_data function to make an API call
  def search_parks_by_name(park_name):
    """
    Searches for parks by name.
    """
    return fetch_data("parks", {"q": park_name}).get("data", [])

  # uses fuzzy search to search the list of parks returned by the search_parks_by_name() function and identify the one that most closely matches the park name
  def find_best_matching_park(park_name, parks):
    """
    Finds the best matching park using fuzzy search.
    """
    park_names = [park['fullName'] for park in parks]
    best_match_name, _ = process.extractOne(park_name, park_names, scorer=fuzz.partial_ratio)
    for park in parks:
      if park['fullName'] == best_match_name:
        return park
    return None
    
  def find_related_data_for_park(park):
    """
    Finds related data for a park from various NPS API endpoints.
    """
    park_code = park["parkCode"]
    endpoints = [
      "activities/parks", "thingstodo" 
      # Add more endpoints as needed. See https://www.nps.gov/subjects/developer/api-documentation.htm.
    ]
    related_data = {endpoint: fetch_data(endpoint, {"parkCode": park_code}) for endpoint in endpoints}
    return related_data
    
  @tool
  def search_park_and_related_data(input: str) -> str:
    """
    Searches for a park and finds related data.
    """
    # strip method removes leading and trailing white spaces
    park_name = input.strip()
    parks = search_parks_by_name(park_name)
    if parks:
      best_matching_park = find_best_matching_park(park_name, parks)
      if best_matching_park:
        combined_data = {
          "park": best_matching_park,
          "related_data": find_related_data_for_park(best_matching_park)
        }
      else:
        combined_data = {"error": f"Exact park named '{park_name}' not found in search results."}
    else:
      combined_data = {"error": f"Park named '{park_name}' not found."}
    return json.dumps(combined_data, indent=4)
  
  return search_park_and_related_data

@app.route("/download_pdf", methods=["POST"])
@login_required
def download_pdf():
  """Handles the PDF download of the generated trip itinerary."""
  #* Function scoped variables
  #holds the jsonified trip itinerary details
  output = request.json

  #work with streaming content. 
  # io, or i/o, stands for input and output. 
  # Input refers to the process of reading data from external sources, keeping the bytes received in an in-memory buffer. 
  # Output refers to the process of writing data to external destinations.
  buffer = io.BytesIO()
  # a class in the Platypus library that can be used to create PDF documents
  doc = SimpleDocTemplate(buffer, pagesize=letter)
  # used to define the layout within the PDF being created
  styles = getSampleStyleSheet()
 
  # used to build the structure and data that will be contained within the PDF.
  elements = []

  #* Create formatting for the PDF
  elements.append(Paragraph(f"<b>Trip Name:</b> {output['trip_name']}", styles['Normal']))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"<b>Location:</b> {output['location']}", styles['Normal']))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"<b>Dates:</b> {output['trip_start']} - {output['trip_end']}", styles['Normal']))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"<b>Typical Weather:</b> {output['typical_weather']}", styles['Normal']))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"<b>Traveling With:</b> {output['traveling_with']}", styles['Normal']))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"<b>Lodging:</b> {output['lodging']}", styles['Normal']))
  elements.append(Spacer(1, 12))
  elements.append(Paragraph(f"<b>Activities:</b> {output['adventure']}", styles['Normal']))
  elements.append(Spacer(1, 24))
 
  elements.append(Paragraph("<b>Itinerary:</b>", styles['Normal']))
  elements.append(Spacer(1, 12))
  for day in output['itinerary']:
    elements.append(Paragraph(f"<b>Day {day['day']}:</b> {day['date']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Morning:</b> {day['morning']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Afternoon:</b> {day['afternoon']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Evening:</b> {day['evening']}", styles['Normal']))
    elements.append(Spacer(1, 24))
 
  elements.append(Paragraph(f"<b>Important Things to Know:</b> {output['important_things_to_know']}", styles['Normal']))

  #* Create the PDF
  doc.build(elements)
  
  # sets the reference point from where the read of the file will start to the beginning
  buffer.seek(0)
  # called to return the file when the user clicks the “Export trip” button
  return send_file(buffer, as_attachment=True, download_name="itinerary.pdf", mimetype='application/pdf')

#* Route to fetch all trips added by user
# query the Trip table in the database, filtering by the current user’s ID, to get all the saved trips and assign them to a variable
@app.route("/my_trips", methods=["GET"])
@login_required
def my_trips():
  """Renders the saved trips page."""
  trips = Trip.query.filter_by(user_id=current_user.id).all()
  return render_template("my-trips.html", trips=trips, user=current_user)

#* Route to view a particular trip from saved trips
# Query the Trip database using the trip_id and save the response to a variable named trip. Create a dictionary named output that holds the data for the trip.
# The visitor will see the same view-trip page you’ve seen before with the specific trip associated with the trip_id
@app.route("/view_trip/<int:trip_id>", methods=["GET"])
@login_required
def view_saved_trip(trip_id):
  """Renders the detailed view for a saved trip."""
  trip = Trip.query.get_or_404(trip_id)
  output = {
    "trip_name": trip.trip_name,
    "location": trip.location,
    "trip_start": trip.trip_start,
    "trip_end": trip.trip_end,
    "typical_weather": trip.typical_weather,
    "traveling_with": trip.traveling_with,
    "lodging": trip.lodging,
    "adventure": trip.adventure,
    "itinerary": json.loads(trip.itinerary) if trip.itinerary else [],
    "important_things_to_know": trip.important_things_to_know
  }
  return render_template("view-trip.html", output=output, user=current_user, trip_id=trip.id)

@app.route("/delete_trip/<int:trip_id>", methods=["POST"])
@login_required
def delete_trip(trip_id):
  """Handles the deletion of a trip."""
  trip = Trip.query.get_or_404(trip_id)
  # Make sure user has permission to delete the trip
  if trip.user_id != current_user.id:
    flash("You do not have permission to delete this trip.", "danger")
    return redirect(url_for('my_trips'))
  
  db.session.delete(trip)
  db.session.commit()
  flash("Trip deleted successfully.", "success")
  log.info("Trip deleted: %s", flash)
  return redirect(url_for('my_trips'))

#* Create a Flask CLI command for initializing the database
# Run "flask init-db" from the command line to initialize the database
@app.cli.command("init-db")
def init_db():
  db.create_all()
  parks = get_parks()
  for park in parks:
    # Check if park is already in database
    existing_park = Park.query.filter_by(code=park["code"]).first()
    if not existing_park:
      new_park = Park(name=park["name"], code=park["code"])
      db.session.add(new_park)
  db.session.commit()
  print("Database initialized!")

#* Run the flask server
if __name__ == "__main__":#
  app.run()
