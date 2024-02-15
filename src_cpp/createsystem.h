#ifndef CREATE_SYSTEM
#define CREATE_SYSTEM

# include "linesC.h"
# include "parameters.h"
# include "stationC.h"
# include "tlC.h"
# include <vector>
# include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <sstream>
#include <string>

struct System
{
    std::vector<lineC> Lines;  
    std::vector<stationC> Stations;
    std::vector<tlC> Tlights;
    std::vector<std::array<int, 4>> Breaks;
};


auto createsystem(std::string stationlist, std::string stationdefinition, std::string tldefinition, std::string servicelist, std::string servicedefinitions, std::string servicedata, std::string servicetls, std::string breaksdef, std::string servicebreaks, std::string servicechange){
    
    // Creating the structure of the system
    System SYSTEM;
    
    // creating the list of stations in the system
    std::ifstream stationlist_f, stationdefinitions_f;
    stationlist_f.open(stationlist);
    stationdefinitions_f.open(stationdefinition);
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
    std::ifstream tllist_f;
    tllist_f.open(tldefinition);
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
    std::ifstream servicelist_f, servicedefinitions_f, servicedata_f, servicetls_f, servicebreaks_f, breaksdef_f, servicechanges_f;
    servicelist_f.open(servicelist);
    servicedefinitions_f.open(servicedefinitions);
    servicedata_f.open(servicedata);
    breaksdef_f.open(breaksdef);
    servicebreaks_f.open(servicebreaks);
    servicetls_f.open(servicetls);
    servicechanges_f.open(servicechange);
    
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


// this script loads the configuration files and creates the corresponding lane configuration when there are many different kinds of configuration files, the factor is a multiplying factor to be applied in case it is needed
std::vector<std::vector<std::vector<int>>> loadconffilekind(std::string root, System SYSTEM, float factor){
    std::vector<std::vector<std::vector<int>>> conffile;
    // Loading the configuration file for each service
    for (int i = 0; i < SYSTEM.Lines.size(); i++ ){
        std::string filename = "../conf/";
        filename = filename + root +"_"+SYSTEM.Lines[i].name+".txt";
        //std::cout<<filename<<std::endl;
        std::ifstream file(filename);
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


// this script loads the maximal speed configuration file
std::vector<std::vector<int>> loadspeedfile(std::string root){
    std::vector<std::vector<int>> V;
    // Loading the configuration file 
    std::string filename = "../conf/";
    filename = filename + root +".txt";
    //std::cout<<filename<<std::endl;
    std::ifstream file(filename);
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