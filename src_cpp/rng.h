#ifndef RNG_H
#define RNG_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <random>
#include <vector>

// All the random numbers of a simulation are drawn from this class.
// The distributions of the standard library are not used because their results depend on the compiler,
// the Mersenne Twister generator is fully specified by the standard. The same seed gives the same simulation everywhere.
class rngC{
    public:
        std::mt19937_64 generator;

        rngC(int seed): generator(seed){}

        // a uniform number in [0,1)
        double uniform(void){
            return (generator() >> 11) * (1.0/9007199254740992.0);
        }
        // a uniform integer in [0,n)
        int below(int n){
            const std::uint64_t range = n;
            // the values above the limit are rejected, so that all results are equally likely
            const std::uint64_t limit = UINT64_MAX - UINT64_MAX % range;
            std::uint64_t value = generator();
            while (value >= limit){
                value = generator();
            }
            return value % range;
        }
        // a Poisson distributed integer, using the multiplication method of Knuth
        int poisson(double mean){
            int count = 0;
            // a large mean is split in parts, the sum of Poisson variables is a Poisson variable
            while (mean > 0){
                double part = std::min(mean, 256.0);
                double limit = std::exp(-part);
                double product = uniform();
                while (product > limit){
                    count++;
                    product = product*uniform();
                }
                mean = mean - part;
            }
            return count;
        }
};

// A discrete distribution over the indices of a list of weights
class discreteC{
    public:
        std::vector<double> cumulative; // the cumulative sum of the weights
        int last = 0; // the last index with a positive weight

        discreteC(){}
        discreteC(const std::vector<double> & weights){
            double total = 0;
            for (int i = 0; i<weights.size(); i++){
                if (weights[i] > 0){
                    total = total + weights[i];
                    last = i;
                }
                cumulative.push_back(total);
            }
        }

        int sample(rngC & RNG){
            if (cumulative.empty() || cumulative.back() <= 0){
                return 0;
            }
            double value = RNG.uniform()*cumulative.back();
            // the first index whose cumulative weight is larger than the value, an index with no weight is never chosen
            int index = std::upper_bound(cumulative.begin(), cumulative.end(), value) - cumulative.begin();
            return std::min(index, last);
        }
};

#endif
