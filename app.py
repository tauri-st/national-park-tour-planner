from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import OpenAI

# app will run at: http://127.0.0.1:5000/

#* Create instance of OpenAI class
llm = OpenAI(
   max_tokens = -1
)

#* Create instance of JsonOutputParser
parser = JsonOutputParser()

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

# Initialize the Flask application
app = Flask(__name__)

#* Write a prompt template
# First we temporarily use placeholders,
# but this will eventually accept user form data
def build_new_trip_prompt_template():
  #* Declare example dictionary to convert to "few-shot" prompting
  #response has to be in JSON format so that we can interact with the values and in this case display the data on the page
  examples = [
    {
      "prompt":
      """
      Create a trip for me to Yosemite National Park between the dates of 2024-10-07 and 2024-10-09. I will be traveling solo. I prefer housing in the form of campsites. I prefer these types of adventures: hiking, swimming. Create a daily itinerary for this trip using this information.
      """,
      "response":
      """
      {{"trip_name":"My awesome trip to Yosemite 2024 woohoooo","location":"Yosemite National Park","trip_start":"2024-10-07","trip_end":"2024-10-09","num_days":"3","traveling_with":"solo","lodging":"campsites","adventure":"hiking, swimming","itinerary":[{{"day":"1","date":"2024-10-07","morning":"Arrive at Yosemite National Park","afternoon":"Set up campsite at North Pines Campground","evening":"Explore the campground and have a family campfire dinner"}},{{"day":"2","date":"2024-10-08","morning":"Guided tour of Yosemite Valley (includes stops at El Capitan, Bridalveil Fall, Half Dome)","afternoon":"Picnic lunch in the Valley","evening":"Relax at the campsite, storytelling around the campfire"}},{{"day":"3","date":"2024-10-09","morning":"Hike to Mirror Lake (easy hike)","afternoon":"Swimming at Mirror Lake","evening":"Dinner at the campsite, stargazing"}}]}}
      """
    },
    {
      "prompt":
      """
      Create a trip for me to Grand Canyon National Park between the dates of 2024-10-07 and 2024-10-09. I will be traveling in a group. I prefer housing in the form of hotels, lodges. I prefer these types of adventures: tours, climbing. Create a daily itinerary for this trip using this information.
      """,
      "response":
      """
      {{"trip_name":"My awesome trip to the Grand Canyon ooooohhhh","location":"Grand Canyon National Park","trip_start":"2024-05-23","trip_end":"2024-05-25","num_days":"3","traveling_with":"in a group","lodging":"hotels, lodges","adventure":"tours, climbing","itinerary":[{{"day":"1","date":"2024-10-07","morning":"Arrive at Grand Canyon National Park, check into your lodge (e.g., El Tovar Hotel or Bright Angel Lodge)","afternoon":"Guided South Rim bus tour (stops at Desert View Watchtower, Yavapai Point, and Grandview Point)","evening":"Enjoy a sunset view from Mather Point and dinner at the lodge restaurant"}},{{"day":"2","date":"2024-10-08","morning":"Guided hike/climbing experience at Grand Canyon's Rim-to-Rim trail (shorter section, suitable for a day's climb)","afternoon":"Scenic lunch at a viewpoint along the South Rim trail","evening":"Attend a ranger-led stargazing session (if available) or relax at the lodge with evening drinks by the fire"}},{{"day":"3","date":"2024-10-09","morning":"Helicopter tour over the Grand Canyon for breathtaking aerial views","afternoon":"Lunch at Grand Canyon Village, last-minute shopping for souvenirs","evening":"Depart from Grand Canyon National Park"}}]}}
      """
    },
    {
      "prompt":
      """
      Create a trip for me to Cleveland National Forest between the dates of 2024-10-10 and 2024-10-12. I will be traveling with a partner, kids. I prefer housing in the form of hotels, lodges. I prefer these types of adventures: tours, climbing. Create a daily itinerary for this trip using this information.
      """,
      "response":
      """
      {{"trip_name":"My romantic trip to Cleveland National Forest","location":"Cleveland National Forest","trip_start":"2024-10-10","trip_end":"2024-10-12","num_days":"3","traveling_with":"with a partner, with kids","lodging":"hotels, lodges","adventure":"hiking, swimming","itinerary":[{{"day":"1","date":"2024-10-10","morning":"Arrive at Cleveland National Forest. Check in at a cozy bed & breakfast in or around Julian (e.g., Pine Hills Lodge or Julian Lodge).","afternoon":"Explore the scenic Santa Ysabel Preserve for a family-friendly hike. The West Preserve offers a 3.5-mile loop that’s great for kids with wide trails and gentle slopes.","evening":"Return to the bed & breakfast. Enjoy a homemade dinner at the B&B or a meal at a local restaurant in Julian (ex. Jeremy's on the Hill, a farm-to-table restaurant in Julian). Finish the evening with a relaxing stroll around town."}},{{"day":"2","date":"2024-10-11","morning":"Cycle the Sunrise Highway, a scenic cycling route with stunning views of the forest and surrounding mountains. Opt for a family-friendly section from Pine Valley to Laguna Mountain, which has smoother paths suitable for kids.","afternoon":"Pack a picnic lunch and stop at Laguna Mountain Recreation Area. Afterward, explore the Big Laguna Trail with a short family hike to the lake, enjoying the serene views.","evening":"Head back to your bed & breakfast for some downtime. Enjoy a casual family dinner in Julian (ex. The Julian Grille), perhaps trying a famous Julian apple pie for dessert."}},{{"day":"3","date":"2024-10-12","morning":"Hike Cuyamaca Peak via the Lookout Fire Road trail. It’s a moderate trail, but the views from the top make it a great reward for the whole family.","afternoon":"Have lunch at a restaurant in Julian (ex. Romano's Restaurant). Explore the town, visit the local shops, or stop by the Julian Mining Company for a fun family activity like gem mining.","evening":"Depart Cleveland National Forest and head back home, or enjoy a final relaxing evening in Julian before wrapping up your trip."}}]}}
      """
    }
  ]

  #* Create a prompt template that defines the structure of the response
  example_prompt = PromptTemplate.from_template(
    template =
    """
    {prompt}\n{response}
    """
  )
  #use one of the examples to log the output
  #log.info(example_prompt.format(**examples[0]))
  
  #* Create few-shot prompt template:
  few_shot_prompt = FewShotPromptTemplate(
    examples = examples,
    example_prompt = example_prompt,
    #set to the real prompt with the user's form data included
    #it will be appnded to the end of all the example prompts to give the model context
    suffix = "This trip is to {location} between {trip_start} and {trip_end}. This person will be traveling {traveling_with} and would like to stay in {lodging}. They want to {adventure}. Create a daily itinerary for this trip using this information. You are a backend data processor that is part of our site's programmatic workflow. Output the itinerary as only JSON with no text before or after the JSON.",
    #set to inputs that will be assigned values when .format() is called
    #this input passes in the real prompt with the user's form data included
    input_variables = ["location", "trip_start", "trip_end", "traveling_with", "lodging", "adventure"],
  )

  return few_shot_prompt

  # Call format on the few_shot_prompt
  # return few_shot_prompt.format(input = "This trip is to " + form_data["location"] + " between " + form_data["trip_start"] + " and " +  form_data["trip_end"] + ". This person will be traveling " + form_data["traveling_with_list"] + " and would like to stay in " + form_data["lodging_list"] + ". They want to " + form_data["adventure_list"] + ". Create a daily itinerary for this trip using this information.")

def build_weather_prompt_template():
   # TODO: Create example prompts with a few shot template
   #* Show the model how you want it to take the trip information as an input
    # TODO: Write a chain that uses the new prompt template
   #* Show the model how to update to include weather information
    # TODO: Invoke the chain and get the response then send it to the view file
    # TODO: Update the view file to display the weather information

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
    "traveling_with_list": traveling_with_list,
    "lodging_list": lodging_list,
    "adventure_list": adventure_list,
    "trip_name": request.form["trip-name"]
  })
  
  # pass context dictionary which then can be referenced using variable names to output dynamic data.
  # Add a second argument to render_template() as a key / value pair, with the key being output and the value being output, which is the JSON-parsed response from the model:
  return render_template("view-trip.html", output = output)
    
# Run the flask server
if __name__ == "__main__":#
    app.run()
