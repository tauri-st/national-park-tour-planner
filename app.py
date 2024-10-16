from flask import Flask, render_template, request
import logging
from datetime import datetime
from langchain_openai import OpenAI
#Allows to call an agent into the code
from langchain.agents import create_json_chat_agent, AgentExecutor
#These two APIs will be used with Wikipedia built-in tool which makes it easy to access and parse data from Wikipedia
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
#Implements the Runnable Interface and wraps a function within code to let an agent easily work with it
from langchain.tools import StructuredTool
#gives access to LangChain Hub community contributed resources
from langchain import hub

# app will run at: http://127.0.0.1:5000/

#* Create instance of OpenAI class
llm = OpenAI(
   max_tokens = -1
)

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

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
  # create comma seperated lists for all prompts with multi-select to collect all values
  # this is based on the "name" property in the form inputs in plan-trip.html
  traveling_with_list = ",".join(request.form.getlist("traveling-with"))
  lodging_list = ", ".join(request.form.getlist("lodging"))
  adventure_list = ", ".join(request.form.getlist("adventure"))

  #log.info(cleaned_form_data)
  prompt = build_new_trip_prompt_template()

  #* Build LangChain
  chain = prompt | llm | parser

  # create a dictionary containing cleaned form data
  output = chain.invoke({
    "location": request.form["location-search"],
    "trip_start": request.form["trip-start"],
    "trip_end": request.form["trip-end"],
    "traveling_with": traveling_with_list,
    "lodging": lodging_list,
    "adventure": adventure_list,
    "trip_name": request.form["trip-name"]
  })

  # Write a chain that uses the new prompt template for weather
  prompt2 = build_weather_prompt_template()

  chain2 = prompt2 | llm | parser

  #* Invoke the chain and get the response then send it to the view file
  # You can only send a string to a model as input, so you need to convert the output back to a string
  output_str = json.dumps(output)
  output2 = chain2.invoke({"input": output_str})

  log.info(output2)
  
  # pass context dictionary which then can be referenced using variable names to output dynamic data.
  # Add a second argument to render_template() as a key / value pair, with the key being output and the value being output, which is the JSON-parsed response from the model:
  return render_template("view-trip.html", output = output2)

# inform the LLM what type of response we're looking for and how we want the response to be formatted
# user's form responses will be used as arguments
def generate_trip_input(location, trip_start, trip_end, traveling_with, lodging, adventure):
  """
  Generates a structured input string for the trip planning agent.
  """
  return f"""
    Create an itinerary for a trip to {location}.
    The trip starts on: {trip_start}
    The trip ends on: {trip_end}
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
    
# Run the flask server
if __name__ == "__main__":#
    app.run()
