# BRT_C_MEGABUS

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

