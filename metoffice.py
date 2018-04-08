##################################################################
#
# rain.py
#
# Methods for getting local rain details for now
#
##################################################################
import os, sys, requests, json, datetime

class Rain():

   def __init__(self,here='351389'):
       self.HERE = here # default is Epping 
       if not sys.path[0]: this_dir = os.getcwd()
       else: this_dir = sys.path[0]
       with open(this_dir + '/.credentials/datapoint.key') as dpkey: self.KEY  = dpkey.readline()
       self.METOFF = 'datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/'
       self.URL = 'http://' + self.METOFF +  self.HERE + '/?key=' + self.KEY + \
                  '&res=3hourly'
       self.lastRainForecast = 0
       #print (self.URL)

   def getForecastJSON(self):
       response = requests.get(self.URL)
       if response.status_code != 200: return [ {'Pp': '-1'} ]
       today = response.json()['SiteRep']['DV']['Location']['Period'][0]['Rep']
       this_hour = datetime.datetime.now().hour
       self.slot = (this_hour//3) * 180
       rep = [ r for r in today if r['$'] == str(self.slot) ]
       return rep

   def getPrecipProb(self):
       self.lastRainForecast = self.getForecastJSON()[0]['Pp']
       # use the variable more often than getting the forecast as API limit it 300 per hour
       # and 5000 per day
       return self.lastRainForecast

# End
