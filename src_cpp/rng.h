#ifndef RNG_H
#define RNG_H

#include <cstdlib>
#include <random>
#include <vector>

// All the random numbers of a simulation are drawn from this class
class rngC{
    public:
        std::default_random_engine generator;

        rngC(int seed): generator(seed){
            srand(seed);
        }
        // a uniform number in [0,1]
        double uniform(void){
            return (double) rand() / (RAND_MAX);
        }
        // a uniform number in [0,1], in single precision
        float uniformf(void){
            return (float) rand() / (RAND_MAX);
        }
        // a uniform integer in [0,n)
        int below(int n){
            return rand()%n;
        }
        // a Poisson distributed integer
        int poisson(double mean){
            std::poisson_distribution<int> distribution (mean);
            return distribution(generator);
        }
};

// A discrete distribution over the indices of a list of weights
class discreteC{
    public:
        std::discrete_distribution<int> distribution;

        discreteC(){}
        discreteC(const std::vector<double> & weights): distribution(weights.begin(), weights.end()){}

        int sample(rngC & RNG){
            return distribution(RNG.generator);
        }
};

#endif
