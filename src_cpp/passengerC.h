#ifndef PASSENGER_C
#define PASSENGER_C

#include<array>
#include<vector>
#include <numeric>
#include"routeC.h"
#include"createsystem.h"
#include"parameters.h"
#include"rng.h"
#include <algorithm>
#include <cmath>


// This function tells the system to create a new passenger
void insertPassenger(std::vector<std::vector<int>> & STPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, int & PASSCOUNT, discreteC & INDIST, std::vector<discreteC> & ODDIST, int TIME, rngC & RNG, Stats & STATS){
    int originID= INDIST.sample(RNG);
    int destinationID = ODDIST[originID].sample(RNG);
    int pos_correction = 0;
    // Insert the passenger at the station
    STPASSENGERS[originID].push_back(PASSCOUNT);
    // Adding the passenger inforation to the Passenger Database
    // the format is [origin,destination, entertime, pos_correction, startpos, finalpos]
    PASSENGERS.push_back(std::array<int, Nparpass> {originID, destinationID, TIME, pos_correction, 0, 0});
    // increasing the passenger count
    PASSCOUNT++;
    STATS.st_entries[originID]++;
}


float boardingProbability(int capacity, int occupation, float rate){
    float prob = 1/(1+std::exp((occupation-capacity)/rate));
    return prob;
}


// This function makes the passenger board the bus
void boardPassenger(int passID, int busID, int stationID, int lineID, std::vector<std::vector<int>> &BUSPASSENGERS, std::vector<std::vector<int>> & STPASSENGERS){

    // we add the passenger to the bus list
    BUSPASSENGERS[busID].push_back(passID);
    // we remove the passenger from the station passenger list
    std::vector<int>::iterator position = std::find(STPASSENGERS[stationID].begin(), STPASSENGERS[stationID].end(), passID);
    if (position != STPASSENGERS[stationID].end()) // == myVector.end() means the element was not found
        STPASSENGERS[stationID].erase(position);
    else{
        std::cout<<"WARNING, passenger not found in Station Passengers when attempting to remove"<<std::endl;
    }
   // std::cout<<"Boarded passenger "<<passID<<" to bus with ID "<<busID<<std::endl;
}

void alightpassenger(int passID, int busID, int stationID, int TIME, int& Nactivepass, float & passsp, std::vector<std::vector<int>> & BUSPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, System & SYSTEM){
   // std::cout<<"Alightning passenger "<<passID<<" from bus with iD "<<busID<<std::endl;
    // We first remove the passenger form the bus list
    // we remove the passenger from the station passenger list
    std::vector<int>::iterator position = std::find(BUSPASSENGERS[busID].begin(), BUSPASSENGERS[busID].end(), passID);
    if (position != BUSPASSENGERS[busID].end()) // == myVector.end() means the element was not found
        BUSPASSENGERS[busID].erase(position);
    else{
        std::cout<<"WARNING, passenger not found in Buses Passengers when attempting to remove"<<std::endl;
    }


    // the number of active passengers is reduced
    Nactivepass--;
    // we add the passenger speed to the speed list
    // the correcion PASSENGERS[passID][3] is applied in case a bus has performed a jump
    passsp+=fabs(PASSENGERS[passID][3]+PASSENGERS[passID][5]-PASSENGERS[passID][4])/(TIME-PASSENGERS[passID][2]);
    return;
}

struct busdata
{
    int dwelltime;
    int busoccupation;
};

// This function must be called when a bus arrives at a station
auto busArriving(int busID, int buspos, int stationID, int lineID, int TIME, int &Nactivepass,  float &passsp, std::vector<std::vector<int>>& BUSPASSENGERS, std::vector<std::vector<int>>& STPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, System & SYSTEM, std::vector<std::vector<std::vector<double>>> & weightMatrix, int &busOcc, rngC & RNG, Stats & STATS){
    int destid;
    double weight;
    // first, all the alightning passengers are allowed to descend
    //looking for passengers to alight
    std::vector<int> toAlight;
    for (int i = 0; i<BUSPASSENGERS[busID].size(); i++){
            if (PASSENGERS[BUSPASSENGERS[busID][i]][1]==stationID){ // in case the passenger's next station is the current station
                toAlight.push_back(BUSPASSENGERS[busID][i]); // we enter the passenger to the descending list
        }
    }
    // to calculate the dwell time
    int npass = toAlight.size();
    // now we scan over the descending list
    for (int i =0; i<toAlight.size(); i++){
        // updating the final passenger position
        PASSENGERS[toAlight[i]][5] = buspos;
        // alight passenger
        alightpassenger(toAlight[i],busID,stationID,TIME,Nactivepass,passsp,BUSPASSENGERS,PASSENGERS, SYSTEM);
        busOcc--;
        STATS.st_alightings[stationID]++;
        STATS.delivered++;
        STATS.traveltime+=TIME-PASSENGERS[toAlight[i]][2];
    }

    // Then we board the bus subject to capacity constraints
    // we start by calculating the bus occupation
    std::vector<int> toBoard;
    std::vector<int> aux2 = STPASSENGERS[stationID]; // a copy of the passenger list
    for(int passid: aux2){
        // check whether the bus works for the passenger
        destid = PASSENGERS[passid][1]; // the destination of the passenger
        weight = weightMatrix[stationID][destid][lineID]; // we calculate the weight for the service to destination
        float dice = RNG.uniform(); // we throw the dice
        if (dice<weight){
            toBoard.push_back(passid);
        }
    }

    npass= npass + toBoard.size();
    // we scan over all the boarding passengers
    for(int i=0; i<toBoard.size(); i++){
        // we calculate the boarding probability
        float prob=boardingProbability(SYSTEM.Par.BusCap,busOcc,SYSTEM.Par.BusRate);
        // we throw the dice
        float xi = RNG.uniform();
        if (xi<prob){
            boardPassenger(toBoard[i],busID,stationID,lineID,BUSPASSENGERS,STPASSENGERS);
            PASSENGERS[toBoard[i]][4] = buspos; // Updating the starting position
            busOcc++;
            STATS.st_boardings[stationID]++;
            STATS.ln_boardings[lineID]++;
        }
    }

    busdata Results;
    Results.dwelltime = std::min(SYSTEM.Par.MaxDwell,int(SYSTEM.Par.D0+SYSTEM.Par.D1*npass));
    Results.busoccupation = busOcc;
    return Results;
}
#endif
