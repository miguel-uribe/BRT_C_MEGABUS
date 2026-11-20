#ifndef SIMULATION_H
#define SIMULATION_H

#include "busC.h"
#include "config.h"
#include "createsystem.h"
#include "parameters.h"
#include "passengerC.h"
#include "rng.h"
#include "routeC.h"
#include "tlC.h"

#include <array>
#include <cmath>
#include <deque>
#include <numeric>
#include <vector>

struct sim_results
{
    double BSP = 0; // the average bus speed, in cells per time step
    float flow = 0; // the average passenger flow
    float passp = 0; // the average passenger speed, in cells per time step
    float occ = 0; // the average number of passengers waiting at a station
    float cost = 0; // the total bus time, in bus-hours
    float queues = 0; // the average number of buses pending to be introduced
    std::vector<std::array<int, Nparam+1>> BusData; // the detailed bus information

    int passengers = 0; // the number of passengers that entered the system
    int delivered = 0; // the number of passengers that reached their destination
    double travel_time = 0; // the average travel time of the delivered passengers, including the waiting time
    // the information for each station
    std::vector<int> station_entries; // passengers that entered the system at the station
    std::vector<int> station_boardings; // passengers that boarded a bus at the station
    std::vector<int> station_alightings; // passengers that finished their trip at the station
    std::vector<double> station_waiting; // the average number of passengers waiting at the station
    // the information for each service
    std::vector<int> line_departures; // buses introduced
    std::vector<int> line_queued; // buses that were not available when they had to be introduced
    std::vector<int> line_arrivals; // buses that finished the service
    std::vector<double> line_trip_time; // the average time taken by the buses that finished the service
    std::vector<int> line_boardings; // passengers that boarded the service
};


// A simulation that can be advanced step by step. It owns a copy of its configuration.
class Simulation{
    public:
        System SYSTEM;
        std::vector<std::vector<std::vector<int>>> EL, LC, RC;
        std::vector<std::vector<int>> V;
        std::vector<std::vector<std::vector<double>>> weightMatrix;
        std::vector<int> demand_times;
        std::vector<double> demand_means;
        int initial_time;
        int final_time;
        int TIME; // the next time step to be simulated
        bool record; // whether the detailed bus information is stored at each step

        rngC RNG;
        discreteC INdist; // the passenger entrance distribution
        std::vector<discreteC> ODdist; // the passenger destination distribution, for each origin

        // the buses
        std::vector<int> index; // required to order the buses
        std::vector<std::vector<int>> Parked; // the IDs of the buses parked at each depot
        std::array<std::vector<int>,Nparam> BusesPar; // the buses information
        std::vector<std::deque<int>> Queues; // the services waiting for a bus at each depot

        // the passengers
        std::vector<std::vector<int>> BusesPassengers; // The list of passenger in each bus
        std::vector<std::vector<int>> StationPassengers;  // The list of passengers in each station
        std::vector<std::array<int, Nparpass>> Passengers; // All passenger's information

        // the simulation parameters
        int Nactivepass = 0; // number of active passengers in the system
        int passcount = 0;  // number of total passengers entering the system
        float passsp = 0; // average passenger speed
        float cost = 0; // total operation cost, in bus-DT
        float flow = 0; // average passenger flow in the system
        float occ = 0; // average station occupation
        int ncounts =0; // number of times the flow and the occupation have been measured
        std::vector<float> bussp; // the vector with the average speed of a bus
        std::vector<std::array<int, Nparam+1>> printdata; // the detailed bus information
        int av_queue = 0; // the average service queue length
        int queue_cont = 0; //
        Stats STATS;

        Simulation(const SimConfig & CONF, int seed, bool RECORD): RNG(seed){
            validateconfig(CONF);
            SYSTEM = CONF.system;
            EL = CONF.EL;
            LC = CONF.LC;
            RC = CONF.RC;
            V = CONF.V;
            weightMatrix = normalizeRouteWeights(CONF.route_weights);
            demand_times = CONF.demand_times;
            demand_means = CONF.demand_means;
            initial_time = CONF.initial_time;
            final_time = CONF.final_time;
            TIME = initial_time;
            record = RECORD;

            // the positions of the stops of each service
            for (lineC & line: SYSTEM.Lines){
                line.setstopx(line.stationIDs, line.wagons, SYSTEM.Stations);
            }

            // Creating the passenger distributions
            INdist = discreteC(CONF.IN);
            for (int i =0; i< SYSTEM.Stations.size(); i++){
                ODdist.push_back(discreteC(CONF.OD[i]));
            }

            // Creating random offsets for all the lines without a fixed one
            for (lineC & line: SYSTEM.Lines){
                if (line.offset < 0){
                    line.offset = RNG.below(SYSTEM.Par.max_offset);
                }
            }

            // Creating the bus array
            int fleet = 0;
            for (depotC & depot: SYSTEM.Depots){
                fleet += depot.initial_buses;
            }
            Parked.resize(SYSTEM.Depots.size());
            Queues.resize(SYSTEM.Depots.size());
            initializeBusArray(Parked, SYSTEM); // initializing the parked buses list

            // Creating the passengers lists
            BusesPassengers.resize(fleet);
            StationPassengers.resize(SYSTEM.Stations.size());
            STATS = Stats(SYSTEM.Stations.size(), SYSTEM.Lines.size());
        }

        bool done(void){
            return TIME >= final_time;
        }

        // Advancing the simulation one time step
        void step(void){
            if (done()){
                return;
            }
            // Inserting the passengers
            if (TIME%SYSTEM.Par.insertion_period==0){
                double mean = interpolate(demand_times, demand_means, TIME);
                int npass = 0;
                if (mean > 0){
                    npass = RNG.poisson(mean);
                }
                Nactivepass+=npass;

                for (int j=0; j<npass;j++){
                    insertPassenger(StationPassengers, Passengers, passcount, INdist, ODdist, TIME, RNG, STATS);
                }

                // queue count
                for (std::deque<int> & queue: Queues){
                    av_queue+=queue.size();
                }
                queue_cont++;
            }

            // inserting the buses
            populate(TIME, BusesPar, SYSTEM, Queues, Parked, RNG, STATS);
            sortbuses(BusesPar, index);
            calculategaps(BusesPar, EL, SYSTEM);
            buschangelane(BusesPar,LC, RC, EL, TIME);
            calculategaps(BusesPar, EL, SYSTEM);
            busadvance(BusesPar,SYSTEM,TIME,Nactivepass,passsp,BusesPassengers, StationPassengers,Passengers, Parked, Queues, V, weightMatrix, RNG, bussp, cost, STATS);
            for (auto &tl: SYSTEM.Tlights){
                tl.updatephase();
            }
            getPassengerFlowSpeedOccFast(BusesPar,flow,occ,Nactivepass,ncounts);
            // storing the data in case the detailed data was requested
            if (record){
                std::array<int, Nparam+1> auxdata;
                auxdata[0] = TIME;
                for (int i =0; i<BusesPar[0].size(); i++){
                    for (int j = 0; j<Nparam; j++){
                        auxdata[j+1] = BusesPar[j][i];
                    }
                    printdata.push_back(auxdata);
                }
            }
            // the statistics
            for (int i = 0; i<StationPassengers.size(); i++){
                STATS.st_waiting[i]+=StationPassengers[i].size();
            }
            STATS.nsteps++;
            TIME++;
        }

        // Advancing the simulation several time steps
        void steps(int n){
            for (int i = 0; i<n && !done(); i++){
                step();
            }
        }

        // Advancing the simulation until its final time
        void run(void){
            while (!done()){
                step();
            }
        }

        // The results of the simulation up to the current time, the detailed bus information is not included. The state of the simulation is not modified.
        sim_results results(void){
            sim_results RESULTS;
            // the last simulated time
            int last = TIME-1;

            /////////////////////////////////////////////////////////
            // calculating the speed for the passengers in the buses
            float totalpasssp = passsp;
            for (int i = 0; i<BusesPar[0].size(); i++){ // we scan over the buses
                int busID=BusesPar[13][i];
                for (int j = 0; j<BusesPassengers[busID].size(); j++){ // we scan over all passengers in the bus
                    int passID = BusesPassengers[busID][j];
                    totalpasssp+=fabs(Passengers[passID][3] + BusesPar[0][i]-SYSTEM.Stations[Passengers[passID][0]].stop_pos[0])/(last-Passengers[passID][2]);
                }
            }
            totalpasssp=totalpasssp/passcount;

            /////////////////////////////////////////////////////////
            // Calculating the bus speed
            // We add the speed of the currently active buses
            std::vector<float> totalbussp = bussp;
            float totalcost = cost;
            int total_distance;
            for (int i =0; i<BusesPar[0].size(); i++){
                total_distance = BusesPar[0][i] - SYSTEM.Lines[BusesPar[10][i]].origin;
                for (int j = 0; j<BusesPar[22][i]; j++){
                        total_distance-=SYSTEM.Breaks[SYSTEM.Lines[BusesPar[10][i]].breaks[j]][2]-SYSTEM.Breaks[SYSTEM.Lines[BusesPar[10][i]].breaks[j]][0];
                    }
                if (BusesPar[14][i]!=last){ //we dont take into account buses just released
                    totalbussp.push_back(float(total_distance)/(last-BusesPar[14][i]));
                    totalcost+=(last-BusesPar[14][i]);
                }
            }
            double BSP = std::accumulate(totalbussp.begin(), totalbussp.end(), 0.0);
            BSP = BSP / totalbussp.size();

            /////////////////////////////////////////////////////////
            // normalizing the data
            // the length of the system is the distance between the origins and the ends of the depots
            int length = 0;
            for (depotC & depot: SYSTEM.Depots){
                length += depot.end - depot.origin;
            }
            RESULTS.BSP = BSP;
            RESULTS.cost = totalcost/3600.0; // en unidades de bus-h
            RESULTS.flow = flow/length/ncounts;
            RESULTS.occ = occ/SYSTEM.Stations.size()/ncounts;
            RESULTS.passp = totalpasssp;
            if (queue_cont > 0){
                RESULTS.queues = av_queue/queue_cont;
            }

            /////////////////////////////////////////////////////////
            // the detailed statistics
            RESULTS.passengers = passcount;
            RESULTS.delivered = STATS.delivered;
            if (STATS.delivered > 0){
                RESULTS.travel_time = double(STATS.traveltime)/STATS.delivered;
            }
            RESULTS.station_entries = STATS.st_entries;
            RESULTS.station_boardings = STATS.st_boardings;
            RESULTS.station_alightings = STATS.st_alightings;
            for (long long waiting: STATS.st_waiting){
                RESULTS.station_waiting.push_back(STATS.nsteps > 0 ? double(waiting)/STATS.nsteps : 0.0);
            }
            RESULTS.line_departures = STATS.ln_departures;
            RESULTS.line_queued = STATS.ln_queued;
            RESULTS.line_arrivals = STATS.ln_arrivals;
            RESULTS.line_boardings = STATS.ln_boardings;
            for (int i = 0; i<STATS.ln_arrivals.size(); i++){
                RESULTS.line_trip_time.push_back(STATS.ln_arrivals[i] > 0 ? double(STATS.ln_triptime[i])/STATS.ln_arrivals[i] : 0.0);
            }
            return RESULTS;
        }
};

#endif
