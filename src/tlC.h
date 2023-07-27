#ifndef TL_C
#define TL_C

#include <cstdlib>
#include <vector>
#include <random>

class tlC{
    public:
        std::string name;  // The name of the traffic light
        std::vector<std::string> directions; // A list of traffic directions
        std::vector<int> positions; // A list of traffic directions
        std::vector<int> lengths; // A list of traffic directions
        std::vector<std::vector<int>> phases; // A list of phases, each phase is a list
        std::vector<int> durations; // A list of durations
        int curr_phase; // The current phase
        int phasetime; // The time elapsed since the last change
       
        // Dummy constructor
        tlC(){}
        // real constructor
        tlC(std::string NAME, int offset){
            name = NAME;
            curr_phase = 0;
            phasetime = offset;
        }

        std::string display (void);
        void updatephase(int TIME);
};

std::string tlC::display (void){
    std::string text = "Traffic Lights " + name;
    text = text + ". Current Phase: " + std::to_string(curr_phase);
    text = text + ". Time since last change: " + std::to_string(phasetime) + "\n";
    text = text + ". Directions: ";
    for(int i = 0; i < directions.size(); i++){
        text = text + directions[i] + " "+ std::to_string(positions[i]) + " " + std::to_string(lengths[i]) + " -";
    }
    text = text + "\n Phases: ";

    for(int i = 0; i < phases.size(); i++){
        text = text + std::to_string(durations[i]);
        for(int j = 0; j < phases[i].size(); j++){
            text = text + " " + std::to_string(phases[i][j]);
        }
        text = text + " ";
    }
    text = text + "\n";
    return text;
}


void tlC::updatephase(int TIME){
    phasetime++; // the time is increased
    if (phasetime >= durations[curr_phase]){ // if the time is equal or larger than the expected phase time, the phase is increased
        phasetime = 0;
        curr_phase++;
        if (curr_phase >= durations.size()){ // If the phase is larger than the number of phases, we set it to zero
            curr_phase = 0;
        }
    }
}

#endif