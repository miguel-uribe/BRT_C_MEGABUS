"""
import sys
sys.path.append('../src_cpp')
import simulator
import numpy as np


test = simulator.simulate(1,0,0.5)
print('test' , test.BSP, test.cost, test.passp, test.occ, test.flow, np.array(test.BusData).shape)
"""

import sys
sys.path.append('../src_cpp')
import simulator
import pandas as pd
import numpy as np
import os
import subprocess
import random
import time
#from multiprocessing import pool
from multiprocessing import cpu_count, Manager, Process, Pool

#if __name__ == '__main__':

def write_headways (x):

    dirname = os.path.dirname(__file__)
    x1 = []
    for i in x:
        if i == 0:
            x1.append(1000000)
        else:
            x1.append(int(np.round(1/(i/3600)))) #frequencies to headways (bus/h) --> s

    texto = f'0 {x1[0]} 0\n'+f'1 {x1[1]} 0\n'+f'2 {x1[2]} 0\n'+f'3 {x1[3]} 0\n'+f'4 {x1[4]} 0\n'+f'5 {x1[5]} 0\n'+f'6 {x1[6]} 0\n'+f'7 {x1[7]} 0\n'
    #print(x1)
    filename = os.path.join(dirname,'../conf/') + 'service_data.txt'
    f = open(filename,'w')
    f.write(texto)
    f.close()


#### Scenario 1

##Frecuencias actuales 
f1, f2, f3 = 270, 270, 360 #s
r21, r31 = f1/f2, f1/f3 # Relación frecuencias de rutas

def one_simulation(seed):
    result = simulator.simulate(seed,0,0.5)
    print([result.BSP, result.cost, result.passp, result.occ, result.flow])
    return [result.BSP, result.cost, result.passp, result.occ, result.flow]


def scenario_1():
    results_Sc1, std_Sc1 = [], []
    N_process = 40
    seeds = np.arange(1,N_process+1)
    
    for j in range(1,61,1):
        a = [j, j*r21, j*r31, 0, j, j*r21, 0, 0]
        write_headways(a)
        print(a)
        pool = Pool(processes=N_process)
        results = pool.map(one_simulation, seeds)
        pool.close()
        pool.join()
        print(np.array(results))
        results_Sc1.append(np.array(results).mean(axis = 0))
        std_Sc1.append(np.array(results).std(axis = 0))


    return results_Sc1, std_Sc1

def scenario_2():
    results_Sc2, std_Sc2 = [], []
    N_process = 40
    seeds = np.arange(1,N_process+1)
    for j in range(1,61,100):
        a = [j, j, j, j, j, j, 0, j]
        write_headways(a)
        pool = Pool(processes=N_process)
        results = pool.map(one_simulation, seeds)
        pool.close()
        pool.join()
        #print(np.array(results))
        results_Sc2.append(np.array(results).mean(axis = 0))
        std_Sc2.append(np.array(results).std(axis = 0))

    return results_Sc2, std_Sc2



def run_scenarios():
    results_Sc1, std_Sc1 = scenario_1()
    r1 = pd.DataFrame(results_Sc1, columns = ['Average Bus Speed', 'Average cost', 'Average Passenger Speed', 'Average Occupation', 'Average bus flow'])
    r2 = pd.DataFrame(std_Sc1, columns = ['Std Bus Speed', 'Std cost', 'Std Passenger Speed', 'Std Occupation', 'Std bus flow'])
    r1 = r1.join(r2)
    r1.to_csv('../preliminary results/scenario1.csv', index = False)
    
    results_Sc2, std_Sc2 = scenario_2()
    r3 = pd.DataFrame(results_Sc2, columns = ['Average Bus Speed', 'Average cost', 'Average Passenger Speed', 'Average Occupation', 'Average bus flow'])
    r4 = pd.DataFrame(std_Sc2, columns = ['Std Bus Speed', 'Std cost', 'Std Passenger Speed', 'Std Occupation', 'Std bus flow'])
    r3 = r3.join(r4)
    r3.to_csv('../preliminary results/scenario2.csv', index = False)


#run_scenarios()
one_simulation(1)
#print(results[0].BSP)
#for i in np.arange(1,31):
#    print(i)
#    one_simulation(i)
#scenario_1()

#test = simulator.simulate(1,0,0.5)
#print('test' , test.BSP, test.cost, test.passp, test.occ, test.flow, np.array(test.BusData).shape)