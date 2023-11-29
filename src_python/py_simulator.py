import sys
sys.path.append('../src_cpp')
import simulator
import numpy as np


test = simulator.simulate(1,0,0.5)
print('test' , test.BSP, test.cost, test.passp, test.occ, test.flow, np.array(test.BusData).shape)