#include "busC.h"
#include "createsystem.h"
#include "parameters.h"
#include "passengerC.h"
#include "routeC.h"
#include "tlC.h"

#include <numeric>
#include <chrono>
#include <iostream>
#include <vector>
#include <array>
#include <deque>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace std;

struct sim_results
{
    double BSP;
    float flow;
    float passp;
    float occ;
    float cost;
    int queues;
    vector<array<int, Nparam+1>> BusData; // the detailed bus information
};

int add(int i, int j) {
    return i + j;
}


sim_results simulate (int seed, int print, float Cfract){
    // The arguments list
    // 1 - seed
    // 2 - whether the animation data should be exported [0 or 1]
    // 3 - CubaFract, the fraction of the total fleet initially in Cuba
    std::string stationlist = "../conf/station_list.txt";
    std::string stationdefinition = "../conf/station_definition.txt";
    std::string tldefinition = "../conf/traffic_light_list.txt";
    std::string servicelist = "../conf/service_list.txt";
    std::string servicedefinition = "../conf/service_definition.txt";
    std::string servicedata = "../conf/service_data.txt";
    std::string breaksdef = "../conf/breaks_list.txt";
    std::string servicebreaks = "../conf/service_breaks.txt";
    std::string servicetls = "../conf/service_traffic_lights.txt";
    std::string servicechanges = "../conf/service_changes.txt";

    System SYSTEM;
    //cout<<servicefile<<endl;
    SYSTEM = createsystem(stationlist, stationdefinition, tldefinition, servicelist, servicedefinition, servicedata, servicetls, breaksdef, servicebreaks, servicechanges);
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
    std::vector<std::vector<int>> V;
    V = loadspeedfile(root);

    // Load the passenger configuration files: OD_matrix, RouteMatrix
    std::string rmfile = "../conf/RouteMatrix.txt";
    std::string odfile = "../conf/OD_matrix.txt";
    std::string infile = "../conf/IN.txt";
    std::vector<std::vector<std::vector<routeC>>> routeMatrix;
    std::vector<std::vector<std::vector<double>>> weightMatrix;
    std::vector<std::vector<double>> ODmatrix;
    std::vector<double> IN;

    
    routeMatrix = readMatrixFile(rmfile, SYSTEM);
    ODmatrix = readODmatrix(odfile,SYSTEM);
    IN = readInputProfile(infile);
    weightMatrix = createRouteWeights (routeMatrix, SYSTEM);

    // Creating the passenger entrance distribution
    std::discrete_distribution<int> INdist (IN.begin(), IN.end());

    // Creating the passenger destination distribution
    std::vector<std::discrete_distribution<int>> ODdist;
    for (int i =0; i< SYSTEM.Stations.size(); i++){
        ODdist.push_back(std::discrete_distribution<int> (ODmatrix[i].begin(), ODmatrix[i].end()));
    }

    //cout<<"Read all the configuration files, the system is created"<<endl;

    ////////////////////////////////////////////////////////////////////////
    //Setting the argument information
    ////////////////////////////////////////////////////////////////////////
    std::default_random_engine generator (seed);
    srand(seed);
    //cout<<"the seed has been set to: "<<seed<<endl;
    if ((print!=0) && (print!=1)){
        cout<<"The second argument is neither 0 or 1. Exiting the simulation."<<endl;
        exit;
    }

    /////////////////////////////////////////////////////////////////
    //// Creating random offsets for all the lines

    for (lineC & line: SYSTEM.Lines){
        line.offset = rand()%60;
    }

    ///////////////////////////////////////////////////////////////
    // Creating the bus array
    int fCuba = int(fleet*Cfract);
    int fDosq = fleet-fCuba;
    vector<int> index; // required to order the buses
    array<vector<int>,2> Parked;  //0 for Cuba, 1 for Dosquebradas
    array<vector<int>,Nparam> BusesPar; // the buses information
    array<deque<int>,2> Queues; // 0 for Cuba, 1 for Dosquebradas
    initializeBusArray(Parked, fCuba, fDosq); // initializing the parked buses list


    ///////////////////////////////////////////////////////////////
    // Creating the passengers lists
    array<vector<int>, fleet> BusesPassengers; // The list of passenger in each bus
    vector<vector<int>> StationPassengers;  // The number of passenger in each station
    for (int i =0; i< SYSTEM.Stations.size(); i++){
        vector<int> vectoraux;
        StationPassengers.push_back(vectoraux);
    }
    vector<array<int, Nparpass>> Passengers; // All passenger's information

    
    ///////////////////////////////////////////////////////////////
    // the simulation parameters

    int Nactivepass = 0; // number of active passengers in the system
    int passcount = 0;  // number of total passengers entering the system
    float passsp = 0; // average passenger speed
    float cost = 0; // total operation cost, in bus-DT
    float flow = 0; // average passenger flow in the system
    float occ = 0; // average station occupation
    int ncounts =0; // number of times the flow and the occupation have been measured
    vector<float> bussp; // the vector with the average speed of a bus
    array<int, Nparam+1> auxdata;
    vector<array<int, Nparam+1>> printdata; // the detailed bus information

    //cout<<"Defined all the simulation parameters"<<endl; 
    int initial_hour = 4;
    int final_hour = 9;
    /////////////////////////////////////////////////////////
    // performing the simulation
    for (int TIME=initial_hour*3600; TIME<final_hour*3600;TIME++){
        // Inserting the passengers
        //if (TIME%100==0){
        //std::cout<<TIME<<std::endl;}
        //std::cout<<"Inició el tiempo "<<TIME<<std::endl;
        if (TIME%10==0){
            std::poisson_distribution<int> distribution (getPassengersDemand(factor,TIME));
            int npass = distribution(generator);
            //cout<<npass<<endl;
            Nactivepass+=npass;
            
            for (int j=0; j<npass;j++){
               insertPassenger(StationPassengers, Passengers, passcount, routeMatrix, INdist, ODdist, TIME, generator, SYSTEM.Lines.size());
            }
            
        }
        
        // inserting the buses
        //cout<<t<<endl;
        /*
        if (TIME==4*3600){
            createbus(TIME, 1, BusesPar, SYSTEM, Queues, Parked);
           // createbus(TIME, 2, BusesPar, SYSTEM, Queues, Parked);
        }*/
        //std::cout<<"inicio el tiempo"<<std::endl;
        populate(TIME, BusesPar, SYSTEM, Queues, Parked);
        //std::cout<<"inserto buses"<<std::endl;
        sortbuses(BusesPar, index);
        //std::cout<<"ordeno buses"<<std::endl;
        calculategaps(BusesPar, EL, SYSTEM);
        //std::cout<<"gaps"<<std::endl;
        buschangelane(BusesPar,LC, RC, EL, TIME);
        //std::cout<<"cambios de carril"<<std::endl;
        calculategaps(BusesPar, EL, SYSTEM);
        //std::cout<<"gaps2"<<std::endl;
        busadvance(BusesPar,SYSTEM,TIME,Nactivepass,passsp,BusesPassengers, StationPassengers,Passengers, Parked, V,  routeMatrix, weightMatrix, generator, bussp, cost);
        //std::cout<<"movio el bus"<<std::endl;
        for (auto &tl: SYSTEM.Tlights){
            tl.updatephase();
        }
        getPassengerFlowSpeedOccFast(BusesPar,flow,occ,Nactivepass,ncounts);
        // exporting the data in case of the animation data was requested
        if (print == 1){
            auxdata[0] = TIME;
            for (int i =0; i<BusesPar[0].size(); i++){
                for (int j = 0; j<Nparam; j++){
                    auxdata[j+1] = BusesPar[j][i];
                }
                printdata.push_back(auxdata);
            }
        }
        //std::cout<<"terminó el tiempo"<<std::endl;
    }

   /* for (int i = 0; i<SYSTEM.Stations.size();i++){
        std::cout<<i<<" "<<SYSTEM.Stations[i].name<<" "<<StationPassengers[i].size()<<std::endl;
    }*/

   // std::cout<<"Pasajeros activos "<<Nactivepass<<std::endl;
    //std::cout<<"Pasajeros totales "<<passcount<<std::endl;

   // // Priting the detail of the passengers at the stations
    //for (int passid=0; passid<Passengers.size();passid++){
    //        std::cout<<passid<<" "<<Passengers[passid][0]<<" "<<Passengers[passid][1]<<" "<<Passengers[passid][2]<<" "<<Passengers[passid][3]<<std::endl;
    //}

    // Printing the details of the passengers at a given station
    /*int stid = 6;
    for (int i=0; i<StationPassengers[stid].size(); i++ ){
        int passid = StationPassengers[stid][i];
        std::cout<<passid<<" "<<Passengers[passid][0]<<" "<<Passengers[passid][1]<<" "<<Passengers[passid][2]<<" "<<Passengers[passid][3]<<std::endl;
    }*/

    /////////////////////////////////////////////////////////
    // calculating the speed for the passengers in the buses
    
    for (int i = 0; i<BusesPar[0].size(); i++){ // we scan over the buses
        int busID=BusesPar[13][i];
        for (int j = 0; j<BusesPassengers[busID].size(); j++){ // we scan over all passengers in the bus
            //std::cout<< BusesPassengers[busID][j] << " " << BusesPar[0][i] <<std::endl;
            int passID = BusesPassengers[busID][j];
            passsp+=fabs(Passengers[passID][3] + BusesPar[0][i]-SYSTEM.Stations[Passengers[passID][0]].stop_pos[0])/(final_hour*3600-1-Passengers[passID][2]);
        
        }   
        
    }

    passsp=passsp/passcount;
    //std::cout<<"Velocidad pasajeros: " <<passsp <<std::endl;
    
    /////////////////////////////////////////////////////////
    // Calculating the bus speed
    // We first calculate the speed for the currently active buses
    int total_distance;
    for (int i =0; i<BusesPar[0].size(); i++){
        total_distance = BusesPar[0][i] - SYSTEM.Lines[BusesPar[10][i]].origin;
        for (int j = 0; j<BusesPar[22][i]; j++){
                total_distance-=SYSTEM.Breaks[SYSTEM.Lines[BusesPar[10][i]].breaks[j]][2]-SYSTEM.Breaks[SYSTEM.Lines[BusesPar[10][i]].breaks[j]][0];
            }
        if (BusesPar[14][i]!=final_hour*3600-1){ //we dont take into account buses just released
            bussp.push_back(float(total_distance/(final_hour*3600-1-BusesPar[14][i])));
            //cout<<bussp.back()<<" >0"<<endl;
            cost+=(final_hour*3600-1-BusesPar[14][i]);
        }
    }
    double BSP = std::accumulate(bussp.begin(), bussp.end(), 0.0);
    BSP = BSP / bussp.size();

    /////////////////////////////////////////////////////////
    // normalizing the data
    cost = cost/3600.0; // en unidades de bus-h
    flow = flow/(Ends[0]-Origins[0]+Ends[1]-Origins[1])/ncounts;
    occ = occ/SYSTEM.Stations.size()/ncounts;
    /////////////////////////////////////////////////////////
    // exporting the data

    sim_results RESULTS;
    RESULTS.BSP = BSP;
    RESULTS.flow = flow;
    RESULTS.cost = cost;
    RESULTS.occ = occ;
    RESULTS.passp = passsp;
    RESULTS.BusData = printdata;
    RESULTS.queues = Queues[0].size()+Queues[1].size()
    return RESULTS;
}


PYBIND11_MODULE(simulator, m) {
    py::class_<sim_results>(m, "sim_results")
        .def_readwrite("BSP", &sim_results::BSP)
        .def_readwrite("flow", &sim_results::flow)
        .def_readwrite("passp", &sim_results::passp)
        .def_readwrite("occ", &sim_results::occ)
        .def_readwrite("cost", &sim_results::cost)
        .def_readwrite("queue", &sim_results::queues)
        .def_readwrite("BusData", &sim_results::BusData);

        

    m.def("simulate", &simulate, "a complete system simulation");

}
