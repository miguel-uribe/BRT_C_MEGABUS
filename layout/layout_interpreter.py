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

#################################################################
############# now we start building the traffic lights information
traffic_lights_df = pd.read_excel(os.path.join(wd,'traffic_lights_file.xlsx'))
traffic_lights = {}
for index, row in traffic_lights_df.iterrows():
    tlname = row['name']
    traffic_lights[tlname] = {}
    traffic_lights[tlname]['dir'] = [info.strip() for info in row['direction'].split('-')] # we read all the directions
    traffic_lights[tlname]['lengths'] = [int(info.strip()) for info in row['length'].split('-')] # we read all the lengths
    if (len(traffic_lights[tlname]['dir'])!=len(traffic_lights[tlname]['lengths'])): # we check that the number of directions and lengths is the same
        print(f"Warning!! Traffic light {tlname} has a different number of directions than lengths")
    traffic_lights[tlname]['offset'] = row['offset']
    phase = 0
    traffic_lights[tlname]['phases'] = []   # we create a list of phases
    while(type(row[f'phase_{phase}'])==str):   # we only scan until a phase is not a string
        duration, scheme = row[f'phase_{phase}'].split(':')  # we get the information 
        duration = int(duration) # the duration must be an integer
        scheme = [int(info.strip()) for info in scheme.split('-')] # the scheme is an integer list of 0's and 1's
        phase += 1
        traffic_lights[tlname]['phases'].append((duration, scheme))
        if (len(traffic_lights[tlname]['dir'])!=len(scheme)):
            print(f"Warning!!! Traffic light {tlname} has a scheme with a different number of elements than the number of possible directions")
    # We create the list of positions, it is initialized with None values
    traffic_lights[tlname]['pos'] = [None]*len(traffic_lights[tlname]['dir'])


###################################################################
############## we load the layout file information
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
servicetrafficlights = {} #The succession of traffic lights per route
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
                            servicedefinition[service].append((name,pos))
                    # if there are more than 1 element, only some services make their stop
                    else:
                        new_services = [data.strip() for data in stopdata[1:]]
                        # we add the stop to the specific services
                        for service in new_services:
                            servicedefinition[service].append((name,pos))
                            
                ################################################
                #S, the traffic light information
                elif itemclass == 'S':

                    # we extract the name and direction
                    tlname, tldir = [info.strip() for info in iteminfo.split(',')]
                    # we add the position information to the traffic_lights configuration
                    tlindex = np.where(np.array(traffic_lights[tlname]['dir'])==tldir)[0][0]
                    traffic_lights[tlname]['pos'][tlindex] = index
                    # we loop over the services
                    for service in services:
                        # we check  whether the service is already in the traffic lights
                        if service in servicetrafficlights.keys():
                            servicetrafficlights[service].append((tlname, tldir))
                        else:
                            servicetrafficlights[service] = [(tlname, tldir)]
                        # we also add the information of the traffic light
                        
                        
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
                    # we check  whether the service is already in the changes list
                    if org_service in servicechanges.keys():
                        servicechanges[org_service].append([final_service, index])
                    else:
                        servicechanges[service] = [[final_service, index]]
                    # we check  whether the service is already in the finish dictionary
                    if org_service in serviceends.keys():
                        print(f"Error. Service {org_service} has been introduced more than once in serviceends at position {index}")
                    else:
                        serviceends[org_service] = index
        except:
            pass

# for each service, the servicedefinition, the traffic_lights information, and the breaks information must be sorted based on the service start position
# sorting the breaks first:
for key in servicebreaks.keys():
    ord_index = []
    # only if there are more than one breaks it becomes important to sort
    if len(servicebreaks[key])>1:
        breaks = np.array(servicebreaks[key])
        # we now find the first break after the service starts
        ord_index.append(np.where(breaks[:,0] > servicestarts[key])[0][0])
        # we now start finding the first break after the last break
        while (len(ord_index)<len(breaks)):
            # the last break position
            lastbreak = breaks[ord_index[-1], 2]
            # we find the next break after the last break
            ord_index.append(np.where(breaks[:,0] > lastbreak)[0][0])
        # the service breaks are reordered using ord_index
        servicebreaks[key][:] = [servicebreaks[key][i] for i in ord_index]

track_index = {}
# we now proceed to sort the stations
for key in servicedefinition.keys():
    ord_index = [] # the list with the organized index
    track_index[key] = [] # a list with the section number 
    breaksexists = False # By default there are no breaks
    # we create an array of stops
    stops = np.array([stationdefinition[servicedefinition[key][i][0]][servicedefinition[key][i][1]] for i in range(len(servicedefinition[key]))] )
    # we load the array of breaks
    if key in servicebreaks.keys():
        breaks = np.array(servicebreaks[key])
        breaksexists = True
    # we build the sections
    if not breaksexists:
        sections = [(servicestarts[key], serviceends[key])]
    else:
        sections = [(servicestarts[key], breaks[0,0])]
        for i in range(len(breaks)-1):
            sections.append((breaks[i,2], breaks[i+1,0]))
        sections.append((breaks[-1,2], serviceends[key]))
    # We look for the first stop in a section
    for i,section in enumerate(sections):
        firststop = np.where((stops >= section[0]) & (stops<= section[1]) )[0]
        if len(firststop)>0:
            next_index = firststop[0]
            track = i
            break
    ord_index.append(next_index)
    track_index[key].append(track)
    # we repeat this process until all stations are covered
    while (len(ord_index) < len(servicedefinition[key])):
        next_index += 1
        if breaksexists:
            if stops[next_index] > breaks[track][0]:
                next_index = np.where(stops > breaks[track][2])[0][0]
                track += 1
                if (track == len(breaks)):
                    breaksexists = False
        ord_index.append(next_index)
        track_index[key].append(track)
        
    if (len(ord_index)!= len(set(ord_index))):
        print(f"Warning!!! The indices in ord_index for service {key} when ordering the stops are not unique")
    # we reorder the stop list
    servicedefinition[key][:] = [servicedefinition[key][i] for i in ord_index]


track_index_tl = {}
# now we proced to sort the traffic_lights
for key in servicetrafficlights.keys():
    ord_index = [] # the list with the organized index
    track_index_tl[key] = [] # a list with the section number 
    breaksexists = False # By default there are no breaks
    # we create an array with the position of all traffic lights
    tlights = np.array([traffic_lights[name]['pos'][np.where(np.array(traffic_lights[name]['dir'])==dir)[0][0]] for name, dir in servicetrafficlights[key]] )
    # we load the array of breaks
    if key in servicebreaks.keys():
        breaks = np.array(servicebreaks[key])
        breaksexists = True
    # we build the sections
    if not breaksexists:
        sections = [(servicestarts[key], serviceends[key])]
    else:
        sections = [(servicestarts[key], breaks[0,0])]
        for i in range(len(breaks)-1):
            sections.append((breaks[i,2], breaks[i+1,0]))
        sections.append((breaks[-1,2], serviceends[key]))
    #print(sections)
    # We look for the first traffic light in a section
    for i,section in enumerate(sections):
        firstlight = np.where((tlights >= section[0]) & (tlights<= section[1]) )[0]
        if len(firstlight)>0:
            next_index = firstlight[0]
            track = i
            break
    ord_index.append(next_index)
    track_index_tl[key].append(track)
    # we repeat this process until all traffic lights are covered
    while (len(ord_index) < len(servicetrafficlights[key])):
        next_index += 1
        if breaksexists:
            if tlights[next_index] > breaks[track][0]:
                next_index = np.where(tlights > breaks[track][2])[0][0]
                track += 1
                if (track == len(breaks)):
                    breaksexists = False
        ord_index.append(next_index)
        track_index_tl[key].append(track)
    #print(key, ord_index, track_index)
    if (len(ord_index)!= len(set(ord_index))):
        print(f"Warning!!! The indices in ord_index for service {key} when ordering the stops are not unique")
    # we reorder the stop list
    servicetrafficlights[key][:] = [servicetrafficlights[key][i] for i in ord_index]


print("Parsed all the layout and traffic light information, writting the configuration files")
# After we have all the information, we proceed to create all the lane files
for service in lanes.keys():
    # we export the lane file
    name = os.path.join(wd, os.pardir,'conf',f'lanes_{service}.txt')
    np.savetxt(name, lanes[service], fmt = '%d')
    
    # we now calculate the speed
    V = (vmax)*np.ones(np.shape(lanes[service]))  # by default the maximal speed is the same along the entire corridor
    name = os.path.join(wd, os.pardir,'conf',f'V_{service}.txt')
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
    name = os.path.join(wd, os.pardir,'conf',f'LC_{service}.txt')
    np.savetxt(name, LC, fmt = '%d')
    name = os.path.join(wd, os.pardir,'conf',f'RC_{service}.txt')
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
    
    name = os.path.join(wd, os.pardir,'conf',f'EL_{service}.txt')
    np.savetxt(name, EL, fmt = '%d')
    
#################################################################
############# now we start building the station information
# the list of stations
stations = np.array(list(stationdefinition.keys()))
# we export the station list
name = os.path.join(wd, os.pardir,'conf','station_list.txt')
np.savetxt(name,  np.hstack( ( np.arange(len(stations), dtype = int).reshape(-1,1), stations.reshape(-1,1) ) ) , fmt = '%s %s')

# we now create the station definition file
# the format of the file is as follows
# station index - [position, biarticulated capability] (over all docking bays)
name = os.path.join(wd, os.pardir,'conf','station_definition.txt')
text = ''
for i, station in enumerate(stations):
    text = text + f'{i}'
    for dock in stationdefinition[station]:
        text = text + f' {dock} 0' # by default, no biarticulated buses are allowed at any docking bay
    text = text + '\n'
# we export the file
with open(name, 'w') as deffile:
    deffile.write(text)


#################################################################
############# now we start building the service information
# the list of services
services = np.array(list(servicedefinition.keys()))
# we export the service list
name = os.path.join(wd, os.pardir,'conf','service_list.txt')
np.savetxt(name,  np.hstack( ( np.arange(len(services), dtype = int).reshape(-1,1), services.reshape(-1,1) ) ) , fmt = '%s %s')

# for each service we create the service definition file as a series with the station and docking bay information
# the format of the file is as follows
# service index - service start - service end - [station index, docking bay index] (over all stops of the service)
name = os.path.join(wd, os.pardir,'conf','service_definition.txt')
text = ''
for i, service in enumerate(services):
    text = text + f'{i} {servicestarts[service]} {serviceends[service]}'
    for j in range(len(servicedefinition[service])):
        station, dock = servicedefinition[service][j]
        track = track_index[service][j]
        index = np.where(stations == station)[0][0]
        text = text + f' {index} {dock} {track}'
    text = text + '\n'
# we export the file
with open(name, 'w') as deffile:
    deffile.write(text)

# we now create a file specifying the service breaks
# the format of the file is as follows
# service index - [origin pos, origin lane, destination pos, destination lane] (over all the breaks)
name = os.path.join(wd, os.pardir,'conf','service_breaks.txt')
text = ''
for i, service in enumerate(services):
    text = text + f'{i}'
    if service in servicebreaks.keys():
        for or_pos, or_lane, des_pos, des_lane in servicebreaks[service]:
            text = text + f' {or_pos} {or_lane} {des_pos} {des_lane}'
        text = text + '\n'
    else:
        text = text + '\n'
# we export the file
with open(name, 'w') as breakfile:
    breakfile.write(text)


#################################################################
############# now we start building the traffic light information
tlights = np.array(list(traffic_lights.keys()))
# we export the traffic lights list the format of this list is as follows
# traffic_light_index - traffic_light_name - offset -  Ndirections - [list of directions] - [list of positions] - [list of lenghts] - Nphases - [phase duration, phase configuration] (over all the phases) 
name = os.path.join(wd, os.pardir,'conf','traffic_light_list.txt')
text = ''

for i, tl in enumerate(tlights):
    text = text + f'{i} {tl} {traffic_lights[tl]["offset"]} {len(traffic_lights[tl]["dir"])}'
    for dir in traffic_lights[tl]['dir']:
        text = text + f' {dir}'
    for pos in traffic_lights[tl]['pos']:
        text = text + f' {pos}'
    for length in traffic_lights[tl]['lengths']:
        text = text + f' {length}'
    text = text + f' {len(traffic_lights[tl]["phases"])}'
    for phase in traffic_lights[tl]["phases"]:
        text = text + f' {phase[0]}'
        for conf in phase[1]:
            text = text + f' {conf}'
    text = text + '\n'

with open(name, 'w') as tlfile:
    tlfile.write(text)    

print(traffic_lights)
# we now create a file specifying the traffic lights for each service
# the format of the file is as follows
# service index - [traffic light index, direction] (over all the traffic lights)
name = os.path.join(wd, os.pardir,'conf','service_traffic_lights.txt')
text = ''
for i, service in enumerate(services):
    text = text + f'{i}'
    if service in servicetrafficlights.keys():
        for j in range(len(servicetrafficlights[service])):
            tlname, dir = servicetrafficlights[service][j]
            track = track_index_tl[service][j]
            tlindex = np.where (tlname == tlights)[0][0]
            dirindex = np.where (dir == np.array(traffic_lights[tlname]['dir']))[0][0]
            text = text + f' {tlindex} {dirindex} {track}'
        text = text + '\n'
    else:
        text = text + '\n'

with open (name, 'w') as tlservfile:
    tlservfile.write(text)
    
print("All the configuration files have been properly written")
