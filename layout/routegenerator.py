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
    for stID in linedata[3::3]:
        service_stops[i].append(int(stID))

# getting the list of stations
stations = []
for stlist in service_stops:
    stations = stations + stlist
stations = list(set(stations))
print(stations)

# Defining the route matrix with empty list elements
RouteMatrix=[[[] for x in range(len(stations))] for x in range(len(stations))]

# The initial station ID
initstationID=0

#The origins element (updated on everystep)
origins=[]
#In the first step, the origins is simply the initial station
origins.append(initstationID)

#Creating the seed route for all strations
for station in stations:
    RouteMatrix[station][station].append([station,station,0])

for i in range(2*len(stations)):
    #Allocating memory for the destination, line and origin list
    destination=[]
    lines=[]
    origins=[]
    # First we find the possible destinations from the origins
    for station in origins:
        # we scan all the sevices
        for line in service_stops:
            # we find the index of the stop
            try:
                stindex = line.index(station)
            except:
                stindex = 45
        # Adding the new information
        destinationIDs=destinationIDs+destinationaux
        lineIDs=lineIDs+lineaux
        originIDs=originIDs+originaux
print(RouteMatrix)
    
'''
Copiado del original



# The algorithm stops when all stations are covered
#for station in Stations:
for i in range(2*len(Stations)):
    #Allocating memory for the destination, line and origin list
    destinationIDs=[]
    lineIDs=[]
    originIDs=[]
    # First we find the possible destinations from the origins
    for stationID in origins:
        [destinationaux,lineaux,originaux]=lineC.getdestinations(Stations,stationID,Lines)
        # Adding the new information
        destinationIDs=destinationIDs+destinationaux
        lineIDs=lineIDs+lineaux
        originIDs=originIDs+originaux
        
    # Creating a warning in case the size of the three vectors is different
    if len(destinationIDs)!=len(lineIDs) or len(destinationIDs)!=len(originIDs) or len(lineIDs)!=len(originIDs):
        print("Warning! The destinationIDs, lineIDs and originIDs vectors have different size")
        break
            
    # Creating the routes
    for destination,line,origin in zip(destinationIDs,lineIDs,originIDs):
        # Sweeping over all stations
        for station in Stations:
            # Checking all routes from station to origin
            for route in RouteMatrix[station.ID][origin]:
                # Copying the route to reach the origin
                routeaux=copy.deepcopy(route)
                # Only if the destination is not already in the route 
                if routeC.changenotincluded(routeaux,destination):
                    # Adding the new routefragment
                    routeaux.addstop(line,destination)
                    # only if the number of fragments is not larger than 3
                    if len(routeaux.fragments)<4:
                        # Checking the new route is not already there
                        alreadythere=False
                        for route1 in RouteMatrix[station.ID][destination]:
                            alreadythere=alreadythere+routeC.compareroutes(route1,routeaux)
                        if alreadythere==0:
                            # Adding the newly created route to the matrix
                            routeC.insertRoute(RouteMatrix[station.ID][destination],routeaux)    
    #    print(destinationIDs)
    
    # Removing duplicates
    destinationIDs=list(set(destinationIDs))
#    print(destinationIDs)

    # updating the origins
    origins=list(destinationIDs)
    print(origins)
'''
print(service_stops)