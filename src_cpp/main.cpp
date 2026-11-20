#include "busC.h"
#include "config.h"
#include "createsystem.h"
#include "parameters.h"
#include "passengerC.h"
#include "simulation.h"
#include "tlC.h"

#include <array>
#include <stdexcept>
#include <string>
#include <vector>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

namespace py = pybind11;
using namespace std;

// These lists are handled by reference in Python, so that their elements can be modified in place
PYBIND11_MAKE_OPAQUE(std::vector<lineC>);
PYBIND11_MAKE_OPAQUE(std::vector<stationC>);
PYBIND11_MAKE_OPAQUE(std::vector<tlC>);
PYBIND11_MAKE_OPAQUE(std::vector<depotC>);

// The names of the columns of the bus information
const std::vector<std::string> bus_columns = {
    "x", "lane", "speed", "gap_forward", "gap_forward_left", "gap_backward_left", "speed_backward_left",
    "next_stop_x", "next_station", "next_stop_index", "line", "stop_time", "dwell_time", "bus_id",
    "start_time", "length", "occupation", "gap_forward_right", "gap_backward_right", "speed_backward_right",
    "penalty_time", "advancing", "track", "next_tl_index", "next_tl_direction", "next_tl", "next_tl_x", "next_break_x"
};


// A complete simulation of the Megabus system, with the configuration files located in ../conf/
sim_results simulate (int seed, int print, float Cfract){
    // The arguments list
    // 1 - seed
    // 2 - whether the animation data should be exported [0 or 1]
    // 3 - CubaFract, the fraction of the total fleet initially in Cuba
    if ((print!=0) && (print!=1)){
        throw std::invalid_argument("The second argument must be either 0 or 1");
    }
    SimConfig CONF = loadconfig("../conf/");
    int fCuba = int(megabus_fleet*Cfract);
    int fDosq = megabus_fleet-fCuba;
    CONF.system.Depots[0].initial_buses = fCuba;
    CONF.system.Depots[1].initial_buses = fDosq;

    Simulation SIM (CONF, seed, print==1);
    {
        py::gil_scoped_release release;
        SIM.run();
    }
    sim_results RESULTS = SIM.results();
    RESULTS.BusData = std::move(SIM.printdata);
    return RESULTS;
}


PYBIND11_MODULE(simulator, m) {
    m.attr("BUS_COLUMNS") = bus_columns;

    py::class_<sim_results>(m, "sim_results")
        .def_readwrite("BSP", &sim_results::BSP)
        .def_readwrite("flow", &sim_results::flow)
        .def_readwrite("passp", &sim_results::passp)
        .def_readwrite("occ", &sim_results::occ)
        .def_readwrite("cost", &sim_results::cost)
        .def_readwrite("queue", &sim_results::queues)
        .def_readwrite("BusData", &sim_results::BusData)
        .def_readwrite("passengers", &sim_results::passengers)
        .def_readwrite("delivered", &sim_results::delivered)
        .def_readwrite("travel_time", &sim_results::travel_time)
        .def_readwrite("station_entries", &sim_results::station_entries)
        .def_readwrite("station_boardings", &sim_results::station_boardings)
        .def_readwrite("station_alightings", &sim_results::station_alightings)
        .def_readwrite("station_waiting", &sim_results::station_waiting)
        .def_readwrite("line_departures", &sim_results::line_departures)
        .def_readwrite("line_queued", &sim_results::line_queued)
        .def_readwrite("line_arrivals", &sim_results::line_arrivals)
        .def_readwrite("line_trip_time", &sim_results::line_trip_time)
        .def_readwrite("line_boardings", &sim_results::line_boardings);

    py::class_<SimParams>(m, "SimParams")
        .def(py::init<>())
        .def_readwrite("busL", &SimParams::busL)
        .def_readwrite("p", &SimParams::p)
        .def_readwrite("p0", &SimParams::p0)
        .def_readwrite("pentime", &SimParams::pentime)
        .def_readwrite("BusRate", &SimParams::BusRate)
        .def_readwrite("BusCap", &SimParams::BusCap)
        .def_readwrite("D0", &SimParams::D0)
        .def_readwrite("D1", &SimParams::D1)
        .def_readwrite("MaxDwell", &SimParams::MaxDwell)
        .def_readwrite("insertion_period", &SimParams::insertion_period)
        .def_readwrite("max_offset", &SimParams::max_offset);

    py::class_<lineC>(m, "Line")
        .def(py::init<>())
        .def(py::init<std::string>())
        .def_readwrite("name", &lineC::name)
        .def_readwrite("stationIDs", &lineC::stationIDs)
        .def_readwrite("wagons", &lineC::wagons)
        .def_readwrite("stoptracks", &lineC::stoptracks)
        .def_readonly("stopx", &lineC::stopx)
        .def_readwrite("origin", &lineC::origin)
        .def_readwrite("end", &lineC::end)
        .def_readwrite("or_lane", &lineC::or_lane)
        .def_readwrite("headway", &lineC::headway)
        .def_readwrite("biart", &lineC::biart)
        .def_readwrite("offset", &lineC::offset)
        .def_readwrite("change_pos", &lineC::change_pos)
        .def_readwrite("dest_line", &lineC::dest_line)
        .def_readwrite("breaks", &lineC::breaks)
        .def_readwrite("tls", &lineC::tls)
        .def_readwrite("tldir", &lineC::tldir)
        .def_readwrite("tltracks", &lineC::tltracks)
        .def("__repr__", &lineC::display);

    py::class_<stationC>(m, "Station")
        .def(py::init<>())
        .def(py::init<std::string>())
        .def_readwrite("name", &stationC::name)
        .def_readwrite("stop_pos", &stationC::stop_pos)
        .def_readwrite("stop_biart", &stationC::stop_biart)
        .def("__repr__", &stationC::display);

    py::class_<tlC>(m, "TrafficLight")
        .def(py::init<>())
        .def(py::init<std::string, int>())
        .def_readwrite("name", &tlC::name)
        .def_readwrite("directions", &tlC::directions)
        .def_readwrite("positions", &tlC::positions)
        .def_readwrite("lengths", &tlC::lengths)
        .def_readwrite("phases", &tlC::phases)
        .def_readwrite("durations", &tlC::durations)
        .def_readwrite("curr_phase", &tlC::curr_phase)
        .def_readwrite("phasetime", &tlC::phasetime)
        .def("__repr__", &tlC::display);

    py::class_<depotC>(m, "Depot")
        .def(py::init<>())
        .def_readwrite("name", &depotC::name)
        .def_readwrite("origin", &depotC::origin)
        .def_readwrite("end", &depotC::end)
        .def_readwrite("initial_buses", &depotC::initial_buses);

    py::bind_vector<std::vector<lineC>>(m, "LineList");
    py::bind_vector<std::vector<stationC>>(m, "StationList");
    py::bind_vector<std::vector<tlC>>(m, "TrafficLightList");
    py::bind_vector<std::vector<depotC>>(m, "DepotList");

    py::class_<SimConfig>(m, "SimConfig")
        .def(py::init<>())
        .def(py::init<const SimConfig &>(), "a copy of a configuration")
        .def_property_readonly("lines", [](SimConfig & CONF) -> std::vector<lineC> & {return CONF.system.Lines;}, py::return_value_policy::reference_internal)
        .def_property_readonly("stations", [](SimConfig & CONF) -> std::vector<stationC> & {return CONF.system.Stations;}, py::return_value_policy::reference_internal)
        .def_property_readonly("traffic_lights", [](SimConfig & CONF) -> std::vector<tlC> & {return CONF.system.Tlights;}, py::return_value_policy::reference_internal)
        .def_property_readonly("depots", [](SimConfig & CONF) -> std::vector<depotC> & {return CONF.system.Depots;}, py::return_value_policy::reference_internal)
        .def_property_readonly("params", [](SimConfig & CONF) -> SimParams & {return CONF.system.Par;}, py::return_value_policy::reference_internal)
        .def_property("breaks", [](SimConfig & CONF){return CONF.system.Breaks;}, [](SimConfig & CONF, std::vector<std::array<int, 4>> breaks){CONF.system.Breaks = breaks;})
        .def_readwrite("EL", &SimConfig::EL)
        .def_readwrite("LC", &SimConfig::LC)
        .def_readwrite("RC", &SimConfig::RC)
        .def_readwrite("V", &SimConfig::V)
        .def_readwrite("route_weights", &SimConfig::route_weights)
        .def_readwrite("OD", &SimConfig::OD)
        .def_readwrite("IN", &SimConfig::IN)
        .def_readwrite("demand_times", &SimConfig::demand_times)
        .def_readwrite("demand_rates", &SimConfig::demand_rates)
        .def_readwrite("initial_time", &SimConfig::initial_time)
        .def_readwrite("final_time", &SimConfig::final_time)
        .def("validate", [](const SimConfig & CONF){validateconfig(CONF);}, "raises ValueError if the configuration is not consistent");

    py::class_<Simulation>(m, "Simulation")
        .def(py::init<const SimConfig &, int, bool>(), py::arg("config"), py::arg("seed"), py::arg("record") = false)
        .def_readonly("time", &Simulation::TIME, "the next time step to be simulated")
        .def_readonly("initial_time", &Simulation::initial_time)
        .def_readonly("final_time", &Simulation::final_time)
        .def_property_readonly("done", &Simulation::done)
        // the simulations do not share any state, they can run in different threads at the same time
        .def("step", [](Simulation & SIM, int n){
            py::gil_scoped_release release;
            SIM.steps(n);
        }, py::arg("n") = 1, "advances the simulation n time steps")
        .def("run", [](Simulation & SIM){
            py::gil_scoped_release release;
            SIM.run();
        }, "advances the simulation until its final time")
        .def("results", &Simulation::results, "the results up to the current time")
        .def("buses", [](Simulation & SIM){
            // one row per bus, the columns are listed in BUS_COLUMNS
            int nbuses = SIM.BusesPar[0].size();
            py::array_t<int> data ({nbuses, Nparam});
            auto view = data.mutable_unchecked<2>();
            for (int i = 0; i<nbuses; i++){
                for (int j = 0; j<Nparam; j++){
                    view(i,j) = SIM.BusesPar[j][i];
                }
            }
            return data;
        }, "the current information of the buses in the system, one row per bus")
        .def("bus_data", [](Simulation & SIM){
            // one row per bus and time step, the first column is the time
            int nrows = SIM.printdata.size();
            py::array_t<int> data ({nrows, Nparam+1});
            auto view = data.mutable_unchecked<2>();
            for (int i = 0; i<nrows; i++){
                for (int j = 0; j<Nparam+1; j++){
                    view(i,j) = SIM.printdata[i][j];
                }
            }
            return data;
        }, "the recorded information of the buses, one row per bus and time step. The first column is the time")
        .def("station_passengers", [](Simulation & SIM){
            std::vector<int> waiting;
            for (std::vector<int> & station: SIM.StationPassengers){
                waiting.push_back(station.size());
            }
            return waiting;
        }, "the current number of passengers waiting at each station")
        .def("traffic_light_phases", [](Simulation & SIM){
            std::vector<int> phases;
            for (tlC & tl: SIM.SYSTEM.Tlights){
                phases.push_back(tl.curr_phase);
            }
            return phases;
        }, "the current phase of each traffic light")
        .def("parked_buses", [](Simulation & SIM){
            std::vector<int> parked;
            for (std::vector<int> & depot: SIM.Parked){
                parked.push_back(depot.size());
            }
            return parked;
        }, "the current number of buses parked at each depot")
        .def("queued_buses", [](Simulation & SIM){
            std::vector<int> queued;
            for (std::deque<int> & depot: SIM.Queues){
                queued.push_back(depot.size());
            }
            return queued;
        }, "the current number of services waiting for a bus at each depot");

    m.def("load_config", &loadconfig, py::arg("directory"), "loads the configuration of the Megabus system from the configuration files in a directory");
    m.def("simulate", &simulate, "a complete system simulation");

}
