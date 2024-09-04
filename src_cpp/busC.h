#ifndef BUS_C
#define BUS_C
#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <functional>
#include "parameters.h"
//#include "fleetsize.h"
#include "createsystem.h"
#include "linesC.h"
#include "routeC.h"
#include "passengerC.h"
#include <array>
#include <cmath>
#include <deque>

// creating a bus
void createbus(int TIME, int lineID, std::array<std::vector<int>,Nparam> & BUSESPAR, System & SYSTEM, std::array<std::deque<int>,2> & QUEUES, std::array<std::vector<int>,2> & PARKED){  
    // Determining whether the bus starts from Cuba or Dosquebradas
    int origin = SYSTEM.Lines[lineID].origin;
    int parkID = std::distance(std::begin(Origins),std::find(std::begin(Origins), std::end(Origins), origin));
    if (parkID>=PARKED.size()){
        std::cout<<"Unable to indentify the ParkID, no bus has been introduced"<<std::endl;
        return;
    }
    // we check there are buses available
    if(!PARKED[parkID].empty()){  
        // we append the bus parameters at the end 
        BUSESPAR[0].push_back(SYSTEM.Lines[lineID].origin); //position
        BUSESPAR[1].push_back(SYSTEM.Lines[lineID].or_lane); // lane
        BUSESPAR[2].push_back(0); // speed
        BUSESPAR[3].push_back(0); // gapf
        BUSESPAR[4].push_back(0); // gapfl
        BUSESPAR[5].push_back(0); // gapbl
        BUSESPAR[6].push_back(0); //vbefl
        BUSESPAR[17].push_back(0); // gapfr
        BUSESPAR[18].push_back(0); // gapbr
        BUSESPAR[19].push_back(0); //vbefr
        BUSESPAR[10].push_back(lineID); //lineID
        BUSESPAR[20].push_back(0); //penalty time
        BUSESPAR[11].push_back(0); // stoptime
        BUSESPAR[12].push_back(0); // dwell time
        BUSESPAR[16].push_back(0); // bus occupation
        BUSESPAR[13].push_back(PARKED[parkID].back()); // The bus ID
        BUSESPAR[14].push_back(TIME); //the initial time
        if (SYSTEM.Lines[lineID].biart == 0){
            BUSESPAR[15].push_back(busL[0]); // The size of the bus
        }
        else{
            int r = (int) std::round(100.0*rand()/RAND_MAX);
            if (r > SYSTEM.Lines[lineID].biart){
                BUSESPAR[15].push_back(busL[0]);}
            else{
                BUSESPAR[15].push_back(busL[1]);}
        }



        BUSESPAR[21].push_back(1); // advancing
        BUSESPAR[22].push_back(0); // track where the service is
        BUSESPAR[23].push_back(0); // index of the next traffic light
        

        if (SYSTEM.Lines[lineID].tls.size()>0){ // if there are traffic lights
            BUSESPAR[24].push_back(SYSTEM.Lines[lineID].tldir[0]); // direction index of the next traffic light
            BUSESPAR[25].push_back(SYSTEM.Lines[lineID].tls[0]); // system index of the next traffic light
            BUSESPAR[26].push_back(SYSTEM.Tlights[BUSESPAR[25].back()].positions[BUSESPAR[24].back()]); // position of the next traffic light
        }
        else{
            BUSESPAR[24].push_back(-1);
            BUSESPAR[25].push_back(-1);
            BUSESPAR[26].push_back(1e6);
        }

        // Position of the next break
        if (SYSTEM.Lines[lineID].breaks.size()>0){
            BUSESPAR[27].push_back(SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[0]][0]);
        }
        else{
            BUSESPAR[27].push_back(1e6);
        }
            
        // we retrieve the first stop information
        if (SYSTEM.Lines[lineID].stopx.size()>0){ // in case there are stops
            BUSESPAR[7].push_back(SYSTEM.Lines[lineID].stopx[0]); // the position of the next stop
            BUSESPAR[8].push_back(SYSTEM.Lines[lineID].stationIDs[0]); // the ID of the next station
            BUSESPAR[9].push_back(0); // next station index
            
        }
        else{ // the nonstop buses
            BUSESPAR[7].push_back(1e6); // the position of the next stop
            BUSESPAR[8].push_back(-1); // the position of the next stop
            BUSESPAR[9].push_back(-1); // next station index    
        }
        /*
        for (int i=0; i<Nparam; i++){
            std::cout<<BUSESPAR[i].back()<<" ";
        }
        std::cout<<std::endl;*/
        // We remove the bus from the parked list
        PARKED[parkID].pop_back();
    }
    // If there are no buses, we must throw a warning
    else{
        QUEUES[parkID].push_back(lineID);
    }

} 



// This function must be called after the bus stops in a given station
void updatestop(int index, std::array<std::vector<int>,Nparam> & BUSESPAR, System & SYSTEM){
    int line=BUSESPAR[10][index];
    int i=BUSESPAR[9][index]+1; // updating the index to the next station
    if (i>=SYSTEM.Lines[line].stopx.size()){    // in case the final station is reached
        BUSESPAR[7][index]=1e6; // we set the next stop to out of bounds
        BUSESPAR[8][index]=-1;  // the next station ID
        BUSESPAR[9][index]=-1;   // the next station index
    }
    // Otherwise all parameters are updated
    else{
        BUSESPAR[7][index]=SYSTEM.Lines[line].stopx[i];
        BUSESPAR[8][index]=SYSTEM.Lines[line].stationIDs[i];
        BUSESPAR[9][index]=i;
    }
}


// This script initializes the buses as parked at the portals 
void initializeBusArray(std::array<std::vector<int>,2> & PARKED, int FCUBA, int FDOSQ){
    
    for (int i=0; i<FCUBA; i++){
        PARKED[0].push_back(i);
    }

    for (int i=FCUBA; i<(FCUBA+FDOSQ); i++){
        PARKED[1].push_back(i);
    }    
}


// inserting the buses in the system
void populate(int TIME, std::array<std::vector<int>,Nparam> & BUSESPAR, System & SYSTEM, std::array<std::deque<int>,2> & QUEUES, std::array<std::vector<int>,2> & PARKED){
    // Now we check and see whether it is time to populate
    // we scan over the lines   
    for (int i=0; i<SYSTEM.Lines.size(); i++){
       if (((TIME-SYSTEM.Lines[i].offset)%SYSTEM.Lines[i].headway)==0){
          //  std::cout<<"Ingresando bus a línea "<<i<<" en tiempo "<<TIME<<std::endl;
            createbus(TIME, i, BUSESPAR, SYSTEM, QUEUES, PARKED);
        }
    }
}


/*z*/
// This function calculates all the gaps for all buses
void calculategaps(std::array<std::vector<int>,Nparam> & BUSESPAR, std::vector<std::vector<std::vector<int>>> &EL, System & SYSTEM){
    int lane, lineID, track, tlsystem, tldir,size, position, curr_phase, state, tlindex, breakdis, next_stop_track, track_difference, distance_to_stop, next_tl_track, tl_track_difference, distance_to_tl;
    
    int Nbuses = BUSESPAR[0].size();
    int Nlanes = EL[0].size();
    int Nbreaks = SYSTEM.Breaks.size();
    int breakindex = 0;
    // The list of the last cars pending the forward gaps in a given lane
    std::vector<std::vector<int>> lastcarR (Nlanes);  // pending forward gaps to the left
    std::vector<std::vector<int>> lastcarL (Nlanes);  // pending forward gaps to the right

    std::vector<int> lastcar (Nlanes, -1);  // pending forward gaps

    // The arrays that tell whether the right-forward and left-forward gaps have been updated for a given lane
    std::vector<bool> rightF (Nlanes, false);  // whether the gaps to the right have been updated
    std::vector<bool> leftF (Nlanes, false);   // whether the gaps to the left have been updated

    // The vector identifying the first car after a break position
    std::vector<int> carbreak (Nbreaks, -1);
    // TAREA: LOS CARROS DESPUÉS DEL BREAK DEBEN SER IDENTIFICADOS ANTES DEL FOR:
    // HAY DOS POSIBILIDADES:
    // USAR PROPIEDADES DE VECTORES (MASCARAS) PARA IDENTIFICARLOS
    // HACER UN FOR SOBRE TODOS LOS CARROS PARA IDENTIFICAR LOS BREAKS.

    // we loop over the breaks
    for (int i = 0; i< Nbreaks; i++){
        // we get the break information
        int breakpos = SYSTEM.Breaks[i][2];
        int breaklane = SYSTEM.Breaks[i][3];
        // we create a vector of indices
        std::vector<size_t> index(Nbuses); // an index vector
        // the vector if filled, starting with 0
        std::iota(index.begin(), index.end(), 0);
        std::vector<size_t> target; // index of all buses in the same lane as the break destination
        std::copy_if(index.begin(), index.end(), std::back_inserter(target),[&](size_t i) { return BUSESPAR[1][i] == breaklane; });
        /*
        std::cout<<"target ";
        for (auto &tar: target){
            std::cout<<tar<<" ";
        }
        std::cout<<std::endl;*/
        auto result = std::find_if(target.begin(), target.end(), [&](size_t i) { return BUSESPAR[0][i] >= breakpos;});
        if (result != target.end()){ // se encontró un resultado
            //std::cout<<"find if "<<*result<<"------------------"<<std::endl;
            carbreak[i] = *result;
        }
    }
/*
    for (int j=0; j<Nbreaks; j++){
        std::cout<<"break "<<j<<" "<<carbreak[j]<<" "<<BUSESPAR[0][carbreak[j]]<<" "<<BUSESPAR[1][carbreak[j]]<<std::endl;
    }
  */  

    // we initially set all gaps to their default values
    std::fill(BUSESPAR[3].begin(), BUSESPAR[3].end(),1000); //forward gap
    std::fill(BUSESPAR[4].begin(), BUSESPAR[4].end(),1000); //gapfl
    std::fill(BUSESPAR[5].begin(), BUSESPAR[5].end(),1000); //gapbl
    std::fill(BUSESPAR[6].begin(), BUSESPAR[6].end(),0); //vbefl
    std::fill(BUSESPAR[19].begin(), BUSESPAR[19].end(),0); //vbefr
    std::fill(BUSESPAR[17].begin(), BUSESPAR[17].end(),1000); //gapfr
    std::fill(BUSESPAR[18].begin(), BUSESPAR[18].end(),1000); //gapbr
    
    // now we proceed to scan all buses from east to west
    for (int i=0; i<Nbuses; i++){
        // we get the bus information
        position = BUSESPAR[0][i];
        lane = BUSESPAR[1][i];
        lineID = BUSESPAR[10][i];
        track = BUSESPAR[22][i];
        tlindex = BUSESPAR[23][i];
        tlsystem = BUSESPAR[25][i];
        tldir =  BUSESPAR[24][i];
        size = BUSESPAR[15][i];
        breakdis = BUSESPAR[27][i];

        /////////////////////////////////////////////////
        ///// FORWARD GAP
        // we now calculate the distance to the next stop
        if (BUSESPAR[9][i]>=0){ //Only if there are stops in the future
            next_stop_track = SYSTEM.Lines[lineID].stoptracks[BUSESPAR[9][i]];
            track_difference = next_stop_track - track;
            // We calculate the distance
            distance_to_stop = BUSESPAR[7][i]-position;
            // If there are breaks in between
            for (int j =0; j<track_difference; j++){
                distance_to_stop+= -(SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[track+j]][2]-SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[track+j]][0]);
            }
        }
        else{ //in case there are no stops
            distance_to_stop=1000;
        }
        // by default the forward gap corresponds to the minimal distance between the next lane ending and the distance to the next stop
        BUSESPAR[3][i] = std::min(EL[lineID][lane][position],distance_to_stop);
        //std::cout<<"default gap "<<BUSESPAR[3][i]<<std::endl;
        

        // in case there are breaks in the future
        if (track<SYSTEM.Lines[lineID].breaks.size()){
            int breakID = SYSTEM.Lines[lineID].breaks[track];
            if((carbreak[breakID]>=0) && (carbreak[breakID]!=i)){
                BUSESPAR[3][i] = std::min(BUSESPAR[3][i],breakdis-position+BUSESPAR[0][carbreak[breakID]]-SYSTEM.Breaks[breakID][2]);
            }
        }
        //std::cout<<"Llegó hasta antes de tl"<<std::endl;
        // Now we take into account the possibility of having a traffic lights
        if (BUSESPAR[24][i]>=0){ // only if there is a traffic light ahead
            // we calculate the distance to the next traffic light
            distance_to_tl = BUSESPAR[26][i]-position;

            // in case the traffic light is in a different tracl
            next_tl_track = SYSTEM.Lines[lineID].tltracks[tlindex];
            tl_track_difference = next_tl_track - track;
            // If there are breaks in between
            for (int j =0; j<tl_track_difference; j++){
                distance_to_tl+= -(SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[track+j]][2]-SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[track+j]][0]);
            }
            // we verify whether the traffic light is in red
            curr_phase = SYSTEM.Tlights[tlsystem].curr_phase;
            state = SYSTEM.Tlights[tlsystem].phases[curr_phase][tldir];
            if (state == 0) // if the traffic light is in red
                BUSESPAR[3][i] = std::min(BUSESPAR[3][i], distance_to_tl);
        }
       
        // if there is a last car already, we update its forward gap and speed ahead
        if (lastcar[lane]>=0){
            BUSESPAR[3][lastcar[lane]] = std::min(position-BUSESPAR[0][lastcar[lane]]-size, BUSESPAR[3][lastcar[lane]]);
        }
         // we now update the last car information
        lastcar[lane] = i;
        
        
        if(rightF[lane] == true)  // the forward gap to the right information is up to date
            lastcarR[lane].clear(); 
        lastcarR[lane].push_back(i);

        if(leftF[lane] == true)  // the forward gap to the left information is up to date
            lastcarL[lane].clear(); 
        lastcarL[lane].push_back(i);

        rightF[lane] = false;
        leftF[lane] = false; 

        // Now we evaluate the gaps to the left
        if (lane<Nlanes-1){
            // by default the gapfl is the end of the lane
            BUSESPAR[4][i] = EL[lineID][lane+1][position];

            if (lastcarR[lane+1].size()>0){  // If there is already some cars in the lane to the left
                // we update the gapbl and the vbefl
                BUSESPAR[5][i] =position-BUSESPAR[0][lastcarR[lane+1].back()]-size;
                BUSESPAR[6][i] =BUSESPAR[2][lastcarR[lane+1].back()];
            
                // if the lastcar information has not been updated
                if (rightF[lane+1]==false){
                    for (int index : lastcarR[lane+1]){
                        // we update gapfr
                        BUSESPAR[17][index] = position-BUSESPAR[0][index]-size;
                        rightF[lane+1] = true;
                    }
                }
            }
        }
        // Now we evaluate the gaps to the right
        if (lane>0){
            // by default the gapfr is the end of the lane
            BUSESPAR[17][i] = EL[lineID][lane-1][position];

            if (lastcarL[lane-1].size()>0){  // If there is already a car in the right lane
                // we update the gapbr and the vbefr
                BUSESPAR[18][i] = position-BUSESPAR[0][lastcarL[lane-1].back()]-size;
                BUSESPAR[19][i] = BUSESPAR[2][lastcarL[lane-1].back()];

                // if the lastcar information has not been updated
                if (leftF[lane-1]==false){
                    for (int index : lastcarL[lane-1]){
                        // we update gapfl
                        BUSESPAR[4][index] = position-BUSESPAR[0][index]-size;
                        leftF[lane-1] = true;
                    }
                }
            }
        }
    }
}

 
void sortbuses(std::array<std::vector<int>,Nparam> & BUSESPAR, std::vector<int> &index){

    // buses are only sorted if there are more than one buses
    if (BUSESPAR[0].size()>1){
        //std::cout<<"Sorting "<<BUSESPAR[0].size()<<std::endl;
        std::vector<int> idx(BUSESPAR[0].size());
        std::iota(idx.begin(), idx.end(),0);
        /*for (int i=0; i<idx.size(); i++){
            std::cout<<idx[i]<<" ";
        }*/
        //sorting indexes
        
        std::sort(idx.begin(),idx.end(),
        [&BUSESPAR](int i1, int i2){
            if (BUSESPAR[0][i1]==BUSESPAR[0][i2]){ //if the buses are in the same position, the order is given according to the index i2<i1 
                return i1>i2;
            }
            else{
                return BUSESPAR[0][i1]<BUSESPAR[0][i2]; // if they are not in the same position, the order is given according to the position
            }
        }
        );


        // we now check whether there is a change in order
        if (index!=idx){ // in case there is a change in order
            //std::cout<<"there is a change"<<std::endl;
            // once sorted, we proceed to update all the arrays
            for (int j =0; j<Nparam; j++){
                std::vector<int> aux;
                for (int i =0; i<idx.size(); i++){
                    aux.push_back(BUSESPAR[j][idx[i]]);
                }
                BUSESPAR[j]=aux; 
            }
        }
        // We finally update the index
        index = idx;
    }
}

/* In this version, we check not for the speeds but for the gaps in order to change the lanes, we also check for the safety criterion
For introduce a probability to breach the safety criterion
*/
void buschangelane(std::array<std::vector<int>,Nparam> & BUSESPAR, std::vector<std::vector<std::vector<int>>> &LC,std::vector<std::vector<std::vector<int>>> &RC, std::vector<std::vector<std::vector<int>>> &EL, int TIME){
    int pos, lane, lineID;
    int Ncars = BUSESPAR[0].size();
    // We create a new array with all the new values of the lanes
    std::vector<int> newy = BUSESPAR[1]; // by default, the bus stays in the same lane
    
    // If the time is even, we perform the possible movements to the right
    //if (TIME % 2 == 0){
    for (int i=0; i<Ncars; i++){ // we scan over all buses
        if (BUSESPAR[20][i] >0){BUSESPAR[20][i] = BUSESPAR[20][i]-1;} // in case the car has some penalty time for changing lane
        else{
            pos = BUSESPAR[0][i];
            lane = BUSESPAR[1][i];
            lineID = BUSESPAR[10][i];
            if ((RC[lineID][lane][pos]==1) && (EL[lineID][lane-1][pos] > EL[lineID][lane][pos]) ){ // only if a movement to the right is allowed
            // EL[carril_destino] > EL[carril_origen]


                // we now evaluate willingness    
                // gapb(r/l) > vbef(r/l)
                // gapf(r/l) > v
                
                if ((BUSESPAR[18][i]>BUSESPAR[19][i]) && (BUSESPAR[17][i]>BUSESPAR[2][i])){
                    newy[i] = lane-1;
                }
            }
        
            else if ((LC[lineID][lane][pos]==1) && (EL[lineID][lane+1][pos] > EL[lineID][lane][pos])){ // only if a movement to the right is allowed
                // EL[carril_destino] > EL[carril_origen]
                // we now evaluate willingness
                // gapb(r/l) > vbef(r/l)
                // gapf(r/l) > v
                // we now evaluate willingness
                if ((BUSESPAR[5][i]>BUSESPAR[6][i]) && (BUSESPAR[4][i]>BUSESPAR[2][i])){
                    newy[i] = lane+1;
                }
            }
        }
    }
    // Now we update all the lanes
    BUSESPAR[1]=newy;        
}


// making the buses move
void busadvance(std::array<std::vector<int>,Nparam> & BUSESPAR, System& SYSTEM, int TIME, int & NACTIVEPASS, float &PASSSP, std::array<std::vector<int>, fleet>& BUSPASSENGERS, std::vector<std::vector<int>>& STPASSENGERS, std::vector<std::array<int, Nparpass>> & PASSENGERS, std::array<std::vector<int>,2> & PARKED, std::vector<std::vector<int>> & V, std::vector<std::vector<std::vector<routeC>>> & MATRIX, std::vector<std::vector<std::vector<double>>> &weightMatrix, std::default_random_engine &generator, std::vector<float> &bussp, float & cost){
    int pos, lane, lineID, dt, speed;
    float prand, mean, std;
    // we scan over all buses
    std::vector<int> toremove;
    
    for (int i =0; i<BUSESPAR[0].size(); i++){
        pos = BUSESPAR[0][i];
        lane = BUSESPAR[1][i];
        lineID = BUSESPAR[10][i];
        speed = BUSESPAR[2][i];

        
        // buses advancing
        if (BUSESPAR[21][i]==1){
            // we implement the VDR-TCA model of Maerivoet
            // we determine the randomization parameter depending on the speed
            if (speed==0)
                prand = p0;
            else
                prand = p;
            
            // we calculate the new speed, vnew=acc*min(acc*(v+acc),acc*gap,acc*vmax)
            BUSESPAR[2][i]=std::max(0,std::min((speed+1),std::min(BUSESPAR[3][i],V[lane][pos])));
            
            // we apply the randomization
            float r = ((float) rand() / (RAND_MAX));
            if (r<prand){BUSESPAR[2][i] = std::max(0,BUSESPAR[2][i]-1);}
            // now we update the position, and the relevant distances
            BUSESPAR[0][i]=pos+BUSESPAR[2][i];

            //std::cout<<i<<" "<<TIME<<" "<<BUSESPAR[0][i]<<" "<<BUSESPAR[13][i]<<std::endl;
            
            // checking whether the bus reaches a stop
            if (BUSESPAR[0][i]==BUSESPAR[7][i]){ 
                //std::cout<<"Bus arrived to the station"<<std::endl; 
                // we set the speed, advancing and stoptime to zero
                BUSESPAR[2][i]=0;
                BUSESPAR[21][i]=0;
                BUSESPAR[11][i]=0;
                // we board and alight passengers, and set the dwell time
                busdata results;
                results=busArriving(BUSESPAR[13][i],BUSESPAR[0][i],BUSESPAR[8][i],BUSESPAR[10][i],TIME,NACTIVEPASS,PASSSP,BUSPASSENGERS,STPASSENGERS,PASSENGERS,SYSTEM, MATRIX,  weightMatrix, BUSESPAR[16][i]);
                BUSESPAR[12][i] = results.dwelltime;
                BUSESPAR[16][i] = results.busoccupation;
                //std::cout<<results.dwelltime<<" "<<results.busoccupation<<std::endl;
                // we update the stop information
                updatestop(i,BUSESPAR,SYSTEM);
                //std::cout<<"Bus left the station"<<std::endl;
            }
            //////////////
            // checking whether the bus reaches a traffic light
            if( (BUSESPAR[26][i]<BUSESPAR[0][i]) && (SYSTEM.Lines[lineID].tltracks[BUSESPAR[23][i]]==BUSESPAR[22][i])){
                //std::cout<<"Bus arrived to tl"<<std::endl;
                // We update the new tl information
                BUSESPAR[23][i]++;
                // in case there are more traffic lights ahead
                if (BUSESPAR[23][i]<SYSTEM.Lines[lineID].tls.size()){
                    BUSESPAR[24][i] = SYSTEM.Lines[lineID].tldir[BUSESPAR[23][i]];
                    BUSESPAR[25][i] = SYSTEM.Lines[lineID].tls[BUSESPAR[23][i]];
                    BUSESPAR[26][i] = SYSTEM.Tlights[BUSESPAR[25][i]].positions[BUSESPAR[24][i]];
                }
                else{// if there are no more traffic lights ahead
                    BUSESPAR[24][i]=-1;
                    BUSESPAR[25][i]=-1;
                    BUSESPAR[26][i]=1e6;
                }
                //std::cout<<"Bus left the tl"<<std::endl;
            }

            //////////
            // checking whether the bus reaches a break
            if (BUSESPAR[27][i]<=BUSESPAR[0][i]){
                //std::cout<<"Llegamos al break"<<std::endl;
                // We update the bus position
                BUSESPAR[0][i] = SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[BUSESPAR[22][i]]][2] + (BUSESPAR[0][i]-BUSESPAR[27][i]);
                // We update the bus lane
                BUSESPAR[1][i] = SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[BUSESPAR[22][i]]][3];
                // We update the pos_correction in the passenger's list
                for (int passID: BUSPASSENGERS[BUSESPAR[13][i]]){
                    PASSENGERS[passID][3] = PASSENGERS[passID][3] - (SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[BUSESPAR[22][i]]][2]-SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[BUSESPAR[22][i]]][0]);
                }
                // We update the track of the bus
                BUSESPAR[22][i]++;
                // We update the position of the next break
                if (BUSESPAR[22][i]<SYSTEM.Lines[lineID].breaks.size()){    
                    BUSESPAR[27][i] = SYSTEM.Breaks[SYSTEM.Lines[lineID].breaks[BUSESPAR[22][i]]][0];
                }
                else{
                    BUSESPAR[27][i] =1e6;
                }

                //std::cout<<"Salimos del break"<<std::endl;  
            }   

            ////////////////
            // checking whether there is a service change
            else if (BUSESPAR[0][i]>=SYSTEM.Lines[BUSESPAR[10][i]].change_pos){
                //std::cout<<"Inicio cambio de servicio"<<std::endl;
                //We add the speed of the bus to the list
                int total_distance = SYSTEM.Lines[BUSESPAR[10][i]].end - SYSTEM.Lines[BUSESPAR[10][i]].origin;
                for (int j = 0; j< SYSTEM.Lines[BUSESPAR[10][i]].breaks.size(); j++){
                    total_distance-=SYSTEM.Breaks[SYSTEM.Lines[BUSESPAR[10][i]].breaks[j]][2]-SYSTEM.Breaks[SYSTEM.Lines[BUSESPAR[10][i]].breaks[j]][0];
                }
                bussp.push_back(float((total_distance/(TIME-BUSESPAR[14][i]))));
                // we update the cost value
                cost+=TIME-BUSESPAR[14][i];

                // changing the line
                int newline = SYSTEM.Lines[BUSESPAR[10][i]].dest_line;
                BUSESPAR[10][i] = newline; // we set the new line
                BUSESPAR[14][i] = 0; // the time is restarted
                // we update the next station information
                if (SYSTEM.Lines[newline].stopx.size()>0){ 
                    BUSESPAR[7][i] = SYSTEM.Lines[newline].stopx[0]; // the position of the next stop
                    BUSESPAR[8][i] = SYSTEM.Lines[newline].stationIDs[0]; // the ID of the next station
                    BUSESPAR[9][i] = 0;  // next station index
                }
                else{
                    BUSESPAR[7][i] = 1e6; // the position of the next stop
                    BUSESPAR[8][i] = -1; // the ID of the next station
                    BUSESPAR[9][i] = -1;  // next station index
                }
                // restarting the track
                BUSESPAR[22][i] = 0;
                 // index of the next traffic light
                BUSESPAR[23][i] = 0;
                if (SYSTEM.Lines[newline].tls.size()>0){ // if there are traffic lights
                    BUSESPAR[24][i] = SYSTEM.Lines[lineID].tldir[0]; // direction index of the next traffic light
                    BUSESPAR[25][i] = SYSTEM.Lines[lineID].tls[0]; // system index of the next traffic light
                    BUSESPAR[26][i] = SYSTEM.Tlights[BUSESPAR[25][i]].positions[BUSESPAR[24][i]]; // position of the next traffic light
                }
                else{
                    BUSESPAR[24][i] = -1;
                    BUSESPAR[25][i] = -1;
                    BUSESPAR[26][i] = 1e6;
                }
                // Position of the next break
                if (SYSTEM.Lines[newline].breaks.size()>0){
                    BUSESPAR[27][i]=SYSTEM.Breaks[SYSTEM.Lines[newline].breaks[0]][0];
                }
                else{
                    BUSESPAR[27][i] = 1e6;
                }
                //std::cout<<"Service changed with "<<BUSESPAR[16][i]<<" passenger on board"<<std::endl;
            }

            // checking whether the bus leaves the system
            else if (BUSESPAR[0][i]>=SYSTEM.Lines[BUSESPAR[10][i]].end){
                //We add the speed of the bus to the list
                //std::cout<<"Bus arrived al final"<<std::endl;
                int total_distance = SYSTEM.Lines[BUSESPAR[10][i]].end - SYSTEM.Lines[BUSESPAR[10][i]].origin;
                for (int j = 0; j< SYSTEM.Lines[BUSESPAR[10][i]].breaks.size(); j++){
                    total_distance-=SYSTEM.Breaks[SYSTEM.Lines[BUSESPAR[10][i]].breaks[j]][2]-SYSTEM.Breaks[SYSTEM.Lines[BUSESPAR[10][i]].breaks[j]][0];
                }
                bussp.push_back(float((total_distance/(TIME-BUSESPAR[14][i]))));
                // we update the cost value
                cost+=TIME-BUSESPAR[14][i];

                // in case there are still passengers on board a warning must be displayed
                if (BUSESPAR[16][i]>0){
                    std::cout<<"WARNING!! A bus with passengers is about to be taken out of the system"<<std::endl;
                }
                //  the bus is removed and added to the parked list
                toremove.push_back(i);
                int end = SYSTEM.Lines[lineID].end;
                int parkID = std::distance(std::begin(Ends),std::find(std::begin(Ends), std::end(Ends), end));
                PARKED[parkID].push_back(BUSESPAR[13][i]);

                // we check if there are buses in the queues
                if (!QUEUES[parkID].empty()){
                    // we create inmediately the bus to fulfill the demand
                    createbus(TIME,QUEUES[parkID][0], BUSESPAR, SYSTEM, QUEUES, PARKED);
                    /*if (BUSESPAR[17][i]==1){
                        std::cout<<"Bus 75 transformed"<<std::endl;
                    }*/
                    // we remove the first element of the queue
                    QUEUES[parkID].pop_front();
                }
            }
            
        }
        // if the bus is not advancing
        else{
            //the stop time is increased by one
            BUSESPAR[11][i]=BUSESPAR[11][i]+1;
            // we check that the stopping time is equal or larger than the dwell time
            if (BUSESPAR[11][i]>=BUSESPAR[12][i]){
                // twe update the changing and the advancing
                BUSESPAR[21][i]=1;
                BUSESPAR[20][i]=pentime;
            }
        }   

        
    }
    
    // we now remove the buses that left the system
    while(!toremove.empty()){
        int i=toremove.back();
        for (int j=0; j<Nparam; j++){
            BUSESPAR[j].erase(BUSESPAR[j].begin()+i);
        }
        toremove.pop_back();
    }
}

// Calculating the passenger flow and the station occupation
void getPassengerFlowSpeedOccFast(std::array<std::vector<int>,Nparam> & BUSESPAR, float &flow, float &occ, int Nactivepass, int &ncounts){
    float newflow=0;
    float newocc=0;
    for (int i=0; i<BUSESPAR[0].size(); i++){ // we scan over buses
        newflow+=BUSESPAR[2][i]*BUSESPAR[16][i];
        newocc+=BUSESPAR[16][i];
    }
    occ+=Nactivepass-newocc; // Active passengers minus passengers in buses
    flow+=newflow;
    ncounts++;
}

#endif