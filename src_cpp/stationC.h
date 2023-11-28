#ifndef STATION_C
#define STATION_C

//#include "parameters.h"
#include <iostream>
#include <string>
#include <vector>


class stationC{
    public:
        std::string name;
        std::vector<int> stop_pos;
        std::vector<int> stop_biart;
        // Dummy Constructor
        stationC (){}
        // The real constructor
        stationC (std::string Name){ 
            name = Name;
        };
        // 
        std::string display (void);
        void addstop (int stoppos, int biart);
};


std::string stationC::display(void){
    std::string text= "Station "+name;
    text = text + ". With stops at: ";
    for(int i=0; i< stop_pos.size(); i++){
        text = text + std::to_string(stop_pos[i])+"("+std::to_string(stop_biart[i])+"), ";
    }
    return text;
}

void stationC::addstop(int stoppos, int biart){
    stop_pos.push_back(stoppos);
    stop_biart.push_back(biart);
}


#endif