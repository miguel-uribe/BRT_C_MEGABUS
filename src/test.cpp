#include "createsystem.h"
#include "parameters.h"
#include "routeC.h"
#include "tlC.h"

#include <iostream>
#include <vector>

using namespace std;

int main (int argc, char **argv){
    std::string stationlist = "../conf/station_list.txt";
    std::string stationdefinition = "../conf/station_definition.txt";
    std::string tldefinition = "../conf/traffic_light_list.txt";
    std::string servicelist = "../conf/service_list.txt";
    std::string servicedefinition = "../conf/service_definition.txt";
    std::string servicedata = "../conf/service_data.txt";
    std::string servicebreaks = "../conf/service_breaks.txt";
    std::string servicetls = "../conf/service_traffic_lights.txt";

    System SYSTEM;
    //cout<<servicefile<<endl;
    SYSTEM = createsystem(stationlist, stationdefinition, tldefinition, servicelist, servicedefinition, servicedata, servicetls, servicebreaks);

    // Reading the configuration files for each service
    string root = "lanes";
    std::vector<std::vector<std::vector<int>>> lanes;
    lanes = loadconffilekind(root, SYSTEM, 1);

    root = "EL";
    std::vector<std::vector<std::vector<int>>> EL;
    EL = loadconffilekind(root, SYSTEM, 1.0/Dx);

    root = "LC";
    std::vector<std::vector<std::vector<int>>> LC;
    LC = loadconffilekind(root, SYSTEM, 1);

    root = "RC";
    std::vector<std::vector<std::vector<int>>> RC;
    RC = loadconffilekind(root, SYSTEM, 1);

    root = "V";
    std::vector<std::vector<std::vector<int>>> V;
    V = loadconffilekind(root, SYSTEM, 1.0*Dt/Dx);

    // Load the passenger configuration files: OD_matrix, RouteMatrix
    std::string rmfile = "../conf/RouteMatrix.txt";
    std::string odfile = "../conf/OD_matrix.txt";
    std::string infile = "../conf/IN.txt";
    std::vector<std::vector<std::vector<routeC>>> routeMatrix;
    std::vector<std::vector<double>> ODmatrix;
    std::vector<double> IN;

    
    routeMatrix = readMatrixFile(rmfile, SYSTEM);
    ODmatrix = readODmatrix(odfile,SYSTEM);
    IN = readInputProfile(infile);

    

    return 0;
}