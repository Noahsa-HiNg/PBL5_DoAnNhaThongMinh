#include <ArduinoJson.h>

struct Device {
    int id;
    int type_id; 
    int pin;
};

Device myDevices[15]; 
int deviceCount = 0;


void parseConfig(String payload) {
    DynamicJsonDocument doc(4096);
    deserializeJson(doc, payload);
    JsonArray arr = doc.as<JsonArray>();
    
    deviceCount = arr.size();
    for (int i = 0; i < deviceCount; i++) {
        myDevices[i].id = arr[i]["id"];
        myDevices[i].type_id = arr[i]["type_id"];
        myDevices[i].pin = arr[i]["pin"];
        
        if (myDevices[i].type_id == 4) {
            pinMode(myDevices[i].pin, OUTPUT);
        } else {
            pinMode(myDevices[i].pin, INPUT);
        }
    }
}