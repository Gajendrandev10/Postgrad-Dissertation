package src;

simple UAVNode
{
    gates:
        input in[];
        output out;
}

network UAVNetwork
{
    submodules:
        groundStation: UAVNode;
        uav1: UAVNode;
        uav2: UAVNode;
        uav3: UAVNode;
        uav4: UAVNode;
        uav5: UAVNode;

    connections allowunconnected:
        uav1.out --> groundStation.in++;
        uav2.out --> groundStation.in++;
        uav3.out --> groundStation.in++;
        uav4.out --> groundStation.in++;
        uav5.out --> groundStation.in++;
}