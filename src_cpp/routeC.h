#ifndef ROUTE_C
#define ROUTE_C

#include <algorithm>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <array>
#include <cstdlib>
#include "parameters.h"
#include "createsystem.h"


// This function reads the route matrix file and returns the weight of each service for each pair of stations, indexed as [origin][destination][service]
std::vector<std::vector<std::vector<double>>> readRouteWeights(std::string filename, int nstations, int nlines){
    // We create the weight matrix, filled with zeros
    std::vector<std::vector<std::vector<double>>> weights (nstations, std::vector<std::vector<double>> (nstations, std::vector<double> (nlines, 0)));
    // openning the file
    std::ifstream file = openconffile(filename);
    std::string str;
    int ori, des, nroutes, nstops, line;
    double weight;
    while (std::getline(file,str)){
        // retrieving the origin and destination stations
        std::istringstream iss(str);
        iss>>ori>>des;
        // now retrieving the number of routes
        std::getline(file,str);
        nroutes = std::stoi(str);
        for (int i=0;i<nroutes;i++){
            std::getline(file,str); // we scan the weight
            weight = std::stod(str);
            std::getline(file,str); // we scan the route information
            std::istringstream iss(str);
            iss>>line>>nstops;
            weights[ori][des][line] = weight;
        }
    }
    file.close();
    return weights;
}

// For each pair of stations the weights are normalized by the largest one, the best service has a weight of one
std::vector<std::vector<std::vector<double>>> normalizeRouteWeights (std::vector<std::vector<std::vector<double>>> weights){
    int nstations = weights.size();
    for (int i = 0; i<nstations; i++){
        for (int j = 0; j<nstations; j++){
            if (weights[i][j].empty()){
                continue;
            }
            // we find the maximum element
            double max = *std::max_element(weights[i][j].begin(),weights[i][j].end());
            // we divide all elements by the maximum only in case max > 0
            if (max > 0){
                for (double &w: weights[i][j]){
                    w = w/max;
                }
            }
        }
    }
    return weights;
}


std::vector<double> readInputProfile(std::string filename){
    std::vector<double> IN;
    std::ifstream file = openconffile(filename);
    std::string str, number;
    while (std::getline(file,str)){
        IN.push_back(stod(str));
    }
    file.close();
    return IN;
}

std::vector<std::vector<double>> readODmatrix(std::string filename, int nstations){
    // initializing the matrix
    std::vector<std::vector<double>> ODmatrix (nstations, std::vector<double> (nstations, 0));

    std::ifstream file = openconffile(filename);
    std::string str, ori, des, number;
    while (std::getline(file,str)){
        std::istringstream iss(str);
        iss>>ori>>des>>number;
        ODmatrix[stoi(ori)][stoi(des)]=stod(number);
    }
    file.close();
    return ODmatrix;
}

#endif
