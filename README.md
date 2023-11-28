# BRT_C_MEGABUS

## What the code does
This code creates a full simulation of the Megabus BRT system in Pereira - Dosquebradas, Colombia. The simulation code is entirely written in c++. To use it, a Python module must be created using the `pybind11` library. Once this library is imported into the Python code, the c++ code can be run as a normal function in Python. The code is meant to run in a Linux machine.

## Installing the prerequisites

### c++ compiler
The first thing you need is a c++ compiler, which can be easily install in Ubuntu using the following lines from a terminal:
`sudo apt update`
`sudo apt install build-essential`

### python
It is recommended that you create a separated Python environment for your project. Unfortunately the Python version in the official Ubuntu repositories does not update fast enough, it is therefore suggested that we include the `deadsnakes` repository to the package manager and then install an up-to-date Python version.

First, we update the repositories and packages
`sudo apt update && sudo apt upgrade`

Next, we add the repository
`sudo add-apt-repository ppa:deadsnakes/ppa`

Now we can install a custom Python version, say Python 3.11
`sudo apt install python3.11`

We can verify that Python 3.11 is installed by executing
`python3.11 --version`

In addition to Python we will need the `venv` and the `python-config` modules which can be installed using:
`sudo apt install python3.11-venv python3.11-dev`

Use the same Python version you installed two steps above. Once these steps are completed we are ready to create a Python environment for the simulation project, this can be achieved as follows:

`python3.11 -m venv /path/to/environment/folders/simulator`

This command will create an environment called `simulator` located in an existing `/path/to/environment/folders` which should have been created beforehand. After this step, the environment can be activated with
`source /path/to/environment/folders/simulater/bin/activate`

Finally, we need to install the required libraries, `numpy` and `pybind11` are mandatories. `pandas`, `jupyter` or visualization libraries such as `matplotlib` and `seaborn` are optional and depend on the work that needs to be performed after the simulations.

`pip install numpy pybind11 pandas jupyter matplotlib seaborn`

## Compiling the c++ source
In order to compile the c++ code to create a Python module, the following line should be run from the `src_c++` folder.
`g++ -O2 -Wall -shared -fPIC $(python -m pybind11 --includes) main.cpp -o simulator.so`

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




Instructions to use the algorithm

- Create the layout file with all the information regarding services, stops, traffic lights and breaks.
- Go to the 'layout' directory
- Execute 'python layout_interpreter.py'
- Execute 'python routegenerator.py'
- Create the file 'IN.txt' with the entrance probability for each station
- Create the file 'OD_matrix.txt' with the travel probability for each pair of stations
- Go to the 'src' directory
- Compile the cpp source code 'g++ -O2 test.txt -o simulation.exe'
- Run the code with './simulation.exe {seed} {print} {fraction}' where {seed} is an integer, {print} is 1 to print the detailed bus information in each time step or 0 otherwise, {fraction} is the fraction of the fleet starting in Cuba.

