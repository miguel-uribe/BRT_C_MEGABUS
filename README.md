# BRT_C_MEGABUS

## What the code does
This code creates a full simulation of the Megabus BRT system in Pereira - Dosquebradas, Colombia. The simulation code is entirely written in c++. To use it, a Python module must be created using the `pybind11` library. Once this library is imported into the Python code, the c++ code can be run as a normal function in Python.

## Installing the prerequisites
The code runs on Linux and on Windows. Three tools are required:

- [uv](https://docs.astral.sh/uv/), which installs Python 3.12 and all the Python libraries of the project.
- A c++ compiler. On Ubuntu: `sudo apt install build-essential`. On Windows: either Visual Studio Build Tools (C++ workload) or a MinGW-w64 GCC distribution such as [WinLibs](https://winlibs.com/) with its `bin` folder in the `PATH`.
- CMake (3.18 or newer) and, optionally, Ninja. Both are included in WinLibs; on Ubuntu: `sudo apt install cmake ninja-build`.

Once uv is installed, the Python environment is created from the repository root with:
```
uv sync
```
The optional analysis libraries (`jupyter`, `matplotlib`, `seaborn`) are installed with `uv sync --group analysis`.

## Compiling the c++ source
The c++ code is compiled into a Python module with CMake. From the repository root:
```
uv run cmake -S . -B build -G Ninja
uv run cmake --build build
```
`-G Ninja` can be omitted on Linux. The commands must be run through `uv run` so that CMake finds the Python of the project environment.

## Testing
The regression tests check that the configuration files generated from the layout, and the results of the simulation for a list of fixed seeds, are exactly the ones recorded in `tests/golden/`. They are run from the repository root with:
```
uv run pytest
```
The tests need the configuration files in `conf/`, they are generated automatically if they are missing or older than the layout files (this takes about half a minute).

The engine draws all its random numbers from its own generator (`src_cpp/rng.h`), so a given seed is meant to give the same results with any compiler and operating system. When a change in the results is intended, the goldens are recorded again with:
```
uv run python tests/record_goldens.py
```

## The compiled module
The compilation creates the `simulator` module in the `src_cpp` folder (`simulator.*.so` on Linux, `simulator.*.pyd` on Windows). The library contains the definition of a function called `simulate()` that receives three inputs:
- (int) seed: the random generator seed
- (int) print: this should be either 0 or 1. 1 if the detailed simulation data must be created, 0 otherwise (faster).
- (float) Cfract: the fraction of the total fleet initially in the Cuba parking lot.

## Using the compiled module from Python code
We suggest all python code should be located in the `src_python` folder. In order to import the library, the following lines of code should be used:
```
import sys
sys.path.append('../src_cpp')
import simulator
```
If the Python code is located in a different folder, the second line must be updated accordingly.

## Using the module
Once imported, the module implements a function called `simulate (seed, print, Cfract)`. This function launches an entire simulation of the system using the given input parameters. All system information is located in the configuration files located in the `conf` folder. Most of these configuration files are created automatically after running the `layout_interpreter.py` and `route_generator.py` files. Most on these configurations later. The `simulate` function will return an instance of the `sim_results` structure, this instance has the following attributes:
- `BSP`. The average bus speed during the window, in cell/unit_time.
- `passsp`. The average passenger speed during the simulation, the speed is computed using also the waiting times at the stations, in cell/unit_time.
- `cost`. The total bus time during the simulation, in bus-h.
- `flow`. The system-wide average passenger flow, in passengers/second.
- `BusData`. The detailed simulation data, time-step by time-step, bus by bus. It is presented as a 2D list format, where each list is a 29-element list containing the time and the 28 bus parameters. It is suggested to parse this list as a numpy array for later work using `bus_data_array = np.array(data.BusData)`.

These atributes can be accessed in the usual Python and C++ ways:
```
import sys
sys.path.append('../src_cpp')
import simulator

data = simulator.simulate(1,0,0.5)
print(data.BSP)  # The obtained average bus speed should be printed
```

## Changing the configuration from Python
The `simulate` function always reads the files in `conf/`. The module also allows to load the configuration once, modify it in memory, and run as many simulations as needed without writing any file:
```
config = simulator.load_config('../conf')

config.lines[0].headway = 240           # the headway of the first service, in seconds
config.depots[0].initial_buses = 30     # the buses initially parked at each depot
config.depots[1].initial_buses = 20
config.demand_rates = [1.2*rate for rate in config.demand_rates]   # passengers per hour, at the times in config.demand_times
config.params.BusCap = 160              # the model parameters, formerly in parameters.h

sim = simulator.Simulation(config, seed=1)
sim.run()
results = sim.results()
```
The configuration also gives access to `stations`, `traffic_lights`, `breaks`, the lane arrays (`EL`, `LC`, `RC`, `V`), the passenger matrices (`IN`, `OD`, `route_weights`) and the simulation window (`initial_time`, `final_time`). A copy of a configuration is created with `simulator.SimConfig(config)`. The simulations do not share any state, so they can run in parallel threads.

In addition to the attributes listed above, the results include the number of `passengers` and `delivered` passengers, their average `travel_time`, and per-station (`station_entries`, `station_boardings`, `station_alightings`, `station_waiting`) and per-service (`line_departures`, `line_queued`, `line_arrivals`, `line_trip_time`, `line_boardings`) information.

A simulation can also be advanced step by step, to look at the state of the system while it runs:
```
sim = simulator.Simulation(config, seed=1)
while not sim.done:
    sim.step(60)                        # advances 60 seconds
    buses = sim.buses()                 # one row per bus, the columns are listed in simulator.BUS_COLUMNS
    waiting = sim.station_passengers()  # the passengers waiting at each station
```
The detailed bus information of every time step is stored when the simulation is created with `record=True`, and retrieved with `sim.bus_data()`.

# The scenario file
A scenario is a single JSON file with the complete description of a system and its simulation: the lanes each service may use, the speed limits, the jumps, the stations with their docking bays, the traffic lights, the services, the depots, the passenger demand and the model parameters. It is meant to replace the spreadsheets in `layout/`, the files in `conf/` and the parameter files described in the rest of this document. The scenario of the Megabus system is `scenarios/megabus.json`.

All the positions in a scenario are given as a cell (one meter) and a lane, along the coordinate in which the buses always advance. The definitions are in `brtsim/model.py`.

## Running simulations
The `brtsim` Python package reads a scenario, checks it, compiles it in memory into the configuration of the engine, and runs it with as many seeds as needed in parallel. Nothing is written to disk:
```
import brtsim

scenario = brtsim.load('scenarios/megabus.json')
results = brtsim.run(scenario, seeds=20)      # raises brtsim.ScenarioError listing every problem of the scenario

print(results.summary())                      # mean, standard deviation and confidence interval of each indicator
results.mean['bus_speed']                     # km/h
results.stations                              # entries, boardings, alightings and waiting passengers of each station
results.services                              # departures, arrivals, trip time and boardings of each service
```
The indicators and their units are listed in `brtsim/results.py`.

To evaluate many alternatives, as an optimization algorithm does, the scenario is prepared once and some of its parameters are replaced in each run, without compiling it again:
```
model = brtsim.prepare(scenario)

results = model.run(seeds=20, frequencies={'1E': 15, '2E': 10}, fleet={'Cuba': 30, 'Dosquebradas': 20}, demand_scale=1.2)

# several cases at once, all their simulations share the processors
cases = [{'frequencies': {'1E': frequency}} for frequency in range(5, 40, 5)]
for case, results in zip(cases, model.run_many(cases, seeds=20)):
    print(case, results.mean['bus_speed'], results.std['bus_speed'])
```
The parameters that can be replaced are the `headways` (seconds) or `frequencies` (buses per hour) and `offsets` of the services, the `fleet` of each depot, the demand (`demand_scale`, `demand`, `entries`), the model parameters (`params`) and the simulation window (`initial_time`, `final_time`); they are described in `Model.config` in `brtsim/api.py`. Any other change, such as the stops of a service, is made in the scenario, which compiles in a fraction of a second. `model.simulation(seed)` gives a simulation that advances step by step, as described above.

## The user interface
The scenario can be edited and simulated in a window, without touching any file by hand:
```
uv run python -m brtsim gui scenarios/megabus.json
```
The window has a page for each part of the scenario: the frequencies of the services, the fleet of each depot, the phases of the traffic lights, the demand (the passengers over time, the stations where they enter and their destinations) and the parameters of the model. Every change can be undone, the problems of the scenario are listed at the bottom of the window as it is edited, and the Run page simulates it with several seeds in the background and shows the averaged results, which can be exported. The network itself (lanes, stations, positions of the traffic lights and paths of the services) is shown but cannot be edited in the window yet.

## The command line
The same is available from the command line:
```
uv run python -m brtsim run scenarios/megabus.json --seeds 20 --frequency 1E=15 --buses Cuba=30 --services --output results.json
uv run python -m brtsim validate scenarios/megabus.json
uv run python -m brtsim --help
```

## Jumps
The parts of a system that are not consecutive along the coordinate of the buses are connected with jumps: the buses reaching a cell continue from another cell and lane. To avoid collisions, a jump must follow two rules:

1. No bus can reach the landing cell along the landing lane: the lane must start at the landing cell, so that a jumping bus never finds buses arriving from behind.
2. No bus can change into the lane of the jump during the 50 cells before the jump, nor into the landing lane during the 50 cells after the landing. A service can change between two lanes wherever it may circulate on both.

Jumps are created with `brtsim.add_jump(scenario, x, lane, to_x, to_lane)`, which raises `brtsim.ScenarioError` and leaves the scenario untouched if the jump breaks a rule. `brtsim.unsafe_jumps(scenario)` lists the jumps of a scenario that break them, it must be checked again after the lanes are modified.

## The Megabus scenario
`scenarios/megabus.json` was created from the original files by the importer, and the tests check that it compiles to exactly the configuration the scripts `layout_interpreter.py` and `routegenerator.py` write. After changing the spreadsheets or the files `IN.txt`, `OD_matrix.txt` or `service_data.txt`, the scenario is created again with:
```
uv run python -m brtsim import-megabus
```

# User Generated Files
The entire simulation workflow relies on a series of user generated files with the basic information of the street layout, traffic lights, and service frequencies. These files must be generated manually.


## The Layout File
The layout file is and Excel file called `layout_file.xlsx` that must be located in the `layout/` folder. This file contains all the information of the places where services can transit, the location of stops, location of traffic lights, possible breaks, speed limits, etc.

Each column in the layout file corresponds to a bus lane, each row in the layout file corresponds to one cell. Each cell can contain either of the following keys and their corresponding complementary information. Different keys declarations must be separated by a semicolon:

- `R`: The list of bus services that may transit through the cell. For example, if a cell can be transited by services `R1`, `R2` and `R5`, the cell must contain the key: `R: R1, R2, R5`. The names of the services and the paths buses might take are taken from these declarations.
- `E`: If a cell corresponds to a bus stop, it must include this key. This key must always be AFTER the `R` key. The complementary information includes the station name and, optionally, which of the services listed in key `R` are making the stop in this cell. If the services are not specified, it is understood that all services in `R` make a stop at this position. For example, if a cell can be transited by services `R1`, `R2` and `R5`; but the cell corresponds to a bus stop in station `El Viajero` where only the service `R1` stops, the following information must be provided in the cell text: `R: R1, R2, R5; E: El Viajero, R1`. If, on the other hand, the cell corresponds to station `Cañarte` and all services must stop there, the information is: `R: R1, R2, R5; E: El Viajero`.
- `S`: If a cell corresponds to the position of a traffic light, it must include this key. The complementary information must contain two items: the name of the traffic light, and the name of the direction. Both names must have a correspondence in the `trafic_lights_file.xlsx` which will be discussed later. For example, if the traffic light `S6` is located in a cell, and the traffic light blocks the traffic in the east direction `E`, the information in the corresponding cell should be:  `R: R1, R2, R5; S: S5, E`.
- `B`: The layout files allows for jumps between lanes. This is useful to incorporate services with different lengths and other particular geometric features a BRT system might have. The jumps can be introduced with the `B` key. Which must also include as complementary information the destination cell and the destination lane. For example, if from a given cell we need to jump to the cell located in 13350 and the lane 2, the following information must be provided: `R: R2; B: 13350, 2`. During the simulation, buses passing over this cell will be automatically transferred to cell 13350 and lane 2. The jumps have boundary conditions, the gaps are therefore preserved and collisions are always avoided.
- `SS`: This is the position where services start their movement. In the simulation this is the cell where buses assigned to this service will be first introduced. For example if services `R1` and `R2` start at a particular cell, the following information must be provided: `R: R1, R2; SS: R1, R2`. At the moment, the `SS` declaration does not incorporate the `R` declaration, and both are needed.
- `SF`: This is the position where services finish their movement. After reaching this position, buses will be removed from the simulation and will be made available to start a new journey. The declaration `R: R1, R2; SF: R1, R2` must be introduced in the finishing cell of services `R1` and `R2`.
- `C`: Some services might mutate at some point in the simulation, this means they change their name, while retaining their passengers. These changes are introduced by the `C` key. If at a particular cell the service `R1` becomes the service `B1`, then the cell must contain the following information: `R: R1, B1 ; C: R1, B1`. Notice how the `C` key is followed by the original service and the destination service.
- `V`: in general, the system-wide max speed, in cells/unit-time, is given in the file `layout/parameters.py` as `vmax`. However, custom max speeds for each cell can be added using the `V` key. This key is followed by the new max speed, in km/h. If, for example, at a given cell the max speed is 30 km/h, then the cell must contain a declaration like `R: R1, R1; V: 30`.

All the declarations might be present at the same time, however the `R` declaration must be added ALWAYS FIRST.

## The Traffic Lights File
All information regarding the traffic lights is located in the file `layout/traffic_lights_file.xlsx`. This is an Excel file where each row corresponds to a traffic light in the system, in no particular order. For each traffic lights, there are several columns where all the relevant information is included in the following way:

- `direction`: A list of the traffic light directions. For example, if a traffic light stops traffic in the east-west, a possible directions declaration would be `E - W`, the name of the direction is not relevant, but must correspond to the one used in the `layout_file.xlsx`. It also determines the order in which all subsequent information will be provided.

- `length`: not used.

- `offset`: These parameters implements the offset between different traffic lights. It is assumed that the initial phase has advanced by a quantity `offset` at the beginning of the simulation.

- `phase_n`: The configuration of the different phases. In the simulation, the traffic light always starts at `phase_0`. Each configuration has the following format: `time: allowdir_0 - allowdir_1 - ...`. The `allowdir_n` is either 0 or 1, 0 corresponding to red and 1 corresponding to green. The number of `allowdir` commands must be the same as the declared directions.

## Processing the layout and traffic lights files
These files are read by an algorithm that parses the input files and creates all the relevant configuration files. The creation of these files only requires the execution of the `layout_interpreter.py` with Python. In the console we go to the folder `layout/` and execute: 
```
python layout_interpreter.py
```
The execution of this script will create the following files in the `conf/` folder:
- `V.txt`: the speed file.
- `lanes_{service}.txt`: the available lanes for each service.
- `LC_{service}.txt`: the left changes file for each service.
- `RC_{service}.txt`: the right changes file for each service.
- `EL_{service}.txt`: the end of lane file for each service.
- `station_list.txt`: the list of the stations.
- `station_definition.txt`: the detailed information of each station.
- `service_list.txt`: the list of bus services.
- `service_definition.txt`: the detailed information of each service.
- `breaks_list.txt`: the list of jumps in the system.
- `service_breaks.txt`: the list of jumps for each system.


# Passenger related files

## The IN file
The IN file is located in `conf/IN.txt` and contains the normalized entrance probability to each of the stations in the system. It is a column vector with only the probabilities, the order of the stations MUST BE the same as in the `conf/station_list.txt`.

## The OD matrix file
The OD file is located in `cong/OD.txt` and contains the normalized probability for a passenger that entered the system at station A to have station B as their final destination. Each row of the file has the following format:
```
station_origin_ID station_destination_ID probability
```
The station ID's are defined in the `station_list.txt` file. The probabilities are normalized such that for a given origin station, the sum of the probabilities of all the destination stations is one.

## Generating all possible routes
Once the configuration files are generated, all possible connections between stations can be computed using the `routegenerator.py` script. To run this script simply go to the `layout/` folder and execute the following code:ç
```
python routegenerator.py
```
This script will generate the following service related files:
- `RouteMatrix.txt`: a file containing all possible connections between stations.

# The service data file
The file `conf/service_data.txt` is the last of the user generated files. This file contains the information about the headways of all services, it also introduces the information regarding whether the service is served by articualed or biarticulated buses. However, the latter feature is not really implemented at the moment. The format of each line in the `service_data.txt` file is the following:
```
service_id headway 0
```
where headway is the service headway in seconds. The service ID is defined in the `service_list.txt` file.


