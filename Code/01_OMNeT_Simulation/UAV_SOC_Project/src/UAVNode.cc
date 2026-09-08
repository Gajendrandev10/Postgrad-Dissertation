#include <omnetpp.h>
#include <fstream>
#include <cstring>

using namespace omnetpp;

static std::ofstream logfile;

class UAVNode : public cSimpleModule
{
  private:
    cMessage *sendEvent = nullptr;

  protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
};

Define_Module(UAVNode);

void UAVNode::initialize()
{
    if (!logfile.is_open())
    {
        logfile.open("uav_traffic.csv", std::ios::out);
        logfile << "Time,UAV,Event,PacketSize,Source,Destination,Latency,PacketLoss,Throughput,Label\n";
        logfile.flush();
    }

    EV << "UAV Node Started: " << getName() << endl;

    if (strcmp(getName(), "groundStation") != 0)
    {
        sendEvent = new cMessage("sendPacket");
        scheduleAt(simTime() + uniform(1, 3), sendEvent);
    }
}

void UAVNode::handleMessage(cMessage *msg)
{
    if (msg == sendEvent)
    {
        int packetSize = intuniform(256, 1024);
        double latency = uniform(20, 80);
        double packetLoss = uniform(0.5, 5.0);
        double throughput = packetSize / latency;

        std::string label = "Normal";

        if (strcmp(getName(), "uav3") == 0 && simTime() > 50)
        {
            latency = uniform(100, 180);
            packetLoss = uniform(15, 35);
            throughput = packetSize / latency;
            label = "Attack";
        }

        cMessage *packet = new cMessage("UAV_Data");
        send(packet, "out");

        logfile << simTime().dbl() << ","
                << getName() << ","
                << "Send" << ","
                << packetSize << ","
                << getName() << ","
                << "groundStation" << ","
                << latency << ","
                << packetLoss << ","
                << throughput << ","
                << label << "\n";

        logfile.flush();

        scheduleAt(simTime() + uniform(1, 3), sendEvent);
    }
    else
    {
        logfile << simTime().dbl() << ","
                << getName() << ","
                << "Receive" << ","
                << 0 << ","
                << "UAV" << ","
                << getName() << ","
                << 0 << ","
                << 0 << ","
                << 0 << ","
                << "Normal" << "\n";

        logfile.flush();

        delete msg;
    }
}

void UAVNode::finish()
{
    if (sendEvent != nullptr)
    {
        cancelAndDelete(sendEvent);
        sendEvent = nullptr;
    }

    if (logfile.is_open())
    {
        logfile.flush();
    }
}
