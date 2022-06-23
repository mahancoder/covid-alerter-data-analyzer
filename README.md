# Covid Alerter Data Analyzer
The data analyzer script for The Covid Alerter Mobile App

## Description
This repo is part of the Covid Alerter project.
This python script will run over the reports database and analyze them, producing a score (0 - 10, best - worse) for a neighbourhood in that day.

## Usage
To run the script, create the file `passowrd.json` containing your database passwords, with this format:
```json
{
    "main": "MySQL Password",
    "osm": "PostgreSQL Password"
}
```
Then, run `analyzer.py` to run the script.

## Technology
This script is written in python. It uses mainly raw SQL and SQL Alchemy to process most of the data.

## Behind the scenes
The main entry point of the app is located in the `analyze.py` module. That module, initiates database connections and passes to them to other functions as an argument. Next, it calls `calculate_par.calculate()` to calculate the number of people needed per square meter in a neighbourhood to add 1 full point to the severity score. This `PAR` is generated based on a few factors like how much of a neighbourhood is open area and what percent of it are houses and etc.  
After calculating the PAR, it calls `calculate_score.calculate` to process the reports, calculate the scores, and store them in the database,

## How the PAR is calculated
The `PAR` is calculated by finding the total area of each 3 types of places, `outdoor`, `indoor`, and `houses`, multiplying them by their specified weights, and divide the total result, by the total area of the neighbourhood (which is considered as the sum of these 3, NOT the actual total area of theneighbourhood)
To find outdoor places, we use a collection of tags that are considered outdoor. We also remove the childs. For example, if a park contains a playground inside it, we don't want the playground's area to be added into the park, instead we just consider the whole park in the computation and remove the playground from the list.
Then, from the remaining `ways`, we filter them out based on buildings that are commercial (indoor but not house). The script does that both based on tags and also whether a building contains a commercial node in its boundaries (this is a common way to map shops in OSM), then, the remaining buildings along with buildings with specific tags, are considered to be houses.

## How the score is calculated
The score is calculated based on the number of reports a user has sent, and the neighbourhood's PAR.
First, we need to filter out all reports, by the reports that are 3+ consecutive reports in the same neighbourhood. Since each person sends reports every 15 mins, this means the person has been in that neighbourhood for 45-60 mins, which is our lower limit of considering a report as a **stay**.
Then, we add 1 point for the first 3 reports, and raise the other reports count to the power of `0.25` to get a decrease in the weight of the consecutive hours of stay after it, and in the end, we multiply the sum of all these reports generated values by the `PAR`, to get the total score. Note that the score is linear, meaning if the result of the computation turns out larger than 10, we still consider the score a `10` which is our maximum severity

**The way all these are accurated is not finite, and they can be tuned by a professional specialist in the medial field, what I've put in are just some dummy constants and methods to show a prototype.**

## ToDo
* Detect the user's house over time and remove it from the score compuataion
* Tweak the processing to account for things like rush hour, traffic, day/night times, weather, and other external factors
* Somehow remove the need to use a list comprehension to turn the query results to their appropriate objects, to store them in the database when calculating the score
* Support for the `way` childs that have a part of their area intersecting another way, and are not fully placed inside another `way`
