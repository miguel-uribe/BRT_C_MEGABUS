import pandas as pd
import numpy as np
import os
##########################################
###### Loading the service definition
##########################################

# we locate the current file position
wd = os.path.dirname(__file__)

# we open the service definition file
file = open(os.path.join(wd, os.pardir, 'conf','service_definition.txt'), 'r')
Lines = file.readlines()
service_stops = [[] for i in range(len(Lines))]
for i,line in enumerate(Lines):
    linedata = line.split(' ')
    for stID in linedata[4::3]:
        service_stops[i].append(int(stID))

print(service_stops)
# reading the list of service changes
file = open(os.path.join(wd, os.pardir, 'conf','service_changes.txt'), 'r')
Lines = file.readlines()
for i,line in enumerate(Lines):
    linedata = line.split(' ')
    if len(linedata)>1:
        orLine = int(linedata[0])
        destLine = int(linedata[1])
        service_stops[orLine].extend(service_stops[destLine])

print(service_stops)
# getting the list of stations
stations = []
for stlist in service_stops:
    stations = stations + stlist
stations = list(set(stations))


# Defining the route matrix with empty list elements
RouteMatrix=[[[] for x in range(len(stations))] for x in range(len(stations))]

# The initial station ID
initstationID = 0

#The origins element (updated on everystep)
origins=[]
#In the first step, the origins is simply the initial station
origins.append(initstationID)

# Looking for all possible direct routes between stations
# No bus changes are included in the list
for epoc in range(10):
    #Allocating memory for the destination, line and origin list
    destinations=[]
    # First we find the possible destinations from the origins
    for station in origins:
        # we scan all the services
        for i,line in enumerate(service_stops):
            # we find the index of the stop
            try:
                stindex = line.index(station)
            except:
                stindex = np.nan
            # in case the origin is in the service
            if ~np.isnan(stindex):
                # we scan over the following stops
                for j in range(stindex+1,len(line)):
                    destinations.append(line[j])
                    # we define the itinerary as service - number of stops
                    itinerary = [i, j-stindex]
                    # we check whether the itinerary already exists
                    if itinerary not in RouteMatrix[station][line[j]]:
                        RouteMatrix[station][line[j]].append(itinerary)
                        #print('Added new itinerary', epoc)
    
    origins = list(set(destinations))

# calculating the weigth of each itinerary
RouteWeight = [[[] for i in range(len(stations))] for j in range(len(stations))]
# Normalizing the weights
for i in range(len(stations)):
    for j in range(len(stations)):
        for k in range(len(RouteMatrix[i][j])):
            factor=1
            RouteWeight[i][j].append(np.exp(-factor*np.array(RouteMatrix[i][j][k][1]))/np.sum(np.exp(-factor*np.array(RouteMatrix[i][j])[:,1])))


# Printing the route matrix 
filename=os.path.join(wd,os.pardir,'conf', "RouteMatrix.txt")
print(filename)
routefile=open(filename,'w')

for i in range(len(stations)):
    for j in range(len(stations)):
        routefile.write("%d %d\n"%(i,j))
        routefile.write("%d\n"%len(RouteMatrix[i][j]))
        for k,route in enumerate(RouteMatrix[i][j]):
            routefile.write("%f\n"%RouteWeight[i][j][k])
            routefile.write("%d %d\n"%(RouteMatrix[i][j][k][0],RouteMatrix[i][j][k][1]))                
routefile.close()


