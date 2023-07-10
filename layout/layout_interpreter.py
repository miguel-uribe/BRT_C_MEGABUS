"""_summary_
This file reads the layout_file will all the information regarding the geometrical configuration in the system, it also reads the traffic lights file and checks that all traffic lights information is provided.
This file should be called as:
        python layout_interpreter.py
In the same folder of the current file there must be two input files:
    layout_file.xlsx: an Excel file with all the layout information
    traffic_lights_file.xlsx: an Excel file with the definition of all traffic lights
"""

# loading all the required packages
import pandas as pd
import numpy as np
from parameters import *
import os

# we locate the current file position
wd = os.path.dirname(__file__)
# We initially import the layout file
layout_df = pd.read_excel(os.path.join(wd,'layout_file.xlsx'))
# We determine the number of lanes
nlanes = len(layout_df.columns) - 2
# We determine the length of the system
length = len(layout_df)
# We create dictionaries to store all the information to be gathered from the file
lanes = {} # the arrays with the available lanes for each service
stationdefinition = {} # the list of doors in each station
servicedefinition = {} # The list of stops for each service
traffic_lights = {} # The sucession of traffic lights per route
servicebreaks = {} # the list of breaks in the system, for each service
servicestarts = {} # the position where each service starts
serviceends = {} # the position where each service ends
servicechanges = {} # the position and destination where a service changes

# We now scan over the entire dataframe and proceed to find the information
for index, row in layout_df.iterrows():
    # we scan over each lane
    for j in np.arange(nlanes):
        data = layout_df.loc[index].iloc[j+2]
        # we obtain the information in each case
        try:
            items = data.split(';')
            for item in items:
                itemclass, iteminfo = item.split(':')
                itemclass = itemclass.strip()
                ############################################
                # R, the service information
                if itemclass == 'R':
                    services = [serv.strip() for serv in iteminfo.split(',')]
                    # we now loop over the found services
                    for service in services:
                        # we check whether the service is already in service list
                        if service not in lanes.keys():
                            # we add it to all the relevant lists
                            lanes[service] = np.zeros((length, nlanes))
                            lanes[service][index,j] = 1
                            servicedefinition[service] = []
                        # if it is already there, we only configure the lanes
                        else:
                            lanes[service][index,j] = 1
                ################################################
                #E, the station information
                elif itemclass == 'E':
                    stopdata = iteminfo.split(',')
                    # we add the corresponding stop to the station and the services
                    name = stopdata[0].strip()
                    # we check whether the station is already in the dictionary
                    if name in stationdefinition.keys():
                        # we add the stop
                        stationdefinition[name].append(index)
                    else:
                        stationdefinition[name] = [index]
                    # we retrieve the position of the stop in the station
                    pos = len(stationdefinition[name])-1
                    # if stopdata has only one element - all services make a stop in this place
                    if len(stopdata)==1:
                        # we add the stop to all services
                        for service in services:
                            servicedefinition[service].extend([name,pos])
                    # if there are more than 1 element, only some services make their stop
                    else:
                        new_services = [data.strip() for data in stopdata[1:]]
                        # we add the stop to the specific services
                        for service in new_services:
                            servicedefinition[service].extend([name,pos])
                            
                ################################################
                #S, the traffic light information
                elif itemclass == 'S':
                    # we loop over the services
                    for service in services:
                        # we check  whether the service is already in the traffic lights
                        if service in traffic_lights.keys():
                            traffic_lights[service].extend([info.strip() for info in iteminfo.split(',')])
                        else:
                            traffic_lights[service] = [info.strip() for info in iteminfo.split(',')]
                ################################################
                #B, the bridge information
                elif itemclass == 'B':
                    [final_pos, final_lane] = [info.strip() for info in iteminfo.split(',')]
                    # we loop over the services
                    for service in services:
                        # we check  whether the service is already in the traffic lights
                        if service in servicebreaks.keys():
                            servicebreaks[service].append((index,j, int(final_pos), int(final_lane)))
                        else:
                            servicebreaks[service] = [(index,j, int(final_pos), int(final_lane))]
 
                ################################################
                #SS, the service start 
                elif itemclass == 'SS':
                    # we get the services being introduced
                    int_services = [data.strip() for data in iteminfo.split(',')]
                    # we loop over the services
                    for service in int_services:
                        # we check  whether the service is already in the start dictitionary
                        if service in servicestarts.keys():
                            print(f"Error. Service {service} has been introduced more than once in servicestarts at position {index}")
                        else:
                            servicestarts[service] = index
                ################################################
                #SF, the service finish 
                elif itemclass == 'SF':
                    # we get the services being finishing
                    end_services = [data.strip() for data in iteminfo.split(',')]
                    # we loop over the services
                    for service in end_services:
                        # we check  whether the service is already in the finish dictionary
                        if service in serviceends.keys():
                            print(f"Error. Service {service} has been introduced more than once in serviceends at position {index}")
                        else:
                            serviceends[service] = index
                ################################################
                #C, a service change
                elif itemclass == 'C':
                    # we get the change information
                    org_service, final_service = [data.strip() for data in iteminfo.split(',')]
                    # we check  whether the service is alredy in the changes list
                    if org_service in servicechanges.keys():
                        servicechanges[org_service].append([final_service, index])
                    else:
                        servicechanges[service] = [[final_service, index]]
        except:
            pass
        
print(stationdefinition)
print(servicedefinition)
print(traffic_lights)
print(servicebreaks)
print(servicestarts)
print(serviceends)
print(servicechanges)

# After we have all the information, we proceed to create all the lane files
for service in lanes.keys():
    # we export the lane file
    name = os.path.join(os.pardir,'conf',f'lanes_{service}.txt')
    np.savetxt(name, lanes[service], fmt = '%d')
    
    # we now calculate the speed
    V = (vmax)*np.ones(np.shape(lanes[service]))  # by default the maximal speed is the same along the entire corridor
    name = os.path.join(os.pardir,'conf',f'V_{service}.txt')
    np.savetxt(name, V, fmt = '%d')
    
    # Now we create the leftchange file, containing the information regarding the posibility to change the lane to the left, this is increasing the lane. 0 means change is not possible, 1 means change is possible
    LC = np.copy(lanes[service])
    # clearly for the leftmost lane it is always impossible to move to the left
    LC[:,-1]=0
    # in addition, it is impossible to move to the left when the lane in the left is not there
    mask = lanes[service]-np.roll(lanes[service], -1, axis = 1)==1
    LC[mask] = 0
        
    # Now we create the rightchange file, containing the information regarding the posibility to change the lane to the right, this is decreasing the lane. 0 means change is not possible, 1 means change is possible
    RC = np.copy(lanes[service])
    # clearly for the rightmost lane it is always impossible to move to the left
    RC[:,0]=0
    # in addition, it is impossible to move to the left when the lane in the left is not there
    mask = np.where(lanes[service]-np.roll(lanes[service], 1, axis = 1)==1)
    RC[mask] = 0
    
    # We now print the results
    name = os.path.join(os.pardir,'conf',f'LC_{service}.txt')
    np.savetxt(name, LC, fmt = '%d')
    name = os.path.join(os.pardir,'conf',f'RC_{service}.txt')
    np.savetxt(name, RC, fmt = '%d')
    
    # We now calculate the end of lane
    EL = 1000*np.ones(np.shape(lanes[service]))
    auxEL = np.zeros(np.shape(lanes[service]))
    mask =  (np.roll(lanes[service], 1, axis = 0) - lanes[service]) == 1
    auxEL[mask] = 1

    for i in range(len(lanes[service][0,:])):
        endF = False
        for j in np.arange(len(lanes[service])-1,-1,-1):
            if endF:
                EL[j,i] = endPos-j
            if auxEL[j,i] == 1:
                endF = True
                endPos = j - 1
    
    name = os.path.join(os.pardir,'conf',f'EL_{service}.txt')
    np.savetxt(name, EL, fmt = '%d')
    
#################################################################
############# now we start building the station information
# the list of stations
stations = np.array(list(stationdefinition.keys()))
# we export the station list
name = os.path.join(os.pardir,'conf','station_list.txt')
np.savetxt(name,  np.hstack( ( np.arange(len(stations), dtype = int).reshape(-1,1), stations.reshape(-1,1) ) ) , fmt = '%s %s')

# we now create the station definition file
name = os.path.join(os.pardir,'conf','station_definition.txt')
text = ''
for i, station in enumerate(stations):
    text = text + f'{i}'
    for dock in stationdefinition[station]:
        text = text + f' {dock} 0' # by default, no biarticulated buses are allowed at any docking bay
    text = text + '\n'
deffile = open(name, 'w')
deffile.write(text)
deffile.close()

#################################################################
############# now we start building the service information
# the list of services
services = np.array(list(servicedefinition.keys()))
# we export the service list
name = os.path.join(os.pardir,'conf','service_list.txt')
np.savetxt(name,  np.hstack( ( np.arange(len(services), dtype = int).reshape(-1,1), services.reshape(-1,1) ) ) , fmt = '%s %s')