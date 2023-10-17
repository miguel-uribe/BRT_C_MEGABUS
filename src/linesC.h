#ifndef LINE_C
#define LINE_C

//#include "parameters.h"
#include "stationC.h"
#include <cstdlib>
#include <vector>
#include <random>

class lineC{
    public:
        std::string name;  // The name of the bus service
        std::vector<int> stationIDs; // A list of station IDs where the service stops
        std::vector<int> wagons; // A list with the wagon ID at each station where the service stops
        std::vector<int> stopx; // A list with the positions of the stops where the service stops
        std::vector<int> stoptracks; // A list with the track where each stop is located
        int origin; // The position where buses serving this service are introduced
        int end; // The position where the service ends
        int or_lane; // The lane where the service starts
        int headway; // The average headway for the service
        int biart; // percentage of biarticulated buses
        int offset; // time offset to insert buses
        int change_pos = 1e6; // the position where the line changes to a different one
        int dest_line = -1; // the service to which the line transforms
        std::vector<int> breaks; // the origin of a break
        std::vector<int> tls; // The list of indices in traffic lights
        std::vector<int> tldir; // The list of traffic light directions
        std::vector<int> tltracks; // The list of tracks where each tl is located

        // Dummy constructor
        lineC(){}
        // real constructor
        lineC(std::string NAME){
            name = NAME;
        }

        std::string display (void);
        void setstopx(std::vector<int> &STATIONIDS, std::vector<int> &WAGONS, std::vector<stationC> &STATIONS);
        void addtl(int tl, int dir, int track);
};

std::string lineC::display (void){
    std::string text = "Line "+ name;
    text = text + ". Headway: " + std::to_string(headway);
    text = text + ". Origin: " + std::to_string(origin);
    text = text + ". End: " + std::to_string(end);
    text = text + ". Biarticulated proportion: " + std::to_string(biart);
    text = text + ". Stopping at stations: \n";
    for(int i =0; i<stationIDs.size(); i++){
        text = text + std::to_string(stationIDs[i]) +"("+std::to_string(wagons[i])+", "+std::to_string(stopx[i])+","+std::to_string(stoptracks[i])+")\n";
    }
    text = text + "Line Traffic lights: \n";
    for(int i =0; i<tls.size(); i++){
        text = text + std::to_string(tls[i]) +"("+std::to_string(tldir[i])+", "+std::to_string(tltracks[i])+")\n";
    }
    text = text + "Line Breaks: \n";
    for(int i =0; i<breaks.size(); i++){
        text = text + std::to_string(breaks[i])+"\n";
    }
    return text;
}


void lineC::setstopx(std::vector<int> &STATIONIDS, std::vector<int> &WAGONS, std::vector<stationC> &STATIONS){
    stationIDs = STATIONIDS;
    wagons = WAGONS;
    for (int i = 0; i< stationIDs.size(); i++){
        stopx.push_back(STATIONS[stationIDs[i]].stop_pos[wagons[i]]);
    }
}


void lineC::addtl(int tl, int dir, int track){
    tls.push_back(tl);
    tldir.push_back(dir);
    tltracks.push_back(track);
}

#endif