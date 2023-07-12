# BRT_C_MEGABUS

Future modifications:

- Each line must contain the information of the breaks. This information must be used to determine the distance to the next stop and to apply the boundary conditions at each step.
- To avoid unwanted lane changes, only changes to a lane where the end of lane is larger will be allowed.
- The services that change also have a service end, by default. Therefore, at service ends it should be checked whether a service change takes place
- At intersections, a rule should be created to avoid buses to interfere in the intersections.