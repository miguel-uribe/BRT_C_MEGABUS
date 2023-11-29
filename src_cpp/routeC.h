#ifndef ROUTE_C
#define ROUTE_C

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <array>
#include <cstdlib>
#include "parameters.h"
#include "createsystem.h"
//#include "fleetsize.h"


class routeC{
    public:
        int originID;
        int destinationID;
        int nstops; // format [nstops, line, changingstatioon]
        int lineID;
        double weight;
        // the default constructor
        routeC(){
            originID=-1;
        }
        // The real constructor
        routeC(int ORIGINID, int DESTINATIONID, int NSTOPS, int LINEID, double WEIGHT){
            originID=ORIGINID;
            destinationID= DESTINATIONID;
            nstops = NSTOPS;
            lineID = LINEID;
            weight = WEIGHT;
        }
        std::string display(void);
};

std::string routeC::display(void){
    std::string text="Route from "+std::to_string(originID)+" to "+std::to_string(destinationID)+" with "+std::to_string(nstops)+" stops using service with ID "+std::to_string(lineID)+". The weight of this itinerary is "+ std::to_string(weight)+"\n";
    return text;
}


// This function reads the route matrix file and creates a matrix with all the information
std::vector<std::vector<std::vector<routeC>>> readMatrixFile(std::string filename, System SYSTEM){  
    int NStations = SYSTEM.Stations.size(); // Getting the number of stations
    std::vector<std::vector<std::vector<routeC>>> matrix; // defining the route matrix
    // initializing the vector
    for (int i = 0; i< NStations; i++){
        std::vector<std::vector<routeC>> aux;
            for (int j = 0; j< NStations; j++){ 
                std::vector<routeC> auxaux;
                aux.push_back(auxaux);
            }
        matrix.push_back(aux);
    }
    // openning the file
    std::ifstream file(filename);
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
            routeC route(ori,des,nstops,line,weight); // we create the new route
            matrix[ori][des].push_back(route);
        }
    } 
    file.close();
    return matrix;
}

// Create weight vector
std::vector<std::vector<std::vector<double>>> createRouteWeights (std::vector<std::vector<std::vector<routeC>>> rmatrix, System SYSTEM){
    // We create the weight matrix, filled with zeros
    std::vector<std::vector<std::vector<double>>> weights;
    int nstations = rmatrix.size();
    for(int i = 0; i<nstations; i++){
        std::vector<std::vector<double>> aux;
        for (int j = 0; j<nstations; j++){
            std::vector<double> empty (SYSTEM.Lines.size(), 0);
            aux.push_back(empty);
        }
        weights.push_back(aux);
    }
    // We update the weights
    for (int i = 0; i<nstations; i++){
        for (int j = 0; j<nstations; j++){
            for (routeC route: rmatrix[i][j]){
                double weight = route.weight; // we extract the weight
                int lineID = route.lineID; // We extract the lineID
                weights[i][j][lineID] = weight;  // we update the weight matrix
            }
        }
    }
    
    // We update the weights
    for (int i = 0; i<nstations; i++){
        for (int j = 0; j<nstations; j++){
            for (routeC route: rmatrix[i][j]){
                double weight = route.weight; // we extract the weight
                int lineID = route.lineID; // We extract the lineID
                weights[i][j][lineID] = weight;  // we update the weight matrix
            }
        }
    }

    // we normalize the weights
    for (int i = 0; i<nstations; i++){
        for (int j = 0; j<nstations; j++){
            // we find the maximum element
            double max = *max_element(weights[i][j].begin(),weights[i][j].end());
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
    std::ifstream file(filename);
    std::string str, number;
    double data;
    while (std::getline(file,str)){
        IN.push_back(stod(str));
    }
    file.close();
    return IN;
}

std::vector<std::vector<double>> readODmatrix(std::string filename, System SYSTEM){
    std::vector<std::vector<double>> ODmatrix;
    // initializing the matrix
    for (int i = 0; i<SYSTEM.Stations.size(); i++){
        std::vector<double> aux;
        for (int j = 0; j<SYSTEM.Stations.size(); j++){
            aux.push_back(0);
        }
        ODmatrix.push_back(aux);
    }

    std::ifstream file(filename);
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