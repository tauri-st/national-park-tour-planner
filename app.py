from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI

# app will run at: http://127.0.0.1:5000/

#* Create instance of OpenAI class
llm = OpenAI()

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

#* Write a prompt template
# First we temporarily use placeholders,
# but this will eventually accept user form data
def build_new_trip_prompt(form_data):
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
      {{"trip_name":"My awesome trip to Yosemite 2024 woohoooo","location":"Yosemite National Park","trip_start":"2024-10-07","trip_end":"2024-10-09","num_days":"3","traveling_with":"solo","lodging":"campsites","adventure":"hiking, swimming","itinerary":[{{"day":"1","date":"2024-10-07","activites":["Arrive at Yosemite National Park","Set up campsite at North Pines Campground","Explore the campground and have a family campfire dinner"]}},{{"day":"2","date":"2024-10-08","activities":["Guided tour of Yosemite Valley (includes stops at El Capitan, Bridalveil Fall, Half Dome)","Picnic lunch in the Valley","Relax at the campsite, storytelling around the campfire"]}},{{"day":"3","date":"2024-10-09","activities":["Hike to Mirror Lake (easy hike)","Swimming at Mirror Lake","Dinner at the campsite, stargazing"]}}]}}
      """
    },
    {
      "prompt":
      """
      Create a trip for me to Grand Canyon National Park between the dates of 2024-10-07 and 2024-10-09. I will be traveling in a group. I prefer housing in the form of hotels, lodges. I prefer these types of adventures: tours, climbing. Create a daily itinerary for this trip using this information.
      """,
      "response":
      """
      {{"trip_name":"My awesome trip to the Grand Canyon ooooohhhh","location":"Grand Canyon National Park","trip_start":"2024-05-23","trip_end":"2024-05-25","num_days":"3","traveling_with":"in a group","lodging":"hotels, lodges","adventure":"tours, climbing","itinerary":[{{"day":"1","date":"2024-10-07","activities":["Arrive at Grand Canyon National Park, check into your lodge (e.g., El Tovar Hotel or Bright Angel Lodge)","Guided South Rim bus tour (stops at Desert View Watchtower, Yavapai Point, and Grandview Point)","Enjoy a sunset view from Mather Point and dinner at the lodge restaurant"]}},{{"day":"2","date":"2024-10-08","activities":["Guided hike/climbing experience at Grand Canyon's Rim-to-Rim trail (shorter section, suitable for a day's climb)","Scenic lunch at a viewpoint along the South Rim trail","Attend a ranger-led stargazing session (if available) or relax at the lodge with evening drinks by the fire"]}},{{"day":"3","date":"2024-10-09","activities":["Helicopter tour over the Grand Canyon for breathtaking aerial views","Lunch at Grand Canyon Village, last-minute shopping for souvenirs","Depart from Grand Canyon National Park"]}}]}}
      """
    },
    {
      "prompt":
      """
      Create a trip for me to Cleveland National Forest between the dates of 2024-10-10 and 2024-10-12. I will be traveling with a partner, kids. I prefer housing in the form of hotels, lodges. I prefer these types of adventures: tours, climbing. Create a daily itinerary for this trip using this information.
      """,
      "response":
      """
      {{"trip_name":"My romantic trip to Cleveland National Forest","location":"Cleveland National Forest","trip_start":"2024-10-10","trip_end":"2024-10-12","num_days":"3","traveling_with":"with a partner, with kids","lodging":"hotels, lodges","adventure":"hiking, swimming","itinerary":[{{"day":"1","date":"2024-10-10","activities":["Arrive at Cleveland National Forest. Check in at a cozy bed & breakfast in or around Julian (e.g., Pine Hills Lodge or Julian Lodge).","Explore the scenic Santa Ysabel Preserve for a family-friendly hike. The West Preserve offers a 3.5-mile loop that’s great for kids with wide trails and gentle slopes.","Return to the bed & breakfast. Enjoy a homemade dinner at the B&B or a meal at a local restaurant in Julian (ex. Jeremy's on the Hill, a farm-to-table restaurant in Julian). Finish the evening with a relaxing stroll around town."]}},{{"day":"2","date":"2024-10-11","activities":["Cycle the Sunrise Highway, a scenic cycling route with stunning views of the forest and surrounding mountains. Opt for a family-friendly section from Pine Valley to Laguna Mountain, which has smoother paths suitable for kids.","Pack a picnic lunch and stop at Laguna Mountain Recreation Area. Afterward, explore the Big Laguna Trail with a short family hike to the lake, enjoying the serene views.","Head back to your bed & breakfast for some downtime. Enjoy a casual family dinner in Julian (ex. The Julian Grille), perhaps trying a famous Julian apple pie for dessert."]}},{{"day":"3","date":"2024-10-12","activities":["Hike Cuyamaca Peak via the Lookout Fire Road trail. It’s a moderate trail, but the views from the top make it a great reward for the whole family.","Have lunch at a restaurant in Julian (ex. Romano's Restaurant). Explore the town, visit the local shops, or stop by the Julian Mining Company for a fun family activity like gem mining.","Depart Cleveland National Forest and head back home, or enjoy a final relaxing evening in Julian before wrapping up your trip."]}}]}}
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
    suffix = "{input}",
    #set to inputs that will be assigned values when .format() is called
    #this input passes in the real prompt with the user's form data included
    input_variables = ["input"],
  )

  #* Call format on the few_shot_prompt
  return few_shot_prompt.format(
     input = "This trip is to " + form_data["location"] + " between " + form_data["trip_start"] + " and " +  form_data["trip_end"] + ". This person will be traveling " + form_data["traveling_with_list"] + " and would like to stay in " + form_data["lodging_list"] + ". They want to " + form_data["adventure_list"] + ". Create a daily itinerary for this trip using this information."
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
  #log.info(cleaned_form_data)
  prompt = build_new_trip_prompt(cleaned_form_data)
  #* Make a call to OpenAI, send your new prompt with examples to the model
  response = llm.invoke(prompt)
  #* Log response from the model
  log.info(response)
  log.info(prompt)
  return render_template("view-trip.html")
    
# Run the flask server
if __name__ == "__main__":#
    app.run()
