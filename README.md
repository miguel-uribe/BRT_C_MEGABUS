# BRT_C_MEGABUS

## What the code does
This code creates a full simulation of the Megabus BRT system in Pereira - Dosquebradas, Colombia. The simulation code is entirely written in c++. To use it, a Python module must be created using the `pybind11` library. Once this library is imported into the Python code, the c++ code can be run as a normal function in Python. The code is meant to run in a Linux machine.

## Installing the prerequisites

### c++ compiler
The first thing you need is a c++ compiler, which can be easily install in Ubuntu using the following lines from a terminal:
```
sudo apt update
sudo apt install build-essential
```

### python
It is recommended that you create a separated Python environment for your project. Unfortunately the Python version in the official Ubuntu repositories does not update fast enough, it is therefore suggested that we include the `deadsnakes` repository to the package manager and then install an up-to-date Python version.

First, we update the repositories and packages
```
sudo apt update && sudo apt upgrade
```

Next, we add the repository
```
sudo add-apt-repository ppa:deadsnakes/ppa
```

Now we can install a custom Python version, say Python 3.11
```
sudo apt install python3.11
```
We can verify that Python 3.11 is installed by executing
```
python3.11 --version
```

In addition to Python we will need the `venv` and the `python-config` modules which can be installed using:
```
sudo apt install python3.11-venv python3.11-dev
```

Use the same Python version you installed two steps above. Once these steps are completed we are ready to create a Python environment for the simulation project, this can be achieved as follows:

```
python3.11 -m venv /path/to/environment/folders/simulator
```

This command will create an environment called `simulator` located in an existing `/path/to/environment/folders` which should have been created beforehand. After this step, the environment can be activated with
```
source /path/to/environment/folders/simulater/bin/activate
```

Finally, we need to install the required libraries, `numpy` and `pybind11` are mandatories. `pandas`, `jupyter` or visualization libraries such as `matplotlib` and `seaborn` are optional and depend on the work that needs to be performed after the simulations.

```
pip install numpy pybind11 pandas jupyter matplotlib seaborn
```

## Compiling the c++ source
In order to compile the c++ code to create a Python module, the following line should be run from the `src_c++` folder.
```
g++ -O2 -Wall -shared -fPIC $(python -m pybind11 --includes) main.cpp -o simulator.so
```

This line should create the file `simulator.so` in the folder. The library contains the definition of a function called `simulate()` that receives three inputs:
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


