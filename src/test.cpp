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

using namespace std;

int main (int argc, char **argv){
     auto t00 = std::chrono::high_resolution_clock::now();
    // The arguments list
    // 1 - seed
    // 2 - whether the animation data should be exported
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
    int seed = stoi(argv[1]);
    int print = stoi(argv[2]);
    std::default_random_engine generator (seed);
    srand(seed);
    cout<<"the seed has been set to: "<<seed<<endl;
    if ((print!=0) && (print!=1)){
        cout<<"The second argument is neither 0 or 1. Exiting the simulation."<<endl;
        return 0;
    }
    if(print==0){
        cout<<"Detailed simulation data will not be exported"<<endl;
    }
    else{
        cout<<"Detailed simulation data will be exported"<<endl;
    }

    /////////////////////////////////////////////////////////////////
    //// Creating random offsets for all the lines

    for (lineC & line: SYSTEM.Lines){
        line.offset = rand()%60;
    }

    ///////////////////////////////////////////////////////////////
    // Creating the bus array
    float Cfract = stof(argv[3]);
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

      ///////////////////////////////////////////////////////
    //// defining the output files
    
    string filename = "../results/sim_results_";
    // adding the line times
    for (auto line: SYSTEM.Lines){
        filename= filename +"_"+to_string(line.headway);
    }
    // adding the factor
    filename = filename +"_"+to_string(factor);
    // adding the fleet
    filename = filename +"_"+to_string(fleet);
    // adding the EW fraction
    ofstream animfile;
    string filename_anim;
    if (print == 1){ // in case the animation data is requested
        filename_anim = filename+"_"+to_string(int(100*Cfract))+"_anim.txt";
        animfile.open(filename_anim);
    }

    filename = filename +"_"+to_string(int(100*Cfract))+".txt";


    //cout<<"Defined all the simulation parameters"<<endl; 
    /////////////////////////////////////////////////////////
    // performing the simulation
    for (int TIME=4*3600; TIME<10*3600;TIME++){
        // Inserting the passengers
        //if (TIME%100==0){
        //std::cout<<TIME<<std::endl;}
        
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

        populate(TIME, BusesPar, SYSTEM, Queues, Parked);
        sortbuses(BusesPar, index);
        calculategaps(BusesPar, EL, SYSTEM);
        buschangelane(BusesPar,LC, RC, EL, TIME);
        calculategaps(BusesPar, EL, SYSTEM);
        busadvance(BusesPar,SYSTEM,TIME,Nactivepass,passsp,BusesPassengers, StationPassengers,Passengers, Parked, V,  routeMatrix, weightMatrix, generator, bussp, cost);
        for (auto &tl: SYSTEM.Tlights){
            tl.updatephase();
        }
        getPassengerFlowSpeedOccFast(BusesPar,flow,occ,Nactivepass,ncounts);
        // exporting the data in case of the animation data was requested
        if (print == 1){
            for (int i =0; i<BusesPar[0].size(); i++){
                animfile<<TIME<<" ";
                for (int j = 0; j<Nparam; j++){
                    animfile<<BusesPar[j][i]<<" ";
                }
            animfile<<endl;
            }
        }
    /*    if (TIME%900 == 0){
            std::cout<<"Parqueo: "<<Parked[0].size()<<" "<<Parked[1].size()<<std::endl;
            std::cout<<"Filas: "<<Queues[0].size()<<" "<<Queues[1].size()<<std::endl;
        }*/
    }
    // calculating the average time a function takes
/*
    // insert_pass time
    double sum = std::accumulate(insertpass_time.begin(), insertpass_time.end(), 0.0);
    double mean = sum / insertpass_time.size();

    double sq_sum = std::inner_product(insertpass_time.begin(), insertpass_time.end(), insertpass_time.begin(), 0.0);
    double stdev = std::sqrt(sq_sum / insertpass_time.size() - mean * mean);
    std::cout<<"insert passengers "<<mean<<"+/-"<<stdev<<std::endl;
    
    // insert_pass time
    sum = std::accumulate(populate_time.begin(), populate_time.end(), 0.0);
    mean = sum / populate_time.size();

    sq_sum = std::inner_product(populate_time.begin(), populate_time.end(), populate_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / populate_time.size() - mean * mean);
    std::cout<<"populate buses "<<mean<<"+/-"<<stdev<<std::endl;

    //calculategaps_time
    sum = std::accumulate(calculategaps_time.begin(), calculategaps_time.end(), 0.0);
    mean = sum / calculategaps_time.size();

    sq_sum = std::inner_product(calculategaps_time.begin(), calculategaps_time.end(), calculategaps_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / calculategaps_time.size() - mean * mean);
    std::cout<<"calculate gaps "<<mean<<"+/-"<<stdev<<std::endl;

    //sort_time
    sum = std::accumulate(sort_time.begin(), sort_time.end(), 0.0);
    mean = sum / sort_time.size();

    sq_sum = std::inner_product(sort_time.begin(), sort_time.end(), sort_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / sort_time.size() - mean * mean);
    std::cout<<"sort buses "<<mean<<"+/-"<<stdev<<std::endl;

    //change_time
    sum = std::accumulate(change_time.begin(), change_time.end(), 0.0);
    mean = sum / change_time.size();

    sq_sum = std::inner_product(change_time.begin(), change_time.end(), change_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / change_time.size() - mean * mean);
    std::cout<<"change lane buses "<<mean<<"+/-"<<stdev<<std::endl;

    //advance_time
    sum = std::accumulate(advance_time.begin(), advance_time.end(), 0.0);
    mean = sum / advance_time.size();

    sq_sum = std::inner_product(advance_time.begin(), advance_time.end(), advance_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / advance_time.size() - mean * mean);
    std::cout<<"advance buses "<<mean<<"+/-"<<stdev<<std::endl;

    //traffic lights time
    sum = std::accumulate(tls_time.begin(), tls_time.end(), 0.0);
    mean = sum / tls_time.size();

    sq_sum = std::inner_product(tls_time.begin(), tls_time.end(), tls_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / tls_time.size() - mean * mean);
    std::cout<<"traffic lights "<<mean<<"+/-"<<stdev<<std::endl;

    //calculation_time
    sum = std::accumulate(calculation_time.begin(), calculation_time.end(), 0.0);
    mean = sum / calculation_time.size();

    sq_sum = std::inner_product(calculation_time.begin(), calculation_time.end(), calculation_time.begin(), 0.0);
    stdev = std::sqrt(sq_sum / calculation_time.size() - mean * mean);
    std::cout<<"calculation "<<mean<<"+/-"<<stdev<<std::endl;
*/

    /*
    cout<<"Buses in the system: "<<BusesPar[0].size()<<endl;
    for (int i = 0; i< BusesPar[0].size(); i++){
            cout<<BusesPar[0][i]<<" "<<BusesPar[13][i]<<" "<<BusesPar[10][i]<<" "<<BusesPar[7][i]<<endl;
        }
    cout<<"Queues at the portals: "<<Queues[0].size()<<" "<<Queues[1].size()<<endl;

    cout<<"Number of lanes"<<EL[0][0].size()<<endl;
    cout<<"Number of lanes"<<EL[0].size()<<endl;
*/
    cout<<Nactivepass<<endl;
    cout<<passcount<<endl;
/*
    for (int i=0; i<SYSTEM.Stations.size(); i++){
        std::cout<<SYSTEM.Stations[i].name<<" "<<StationPassengers[i].size()<<std::endl;
    }*/

       /////////////////////////////////////////////////////////
    // calculating the speed for the passengers in the buses
    for (int i = 0; i<BusesPar[0].size(); i++){ // we scan over the buses
        int busID=BusesPar[13][i];
        for (int j = 0; j<BusesPassengers[busID].size(); j++){ // we scan over all passengers in the bus
            //std::cout<< BusesPassengers[busID][j] << " " << BusesPar[0][i] <<std::endl;
            int passID = BusesPassengers[busID][j];
            passsp+=fabs(Passengers[passID][3] + BusesPar[0][i]-SYSTEM.Stations[Passengers[passID][0]].stop_pos[0])/(10*3600-1-Passengers[passID][2]);
        
        }   
        
    }

    passsp=passsp/passcount;
    //std::cout<<"Velocidad pasajeros: " <<passsp <<std::endl;
    
    /////////////////////////////////////////////////////////
    // Calculating the bus speed
    // We first calculate the speed for the currently active buses
    int total_distance;
    for (int i =0; i<BusesPar[0].size(); i++){
        total_distance = SYSTEM.Lines[BusesPar[10][i]].end - SYSTEM.Lines[BusesPar[10][i]].origin;
        for (int j = 0; j<BusesPar[22][i]; j++){
                total_distance-=SYSTEM.Breaks[SYSTEM.Lines[BusesPar[10][i]].breaks[j]][2]-SYSTEM.Breaks[SYSTEM.Lines[BusesPar[10][i]].breaks[j]][0];
            }
        if (BusesPar[18][i]!=10*3600-1){ //we dont take into account buses just released
            bussp.push_back(float(total_distance/(10*3600-1-BusesPar[14][i])));
            //cout<<bussp.back()<<" >0"<<endl;
            cost+=(10*3600-1-BusesPar[14][i]);
        }
    }

    double BSP = std::accumulate(bussp.begin(), bussp.end(), 0.0);
    BSP = BSP / bussp.size();

    //cout<<"BSP "<<BSP<<endl;
    /////////////////////////////////////////////////////////
    // normalizing the data
    cost = cost/3600.0; // en unidades de bus-h
    flow = flow/V[0].size()/ncounts;
    occ = occ/SYSTEM.Stations.size()/ncounts;
    /////////////////////////////////////////////////////////
    // exporting the data

    // opening the file
    ofstream outfile;
    outfile.open(filename, fstream::app);
    outfile<<seed<<" "<<flow<<" "<<passsp<<" "<<BSP<<" "<<occ<<" "<<cost<<endl;
    outfile.close();


    if (print == 1)
        animfile.close();

    auto t1 = std::chrono::high_resolution_clock::now();
    std::cout<<std::chrono::duration_cast<std::chrono::microseconds>(t1 - t00).count()<<std::endl;
    return 0;
}