#ifndef CREATE_SYSTEM
#define CREATE_SYSTEM

# include "linesC.h"
# include "parameters.h"
# include "stationC.h"
# include "tlC.h"
# include <vector>
# include <string>
#include <array>
#include <cmath>
#include <fstream>
#include <sstream>
#include <iostream>
#include <stdexcept>

// A depot is a place where buses are parked. Buses are introduced at the origin cell and are parked again when their service ends at the end cell.
struct depotC
{
    std::string name;
    int origin = 0; // the services starting at this cell take their buses from this depot
    int end = 0; // the services ending at this cell leave their buses at this depot
    int initial_buses = 0; // the number of buses parked at the beginning of the simulation
};

struct System
{
    std::vector<lineC> Lines;
    std::vector<stationC> Stations;
    std::vector<tlC> Tlights;
    std::vector<std::array<int, 4>> Breaks;
    std::vector<depotC> Depots;
    SimParams Par;
};

// The counters gathered during a simulation, they do not affect its evolution
struct Stats
{
    std::vector<int> st_entries; // passengers entering the system at each station
    std::vector<int> st_boardings; // passengers boarding a bus at each station
    std::vector<int> st_alightings; // passengers leaving the system at each station
    std::vector<long long> st_waiting; // the sum over time of the passengers waiting at each station
    std::vector<int> ln_departures; // buses introduced for each service
    std::vector<int> ln_queued; // buses that could not be introduced on time for each service
    std::vector<int> ln_arrivals; // buses finishing each service
    std::vector<long long> ln_triptime; // the sum of the trip times of the buses finishing each service
    std::vector<int> ln_boardings; // passengers boarding each service
    long long traveltime = 0; // the sum of the travel times of the passengers leaving the system
    int delivered = 0; // the number of passengers leaving the system
    int nsteps = 0; // the number of simulated time steps

    Stats(){}
    Stats(int nstations, int nlines):
        st_entries(nstations, 0), st_boardings(nstations, 0), st_alightings(nstations, 0), st_waiting(nstations, 0),
        ln_departures(nlines, 0), ln_queued(nlines, 0), ln_arrivals(nlines, 0), ln_triptime(nlines, 0), ln_boardings(nlines, 0){}
};

// opening a configuration file, a missing file is an error
std::ifstream openconffile(std::string filename){
    std::ifstream file(filename);
    if (!file.is_open()){
        throw std::runtime_error("Unable to open the configuration file " + filename);
    }
    return file;
}


auto createsystem(std::string stationlist, std::string stationdefinition, std::string tldefinition, std::string servicelist, std::string servicedefinitions, std::string servicedata, std::string servicetls, std::string breaksdef, std::string servicebreaks, std::string servicechange){

    // Creating the structure of the system
    System SYSTEM;

    // creating the list of stations in the system
    std::ifstream stationlist_f = openconffile(stationlist);
    std::ifstream stationdefinitions_f = openconffile(stationdefinition);
    std::string Line;
    std::string read;
    int ID;
    std::string stName;
    while (std::getline(stationlist_f,Line)){
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read);
        iss>>read;
        stName = read;
        SYSTEM.Stations.push_back(stationC(stName));
    }
    // opening the definition file to include the stops of each station
    while (std::getline(stationdefinitions_f,Line)){
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read);
        while(iss>>read){
            int stoppos = (int) std::round(1.0*std::stoi(read)/Dx);
            iss>>read;
            int biart = std::stoi(read);
            SYSTEM.Stations[ID].addstop(stoppos, biart);
        }
    }

    stationlist_f.close();
    stationdefinitions_f.close();


    // Reading the traffic lights information file
    std::ifstream tllist_f = openconffile(tldefinition);
    std::string tlname;
    int offset, ndir, nphases;
    while (std::getline(tllist_f,Line)){
        std::istringstream iss(Line);
        iss>>read; //reading the ID
        ID = std::stoi(read);
        iss>>tlname; // reading the name
        iss>>read; //reading the offset
        offset = std::stoi(read);
        iss>>read; //reading the number of directions
        ndir = std::stoi(read);
        std::vector<std::string> directions;
        for (int i=0; i<ndir; i++){ // reading all the directions
            iss>>read;
            directions.push_back(read);
        }
        std::vector<int> positions;
        for (int i=0; i<ndir; i++){ // reading all the positions
            iss>>read;
            if (read == "None"){
                positions.push_back(1e6);
            }
            else{
                positions.push_back(std::stoi(read));
            }
        }
        std::vector<int> lengths;
        for (int i=0; i<ndir; i++){ // reading all the lengths
            iss>>read;
            lengths.push_back(std::stoi(read));
        }
        iss>>read;
        nphases = std::stoi(read);
        std::vector<std::vector<int>> phases;
        std::vector<int> durations;
        for (int i=0; i<nphases; i++){ // reading all the phases
            iss>>read; // reading the duration
            durations.push_back(std::stoi(read));
            std::vector<int> phasesaux;
            for (int j = 0; j<ndir; j++){ // reading all the phases
                iss>>read;
                phasesaux.push_back(std::stoi(read));
            }
            phases.push_back(phasesaux);
        }
        // Adding the traffic light to the SYSTEM
        SYSTEM.Tlights.push_back(tlC(tlname, offset));
        SYSTEM.Tlights.back().directions = directions;
        SYSTEM.Tlights.back().positions = positions;
        SYSTEM.Tlights.back().lengths = lengths;
        SYSTEM.Tlights.back().durations = durations;
        SYSTEM.Tlights.back().phases = phases;

    }

    tllist_f.close();


    // Creating the list of services in the system and loading their headways
    std::ifstream servicelist_f = openconffile(servicelist);
    std::ifstream servicedefinitions_f = openconffile(servicedefinitions);
    std::ifstream servicedata_f = openconffile(servicedata);
    std::ifstream breaksdef_f = openconffile(breaksdef);
    std::ifstream servicebreaks_f = openconffile(servicebreaks);
    std::ifstream servicetls_f = openconffile(servicetls);
    std::ifstream servicechanges_f = openconffile(servicechange);

    // Opening the service list file
    std::string lName;
    while (std::getline(servicelist_f,Line)){
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read);
        iss>>lName;
        SYSTEM.Lines.push_back(lineC(lName));
    }


    // loading the headway and biarticulated information
    int headway;
    int biart;
    while (std::getline(servicedata_f,Line)){
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read);
        iss>>read;
        headway = std::stoi(read);
        iss>>read;
        biart = std::stoi(read);
        SYSTEM.Lines[ID].headway = headway;
        SYSTEM.Lines[ID].biart = biart;
    }

    // loading the information regarding the stops
    int origin, end, or_lane;
    while (std::getline(servicedefinitions_f,Line)){
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read);
        iss>>read;
        origin = std::stoi(read);
        iss>>read;
        or_lane = std::stoi(read);
        iss>>read;
        end = std::stoi(read);
        SYSTEM.Lines[ID].origin =(int) std::round(1.0*origin/Dx);
        SYSTEM.Lines[ID].or_lane = or_lane;
        SYSTEM.Lines[ID].end = (int) std::round(1.0*end/Dx);
        std::vector<int> stationIDs;
        std::vector<int> wagonIDs;
        std::vector<int> stoptracks;
        while(iss>>read){
            stationIDs.push_back(std::stoi(read));
            iss>>read;
            wagonIDs.push_back(std::stoi(read));
            iss>>read;
            stoptracks.push_back(std::stoi(read));
        }
        if (stationIDs.size()>0){
            SYSTEM.Lines[ID].stoptracks = stoptracks;
            SYSTEM.Lines[ID].setstopx(stationIDs, wagonIDs, SYSTEM.Stations);
        }

    }

    // reading the service traffic light information
     // loading the information regarding the stops
    while (std::getline(servicetls_f,Line)){
        std::vector<int> tls;
        std::vector<int> tldir;
        std::vector<int> tltracks;
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read); // reading the service id
        while (iss>>read){
            tls.push_back(std::stoi(read));
            iss>>read;
            tldir.push_back(std::stoi(read));
            iss>>read;
            tltracks.push_back(std::stoi(read));
        }
        SYSTEM.Lines[ID].tls = tls;
        SYSTEM.Lines[ID].tldir = tldir;
        SYSTEM.Lines[ID].tltracks = tltracks;
    }

    // reading the service definition file
     while (std::getline(breaksdef_f,Line)){
        std::array<int, 4> Break;
        std::istringstream iss(Line);
        iss>>read;
        for (int i = 0; i<4; i++){
            iss>>read;
            Break[i] = std::stoi(read);
        }
        SYSTEM.Breaks.push_back(Break);
     }

    // reading the breaks information
    while (std::getline(servicebreaks_f,Line)){
        std::vector<int> breaks; // the index of the breaks
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read); // reading the service id
        while (iss>>read){
            breaks.push_back(std::stoi(read));
        }
        SYSTEM.Lines[ID].breaks = breaks;
    }

    // reading the service changes information
    int dest_ID, pos_change;
    while (std::getline(servicechanges_f,Line)){
        std::istringstream iss(Line);
        iss>>read;
        ID = std::stoi(read); // reading the origin service id
        while (iss>>read){
            dest_ID = std::stoi(read);
            iss>>read;
            pos_change = std::stoi(read);
            SYSTEM.Lines[ID].change_pos = pos_change;
            SYSTEM.Lines[ID].dest_line = dest_ID;
        }
    }


    servicelist_f.close();
    servicedefinitions_f.close();
    servicedata_f.close();
    servicebreaks_f.close();
    servicetls_f.close();
    breaksdef_f.close();
    servicechanges_f.close();

    return (SYSTEM);

}


// this script loads the configuration files of a given kind, there is one file per service. The result is indexed as [service][lane][cell]
std::vector<std::vector<std::vector<int>>> loadconffilekind(std::string dir, std::string root, System & SYSTEM){
    std::vector<std::vector<std::vector<int>>> conffile;
    // Loading the configuration file for each service
    for (int i = 0; i < SYSTEM.Lines.size(); i++ ){
        std::string filename = dir + root +"_"+SYSTEM.Lines[i].name+".txt";
        //std::cout<<filename<<std::endl;
        std::ifstream file = openconffile(filename);
        std::string lane, read;
        // getting the number of lanes
        std::getline(file,lane);
        std::istringstream iss(lane);
        std::vector<std::vector <int>> rootread;
        while(iss>>read){
            std::vector<int> vecaux;
            vecaux.push_back(std::stoi(read));
            rootread.push_back(vecaux);
        }
        while (std::getline(file,lane)){
            std::istringstream iss(lane);
            for (int j = 0; j<rootread.size(); j++){
                iss>>read;
                rootread[j].push_back(std::stoi(read));
            }
        }
        conffile.push_back(rootread);
        file.close();
    }
    return conffile;
}


// this script loads the maximal speed configuration file. The result is indexed as [lane][cell]
std::vector<std::vector<int>> loadspeedfile(std::string dir, std::string root){
    std::vector<std::vector<int>> V;
    // Loading the configuration file
    std::string filename = dir + root +".txt";
    //std::cout<<filename<<std::endl;
    std::ifstream file = openconffile(filename);
    std::string line, read;
    // getting the number of lanes
    std::getline(file,line);
    std::istringstream iss(line);
    while(iss>>read){
        std::vector<int> vecaux;
        vecaux.push_back(std::stoi(read));
        V.push_back(vecaux);
    }
    while (std::getline(file,line)){
        std::istringstream iss(line);
        for (int j = 0; j<V.size(); j++){
                iss>>read;
                V[j].push_back(std::stoi(read));
        }
    }

    file.close();
    return V;
}

#endif
