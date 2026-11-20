#ifndef PARAMETERS_H
#define PARAMETERS_H

#include <array>

// The structural constants of the engine
const int Dt=1;     // This is the time unit
const int Dx=1;     // This is the space unit
const int Nparam = 28;    // Number of integer parameters for each bus
const int Nparpass = 6; // The number of parameters for a passenger

// The parameters of the model, they can be different for each simulation
struct SimParams
{
    std::array<int, 2> busL = {17, 27};    // The bus length, in cells, articulated and biarticulated
    float p = 0.15;          // The random breaking probability
    float p0 = 0.75;         // The random breaking probability when stopped
    int pentime = 5; // The number of seconds after leaving a stop where a bus cannot change lane
    int BusRate = 1; // the rate that modifies the boarding probability
    int BusCap = 100; // the total bus capacity
    int D0 = 10;           // The default dwell time
    float D1 = 0.5;         // The dwell time for boarding or alightning passenger
    int MaxDwell = 30;  // the maximum dwell time
    int insertion_period = 10; // passengers are inserted every insertion_period time steps
    int max_offset = 60; // the services without a fixed offset get a random one, smaller than max_offset
};

#endif
