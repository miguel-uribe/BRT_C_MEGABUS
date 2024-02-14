#ifndef PASSENGER_C
#define PASSENGER_C

#include<array>
#include<vector>
#include <numeric>
#include"routeC.h"
#include"createsystem.h"
#include"parameters.h"
#include <algorithm>
#include <cmath>




// The demand function, over time
double getPassengersDemand(int factor,int time){
    double demand=factor*(40/14874.2)*(1/(1+exp(-(time-6.8*3600)/(0.58*3600))))*(1.73*exp(-pow(((time-6.8*3600)/(1.29*3600)),2))+1);
    return demand;
}

// This function tells the system to create a new passenger
void insertPassenger(std::vector<std::vector<int>> & STPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, int & PASSCOUNT,  std::vector<std::vector<std::vector<routeC>>> & MATRIX, std::discrete_distribution<int> & INDIST, std::vector<std::discrete_distribution<int>> & ODDIST, int TIME, std::default_random_engine GEN, int nlines){
    int originID= INDIST(GEN);
    int destinationID = ODDIST[originID](GEN);
    int pos_correction = 0;
    // Insert the passenger at the station
    STPASSENGERS[originID].push_back(PASSCOUNT);
    // Adding the passenger inforation to the Passenger Database
    // the format is [origin,destination, entertime, pos_correction]
    PASSENGERS.push_back(std::array<int, Nparpass> {originID, destinationID, TIME, pos_correction});
    // increasing the passenger count
    PASSCOUNT++;
}


float boardingProbability(int capacity, int occupation, float rate){
    float prob = 1/(1+std::exp((occupation-capacity)/rate));
    return prob;
}   


// This function makes the passenger board the bus
void boardPassenger(int passID, int busID, int stationID, int lineID, std::array<std::vector<int>, fleet> &BUSPASSENGERS, std::vector<std::vector<int>> & STPASSENGERS){

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

void alightpassenger(int passID, int busID, int stationID, int TIME, int& Nactivepass, float & passsp, std::array<std::vector<int>, fleet> & BUSPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, System & SYSTEM){
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
    passsp+=fabs(PASSENGERS[passID][3]+SYSTEM.Stations[stationID].stop_pos[0]-SYSTEM.Stations[PASSENGERS[passID][0]].stop_pos[0])/(TIME-PASSENGERS[passID][2]);
    
    // we leave the function
    // std::cout<<MATRIX [PASSENGERS[passID][0]] [PASSENGERS[passID][1]][PASSENGERS[passID].back()].display()<<std::endl;
    // std::cout<<"passenger arrived at destination"<<std::endl;
    return;
}

struct busdata
{
    int dwelltime;
    int busoccupation;
};

// This function must be called when a bus arrives at a station
auto busArriving(int busID, int stationID, int lineID, int TIME, int &Nactivepass,  float &passsp, std::array<std::vector<int>, fleet>& BUSPASSENGERS, std::vector<std::vector<int>>& STPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, System & SYSTEM, std::vector<std::vector<std::vector<routeC>>> & routeMatrix, std::vector<std::vector<std::vector<double>>> & weightMatrix, int &busOcc){
    int destid;
    double weight;
    //std::cout<<busOcc<<" ";
    // first, all the alightning passengers are allowed to descend
   // std::cout<<"Alightning passengers from bus with ID "<<busID<<" with initial occupation "<<busOcc<<" arriving at station "<<stationID<<std::endl;
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
        // alight passenger 
        alightpassenger(toAlight[i],busID,stationID,TIME,Nactivepass,passsp,BUSPASSENGERS,PASSENGERS, SYSTEM);
        busOcc--;
       // std::cout<<"Passenger "<<toAlight[i]<<" descended"<<std::endl;
        // std::cout<<"The route is "<<MATRIX [PASSENGERS[toAlight[i]][0]] [PASSENGERS[toAlight[i]][1]] [PASSENGERS[toAlight[i]][5]].display()<<std::endl;
    }

    // Then we board the bus subject to capacity constraints
    // we start by calculating the bus occupation
   // std::cout<<"Boarding passengers"<<std::endl;
    std::vector<int> toBoard;
    std::vector<int> aux2 = STPASSENGERS[stationID]; // a copy of the passenger list
    for(int passid: aux2){
        // check whether the bus works for the passenger
        destid = PASSENGERS[passid][1];
        weight = weightMatrix[stationID][destid][lineID];
        float dice = ((double) rand() / (RAND_MAX)); // we throw the dice
        if (dice<weight){
            //std::cout<<weight<<std::endl;
            toBoard.push_back(passid);
        }
    }

    npass= npass + toBoard.size();
    // we scan over all the boarding passengers
    for(int i=0; i<toBoard.size(); i++){
        // we calculate the boarding probability
        float prob=boardingProbability(BusCap,busOcc,BusRate);
        // we throw the dice
        float xi = ((double) rand() / (RAND_MAX));
        if (xi<prob){
            boardPassenger(toBoard[i],busID,stationID,lineID,BUSPASSENGERS,STPASSENGERS);
            PASSENGERS[toBoard[i]][4] = lineID;
            busOcc++;
            // std::cout<<"Boarding passenger "<<passid<<" to bus with ID"<<busID<<". Passenger will descend at station "<<PASSENGERS[passid].back() <<std::endl;
            //std::cout<<"The route is "<<MATRIX [PASSENGERS[passid][0]] [PASSENGERS[passid][1]] [PASSENGERS[passid][5]].display()<<std::endl;
            
        }
    }

    busdata Results;
    Results.dwelltime = std::min(MaxDwell,int(D0+D1*npass));
    Results.busoccupation = busOcc;
    //std::cout<<Results.busoccupation<<" "<<busID<<" "<<stationID<<" "<<lineID<<" "<<npass<<" "<<Results.dwelltime<<" "<<npass<<std::endl;
    //std::cout<<"New bus occupation of bus with ID "<<busID<<": "<<busOcc<<" passengers"<<std::endl;
    return Results;
}
#endif