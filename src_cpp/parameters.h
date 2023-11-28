#ifndef PARAMETERS_H
#define PARAMETERS_H

#include <array>

// This file defines all the system parameters
const int Dt=1;     // This is the time unit
const int Dx=1;     // This is the space unit
const  std::array<int, 2> busL = {17, 27};    // The bus length, equivalent to 30m
const float p=0.15;          // The random breaking probability
const float p0=0.75;         // The random breaking probability when stopped
const int Nparam = 28;    // Number of integer parameters for each bus
const int Nparpass = 4; // The number of parameters for a passenger
const int pentime = 5; // The number of seconds after leaving a stop where a bus cannot change lane
const int fleet = 50; // The maximum numbers of moving buses
const int factor = 3600; // the average passenger influx to the system, pass/hour
const int BusRate = 1; // the rate that modifies the boarding probability
const int BusCap = 100; // the total bus capacity
const int D0=10;           // The default dwell time
const float D1=0.5;         // The dwell time for boarding or alightning passenger
const int MaxDwell = 30;  // the maximum dwell time
int origins[2] = {0, 19999}; // the origin of buses in the system
int ends[2] = {10943,30653}; // the end of buses in the system

#endif