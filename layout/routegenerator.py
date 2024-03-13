import pandas as pd
import numpy as np
import os
##########################################
###### Loading the service definition
##########################################

# forbidden connections
# This is the list of connections allowed by bus services, but unrealistic in operation
forbidden = [ # originID, destID
    # Egoyá
    (9, 32),
    (9, 33),
    (9, 35),
    (9, 36),
    (9, 37),
    (9, 38),
    (9, 7),
    (9, 5),
    (9, 4),
    (9, 3),
    (9, 2),
    (9, 1),
    (9, 0), 
    # Coliseo
    (11, 32),
    (11, 33),
    (11, 35),
    (11, 36),
    (11, 37),
    (11, 38),
    (11, 7),
    (11, 5),
    (11, 4),
    (11, 3),
    (11, 2),
    (11, 1),
    (11, 0), 
    # Ormaza
    (13, 32),
    (13, 33),
    (13, 35),
    (13, 36),
    (13, 37),
    (13, 38),
    (13, 7),
    (13, 5),
    (13, 4),
    (13, 3),
    (13, 2),
    (13, 1),
    (13, 0), 
    # Mercasa
    (15, 32),
    (15, 33),
    (15, 35),
    (15, 36),
    (15, 37),
    (15, 38),
    (15, 7),
    (15, 5),
    (15, 4),
    (15, 3),
    (15, 2),
    (15, 1),
    (15, 0),
    # El Lago
    (17, 32),
    (17, 33),
    (17, 35),
    (17, 36),
    (17, 37),
    (17, 38),
    (17, 7),
    (17, 5),
    (17, 4),
    (17, 3),
    (17, 2),
    (17, 1),
    (17, 0), 
    # Otun
    (19, 32),
    (19, 33),
    (19, 35),
    (19, 36),
    (19, 37),
    (19, 38),
    (19, 7),
    (19, 5),
    (19, 4),
    (19, 3),
    (19, 2),
    (19, 1),
    (19, 0), 
]


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
                        if (station,line[j]) not in forbidden:
                            RouteMatrix[station][line[j]].append(itinerary)
                        #print('Added new itinerary', epoc)
    
    origins = list(set(destinations))

# calculating the weigth of each itinerary
RouteWeight = [[[] for i in range(len(stations))] for j in range(len(stations))]
# Normalizing the weights
for i in range(len(stations)):
    for j in range(len(stations)):
        if (i,j) not in forbidden: # If the connection is realistic
            for k in range(len(RouteMatrix[i][j])):
                factor=1
                RouteWeight[i][j].append(np.exp(-factor*np.array(RouteMatrix[i][j][k][1]))/np.sum(np.exp(-factor*np.array(RouteMatrix[i][j])[:,1])))
        else:
            print('forbidden')
            print(i,j)



# Printing the route matrix 
filename=os.path.join(wd,os.pardir,'conf', "RouteMatrix.txt")
print(filename)
routefile=open(filename,'w')

for i in range(len(stations)):
    for j in range(len(stations)):
        routefile.write("%d %d\n"%(i,j))
        # We evaluate the routes with a significant weight
        real_routes = [r for r in range(len(RouteMatrix[i][j])) if RouteWeight[i][j][r]>1e-3]
        routefile.write("%d\n"%len(real_routes))
        for k in real_routes:
           #print(i,j,k,len(RouteMatrix[i][j]), RouteMatrix[i][j])
            routefile.write("%f\n"%RouteWeight[i][j][k])
            routefile.write("%d %d\n"%(RouteMatrix[i][j][k][0],RouteMatrix[i][j][k][1]))                
routefile.close()


