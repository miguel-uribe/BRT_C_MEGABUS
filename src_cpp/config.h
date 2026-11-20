#ifndef CONFIG_H
#define CONFIG_H

#include "createsystem.h"
#include "routeC.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

// The complete description of a simulation. It lives in memory: it can be loaded from the configuration files or built directly.
struct SimConfig
{
    System system; // the services, stations, traffic lights, breaks, depots and model parameters
    std::vector<std::vector<std::vector<int>>> EL; // distance to the end of the lane, indexed as [service][lane][cell]
    std::vector<std::vector<std::vector<int>>> LC; // whether a change to the left is allowed, indexed as [service][lane][cell]
    std::vector<std::vector<std::vector<int>>> RC; // whether a change to the right is allowed, indexed as [service][lane][cell]
    std::vector<std::vector<int>> V; // the maximal speed, indexed as [lane][cell]
    std::vector<std::vector<std::vector<double>>> route_weights; // the weight of each service to travel between two stations, indexed as [origin][destination][service]
    std::vector<std::vector<double>> OD; // the probability of each destination for each origin, indexed as [origin][destination]
    std::vector<double> IN; // the probability of entering the system at each station
    // the demand profile: the number of passengers entering the system per hour, linearly interpolated between the given times
    std::vector<int> demand_times;
    std::vector<double> demand_rates;
    int initial_time = 4*3600; // the time when the simulation starts
    int final_time = 9*3600; // the time when the simulation ends
};

// The value at time t of a profile defined by the points (T, Y), linearly interpolated and constant outside the range of T
double interpolate(const std::vector<int> & T, const std::vector<double> & Y, int t){
    if (T.empty()){
        return 0;
    }
    if (t <= T.front()){
        return Y.front();
    }
    if (t >= T.back()){
        return Y.back();
    }
    // the first point after t
    int k = std::upper_bound(T.begin(), T.end(), t) - T.begin() - 1;
    if (T[k] == t){
        return Y[k];
    }
    double fraction = double(t-T[k])/(T[k+1]-T[k]);
    return Y[k] + fraction*(Y[k+1]-Y[k]);
}


/////////////////////////////////////////////////////////////////////////////
// The values of the Megabus reference system that are not in the configuration files

const int megabus_fleet = 50; // The maximum numbers of moving buses
const int megabus_factor = 3600; // the average passenger influx to the system, pass/hour
const int megabus_initial_hour = 4;
const int megabus_final_hour = 9;

// The demand function, over time. It gives the average number of passengers entering the system every megabus_demand_period seconds
const int megabus_demand_period = 10;
double getPassengersDemand(int factor,int time){
    double demand=factor*(50/14958.5)*(1/(1+exp(-(time-6.8*3600)/(0.58*3600))))*(1.73*exp(-pow(((time-6.8*3600)/(1.29*3600)),2))+1);
    return demand;
}

// The configuration of the Megabus system, read from the configuration files in the given directory
SimConfig loadconfig(std::string dir){
    if (!dir.empty() && dir.back()!='/' && dir.back()!='\\'){
        dir = dir + "/";
    }
    SimConfig CONF;
    CONF.system = createsystem(dir+"station_list.txt", dir+"station_definition.txt", dir+"traffic_light_list.txt", dir+"service_list.txt", dir+"service_definition.txt", dir+"service_data.txt", dir+"service_traffic_lights.txt", dir+"breaks_list.txt", dir+"service_breaks.txt", dir+"service_changes.txt");
    // Reading the configuration files for each service
    CONF.EL = loadconffilekind(dir, "EL", CONF.system);
    CONF.LC = loadconffilekind(dir, "LC", CONF.system);
    CONF.RC = loadconffilekind(dir, "RC", CONF.system);
    CONF.V = loadspeedfile(dir, "V");
    // Load the passenger configuration files
    int nstations = CONF.system.Stations.size();
    int nlines = CONF.system.Lines.size();
    CONF.route_weights = readRouteWeights(dir+"RouteMatrix.txt", nstations, nlines);
    CONF.OD = readODmatrix(dir+"OD_matrix.txt", nstations);
    CONF.IN = readInputProfile(dir+"IN.txt");

    // The depots: Cuba and Dosquebradas. By default the entire fleet is in Cuba
    depotC cuba, dosquebradas;
    cuba.name = "Cuba";
    cuba.origin = 0;
    cuba.end = 30653;
    cuba.initial_buses = megabus_fleet;
    dosquebradas.name = "Dosquebradas";
    dosquebradas.origin = 19999;
    dosquebradas.end = 10943;
    dosquebradas.initial_buses = 0;
    CONF.system.Depots.push_back(cuba);
    CONF.system.Depots.push_back(dosquebradas);

    // The simulation window and the demand profile
    CONF.initial_time = megabus_initial_hour*3600;
    CONF.final_time = megabus_final_hour*3600;
    for (int TIME = CONF.initial_time; TIME <= CONF.final_time; TIME += CONF.system.Par.insertion_period){
        CONF.demand_times.push_back(TIME);
        CONF.demand_rates.push_back(getPassengersDemand(megabus_factor, TIME)*3600.0/megabus_demand_period);
    }
    return CONF;
}


/////////////////////////////////////////////////////////////////////////////
// Checking that a configuration is consistent, the engine does not check its indices during the simulation

void confcheck(bool condition, std::string message){
    if (!condition){
        throw std::invalid_argument("Invalid configuration: " + message);
    }
}

void validateconfig(const SimConfig & CONF){
    const System & SYSTEM = CONF.system;
    int nlines = SYSTEM.Lines.size();
    int nstations = SYSTEM.Stations.size();
    int ntls = SYSTEM.Tlights.size();
    int nbreaks = SYSTEM.Breaks.size();
    confcheck(nlines > 0, "there are no services");
    confcheck(nstations > 0, "there are no stations");
    confcheck(SYSTEM.Depots.size() > 0, "there are no depots");
    confcheck(CONF.final_time > CONF.initial_time, "final_time must be larger than initial_time");
    confcheck(SYSTEM.Par.insertion_period > 0, "insertion_period must be positive");
    confcheck(SYSTEM.Par.max_offset > 0, "max_offset must be positive");
    confcheck(SYSTEM.Par.BusRate != 0, "BusRate must not be zero");

    // the lane arrays
    confcheck(CONF.V.size() > 0 && CONF.V[0].size() > 0, "V is empty");
    int nlanes = CONF.V.size();
    int ncells = CONF.V[0].size();
    for (const std::vector<int> & lane: CONF.V){
        confcheck(lane.size() == ncells, "all the lanes in V must have the same number of cells");
    }
    const std::vector<std::vector<std::vector<int>>> * arrays[3] = {&CONF.EL, &CONF.LC, &CONF.RC};
    const std::string names[3] = {"EL", "LC", "RC"};
    for (int k = 0; k<3; k++){
        confcheck(arrays[k]->size() == nlines, names[k] + " must have one entry per service");
        for (const std::vector<std::vector<int>> & service: *arrays[k]){
            confcheck(service.size() == nlanes, names[k] + " must have the same number of lanes as V");
            for (const std::vector<int> & lane: service){
                confcheck(lane.size() == ncells, names[k] + " must have the same number of cells as V");
            }
        }
    }

    // the breaks
    for (const std::array<int, 4> & Break: SYSTEM.Breaks){
        confcheck(Break[0] >= 0 && Break[0] < ncells && Break[2] >= 0 && Break[2] < ncells, "a break has a position outside the system");
        confcheck(Break[1] >= 0 && Break[1] < nlanes && Break[3] >= 0 && Break[3] < nlanes, "a break has a lane outside the system");
    }

    // the stations
    for (const stationC & station: SYSTEM.Stations){
        confcheck(station.stop_pos.size() > 0, "station " + station.name + " has no stops");
        for (int pos: station.stop_pos){
            confcheck(pos >= 0 && pos < ncells, "station " + station.name + " has a stop outside the system");
        }
    }

    // the traffic lights
    for (const tlC & tl: SYSTEM.Tlights){
        confcheck(tl.durations.size() > 0, "traffic light " + tl.name + " has no phases");
        confcheck(tl.phases.size() == tl.durations.size(), "traffic light " + tl.name + " must have one duration per phase");
        for (const std::vector<int> & phase: tl.phases){
            confcheck(phase.size() == tl.positions.size(), "traffic light " + tl.name + " must have one state per direction in each phase");
        }
    }

    // the services
    for (const lineC & line: SYSTEM.Lines){
        std::string name = "service " + line.name;
        confcheck(line.headway > 0, name + " must have a positive headway");
        confcheck(line.origin >= 0 && line.origin < ncells, name + " starts outside the system");
        confcheck(line.end >= 0 && line.end < ncells, name + " ends outside the system");
        confcheck(line.or_lane >= 0 && line.or_lane < nlanes, name + " starts in a lane outside the system");
        confcheck(line.wagons.size() == line.stationIDs.size() && line.stoptracks.size() == line.stationIDs.size(), name + " must have one stop and one track per station");
        for (int i = 0; i < line.stationIDs.size(); i++){
            confcheck(line.stationIDs[i] >= 0 && line.stationIDs[i] < nstations, name + " stops at a station that does not exist");
            confcheck(line.wagons[i] >= 0 && line.wagons[i] < SYSTEM.Stations[line.stationIDs[i]].stop_pos.size(), name + " stops at a stop that does not exist");
            confcheck(line.stoptracks[i] >= 0 && line.stoptracks[i] <= line.breaks.size(), name + " has a stop in a track that does not exist");
        }
        confcheck(line.tldir.size() == line.tls.size() && line.tltracks.size() == line.tls.size(), name + " must have one direction and one track per traffic light");
        for (int i = 0; i < line.tls.size(); i++){
            confcheck(line.tls[i] >= 0 && line.tls[i] < ntls, name + " has a traffic light that does not exist");
            confcheck(line.tldir[i] >= 0 && line.tldir[i] < SYSTEM.Tlights[line.tls[i]].positions.size(), name + " has a traffic light direction that does not exist");
            confcheck(line.tltracks[i] >= 0 && line.tltracks[i] <= line.breaks.size(), name + " has a traffic light in a track that does not exist");
        }
        for (int breakID: line.breaks){
            confcheck(breakID >= 0 && breakID < nbreaks, name + " has a break that does not exist");
        }
        confcheck(line.dest_line < nlines, name + " changes into a service that does not exist");
        confcheck(line.dest_line >= 0 || line.change_pos >= ncells, name + " has a change position but no destination service");
    }

    // the depots
    for (const depotC & depot: SYSTEM.Depots){
        confcheck(depot.initial_buses >= 0, "depot " + depot.name + " has a negative number of buses");
    }

    // the passengers
    confcheck(CONF.IN.size() == nstations, "IN must have one entry per station");
    confcheck(CONF.OD.size() == nstations, "OD must have one row per station");
    for (const std::vector<double> & row: CONF.OD){
        confcheck(row.size() == nstations, "OD must have one column per station");
    }
    confcheck(CONF.route_weights.size() == nstations, "route_weights must have one entry per origin station");
    for (const std::vector<std::vector<double>> & origin: CONF.route_weights){
        confcheck(origin.size() == nstations, "route_weights must have one entry per destination station");
        for (const std::vector<double> & destination: origin){
            confcheck(destination.size() == nlines, "route_weights must have one entry per service");
        }
    }
    confcheck(CONF.demand_times.size() == CONF.demand_rates.size(), "demand_times and demand_rates must have the same size");
    confcheck(std::is_sorted(CONF.demand_times.begin(), CONF.demand_times.end()), "demand_times must be sorted");
    confcheck(std::adjacent_find(CONF.demand_times.begin(), CONF.demand_times.end()) == CONF.demand_times.end(), "demand_times must not have repeated values");
    for (double rate: CONF.demand_rates){
        confcheck(rate >= 0, "demand_rates must not be negative");
    }
    // a passenger must always have somewhere to enter and somewhere to go
    double totalin = 0;
    for (int i = 0; i < nstations; i++){
        confcheck(CONF.IN[i] >= 0, "IN must not be negative");
        totalin += CONF.IN[i];
        double totalod = 0;
        for (double probability: CONF.OD[i]){
            confcheck(probability >= 0, "OD must not be negative");
            totalod += probability;
        }
        confcheck(CONF.IN[i] == 0 || totalod > 0, "station " + SYSTEM.Stations[i].name + " receives passengers but has no destinations in OD");
    }
    confcheck(totalin > 0, "IN must have at least one positive entry");
}

#endif
