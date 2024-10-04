from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts import PromptTemplate

# app will run at: http://127.0.0.1:5000/

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

# Write a prompt template
# First we temporarily use placeholders,
# but this will eventually accept user form data
def build_new_trip_prompt(form_data):
   #declare example dictionary to convert to "few-shot" prompting
   examples = [
      {
        "prompt":
        """
        Create a trip for me to Yosemite National Park between the dates of 2024-10-07 and 2024-10-09. I will be traveling solo. I prefer housing in the form of campsites. I prefer these types of adventures: hiking, swimming. Create a daily itinerary for this trip using this information.
        """,
        "response":
        """
        Day 1: May 23, 2024 (Thursday)
        Morning: Arrive at Yosemite National Park
        Afternoon: Set up campsite at North Pines Campground
        Evening: Explore the campground and have a family campfire dinner
 
        Day 2: May 24, 2024 (Friday)
        Morning: Guided tour of Yosemite Valley (includes stops at El Capitan, Bridalveil Fall, Half Dome)
        Afternoon: Picnic lunch in the Valley
        Evening: Relax at the campsite, storytelling around the campfire
 
        Day 3: May 25, 2024 (Saturday)
        Morning: Hike to Mirror Lake (easy hike, great for kids)
        Afternoon: Swimming at Mirror Lake
        Evening: Dinner at the campsite, stargazing
        """
      },
      {
        "prompt":
        """
        Create a trip for me to Grand Canyon National Park between the dates of 2024-10-07 and 2024-10-09. I will be traveling in a group. I prefer housing in the form of hotels, lodges. I prefer these types of adventures: tours, climbing. Create a daily itinerary for this trip using this information.
        """,
        "response":
        """
        Day 1: October 7, 2024 (Monday)
        Morning: Arrive at Grand Canyon National Park, check into your lodge (e.g., El Tovar Hotel or Bright Angel Lodge)
        Afternoon: Guided South Rim bus tour (stops at Desert View Watchtower, Yavapai Point, and Grandview Point)
        Evening: Enjoy a sunset view from Mather Point and dinner at the lodge restaurant
        
        Day 2: October 8, 2024 (Tuesday)
        Morning: Guided hike/climbing experience at Grand Canyon's Rim-to-Rim trail (shorter section, suitable for a day's climb)
        Afternoon: Scenic lunch at a viewpoint along the South Rim trail
        Evening: Attend a ranger-led stargazing session (if available) or relax at the lodge with evening drinks by the fire

        Day 3: October 9, 2024 (Wednesday)
        Morning: Helicopter tour over the Grand Canyon for breathtaking aerial views
        Afternoon: Lunch at Grand Canyon Village, last-minute shopping for souvenirs
        Evening: Depart from Grand Canyon National Park
        """
      },
      {
        "prompt":
        """
        Create a trip for me to Cleveland National Forest between the dates of 2024-10-10 and 2024-10-12. I will be traveling with a partner, kids. I prefer housing in the form of hotels, lodges. I prefer these types of adventures: tours, climbing. Create a daily itinerary for this trip using this information.
        """,
        "response":
        """
        Day 1: October 10, 2024 (Thursday)
        Morning: Arrive at Cleveland National Forest. Check in at a cozy bed & breakfast in or around Julian (e.g., Pine Hills Lodge or Julian Lodge).
        Afternoon: Explore the scenic Santa Ysabel Preserve for a family-friendly hike. The West Preserve offers a 3.5-mile loop that’s great for kids with wide trails and gentle slopes.
        Evening: Return to the bed & breakfast. Enjoy a homemade dinner at the B&B or a meal at a local restaurant in Julian (ex. Jeremy's on the Hill, a farm-to-table restaurant in Julian). Finish the evening with a relaxing stroll around town.

        Day 2: October 11, 2024 (Friday)
        Morning: Cycle the Sunrise Highway, a scenic cycling route with stunning views of the forest and surrounding mountains. Opt for a family-friendly section from Pine Valley to Laguna Mountain, which has smoother paths suitable for kids.
        Afternoon: Pack a picnic lunch and stop at Laguna Mountain Recreation Area. Afterward, explore the Big Laguna Trail with a short family hike to the lake, enjoying the serene views.
        Evening: Head back to your bed & breakfast for some downtime. Enjoy a casual family dinner in Julian (ex. The Julian Grille), perhaps trying a famous Julian apple pie for dessert.

        Day 3: October 12, 2024 (Saturday)
        Morning: Hike Cuyamaca Peak via the Lookout Fire Road trail. It’s a moderate trail, but the views from the top make it a great reward for the whole family.
        Afternoon: Have lunch at a restaurant in Julian (ex. Romano's Restaurant). Explore the town, visit the local shops, or stop by the Julian Mining Company for a fun family activity like gem mining.
        Evening: Depart Cleveland National Forest and head back home, or enjoy a final relaxing evening in Julian before wrapping up your trip.
        """
      }
   ]
   #Instantiate the class
   prompt_template = PromptTemplate.from_template(
       "Create a trip for me to {location} between the dates of {trip_start} and {trip_end}. I will be traveling {traveling_with_list}. I prefer housing in the form of {lodging_list}. I prefer these types of adventures: {adventure_list}. Create a daily itinerary for this trip using this information."                                          
  )
   #formate the prompt template
   return prompt_template.format(
      location = form_data["location"],
      trip_start = form_data["trip_start"],
      trip_end = form_data["trip_end"],
      traveling_with_list = form_data["traveling_with_list"],
      lodging_list = form_data["lodging_list"],
      adventure_list = form_data["adventure_list"]
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
  log.info(prompt)
  return render_template("view-trip.html")
    
# Run the flask server
if __name__ == "__main__":#
    app.run()
