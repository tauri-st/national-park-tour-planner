from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from langchain_core.prompts import PromptTemplate

# app will run at: http://127.0.0.1:5000/

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

# Write a prompt template
# First we temporarily use placeholders,
# but this will eventually accept user form data
def build_new_trip_prompt(form_data):
   #Instantiate the class
   prompt_template = PromptTemplate.from_template(
       "Create a trip for me by the name of {trip_name}. It will be to {location} between the dates of {trip_start} and {trip_end}. I will be traveling with {traveling_with_list}. I prefer housing in the form of {lodging_list}. I prefer these types of adventures: {adventure_list}"                                          
  )

# Initialize the Flask application
app = Flask(__name__)

# Define the route for the home page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")
  
# Define the route for the plan trip page
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
  return render_template("plan-trip.html")

# Define the route for view trip page with the generated trip itinerary
@app.route("/view_trip", methods=["POST"])
def view_trip():
  # log the request form object
  log.info(request.form)
  # create comma seperated lists for all prompts with multi-select to collect all values
  # this is based on the "name" property in the form inputs in plan-trip.html
  traveling_with_list = ",".join(request.form.getlist("traveling-with"))
  lodging_list = ", ".join(request.form.getlist("lodging"))
  adventure_list = ", ".join(request.form.getlist("adventure"))
  # create a dictionary containing cleaned form data
  cleaned_form_data = {
        "location": request.form["location-search"],
        "trip_start": request.form["trip-start"],
        "trip_end": request.form["trip-end"],
        "traveling_with_list": traveling_with_list,
        "lodging_list": lodging_list,
        "adventure_list": adventure_list,
        "trip_name": request.form["trip-name"]
  }
  # log.info(cleaned_form_data)
  return render_template("view-trip.html")
    
# Run the flask server
if __name__ == "__main__":#
    app.run()
