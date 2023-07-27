#ifndef PARAMETERS_H
#define PARAMETERS_H

#include <array>

// This file defines all the system parameters
const int Dt=1;     // This is the time unit
const int Dx=1;     // This is the space unit
const  std::array<int, 2> busL = {17, 27};    // The bus length, equivalent to 30m
const float p=0.15;          // The random breaking probability
const float p0=0.75;         // The random breaking probability when stopped
const int Nparam = 18;    // Number of integer parameters for each bus
const int Nbool = 1;        // Number of boolean parameters for each bus
const int fleet = 500; // The maximum numbers of moving buses
//const int vsurr = (int) 9*Dt/Dx;

#endif