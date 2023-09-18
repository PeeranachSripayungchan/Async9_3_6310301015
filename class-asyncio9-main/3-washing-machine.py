import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum

student_id = "6310301015"

class MachineStatus(Enum):
    pressure = round(random.uniform(2000,3000), 2)
    temperature = round(random.uniform(25.0,40.0), 2)

class MachineMaintStatus(Enum):
    filter = random.choice(["clear", "clogged"])
    noise = random.choice(["quiet", "noisy"])

class WashingMachine:
    def __init__(self, serial):
        self.MACHINE_STATUS = 'OFF'
        self.SERIAL = serial
        self.Task = None

    def Cancel(self):
        if self.Task != None:
            self.Task.cancel()
            self.Task = None

async def publish_message(w, client, app, action, name, value):
    print(f"{time.ctime()} - [{w.SERIAL}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : w.SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL}"
                        , payload=json.dumps(payload))
    
async def Roaming(w, name):
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL} - {w.MACHINE_STATUS}] {name} START")
    await asyncio.sleep(3600)

'''
async def Running(w, action):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] {action} START")

    if action == "FILLWATER":
        # Simulate filling water
        await asyncio.sleep(10) 
    if action == "HEATMAKER":
        # Simulate heating
        await asyncio.sleep(10) 
    if action == "WASHING":
        # Simulate Washing
        await asyncio.sleep(10) 
'''


async def CoroWashingMachine(w, client, event):
    while True:
        '''
        wait_next = round(10*random.random(),2)
        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... {wait_next} seconds.")
        await asyncio.sleep(wait_next)
        '''
        '''
        if w.MACHINE_STATUS == 'OFF':
            continue
        if w.MACHINE_STATUS in ['READY', 'HEATMAKER']:
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
            await event.wait()
            event.clear()
        '''

        if w.MACHINE_STATUS == 'READY':
            await publish_message(w, client, "hw", "get", "STATUS", "READY")
            await publish_message(w, client, "hw", "get", "LID", "CLOSE")
            w.MACHINE_STATUS = 'FILLWATER'
            await publish_message(w, client, "hw", "get", "STATUS", "FILLWATER")
            await w.Running_Task(client, invert=False)

        if w.MACHINE_STATUS == 'HEATWATER':
            await publish_message(w, client, "hw", "get", "STATUS", "HEATWATER")
            await w.Running_Task(client, invert=False)

        if w.MACHINE_STATUS == ['WASH', 'RINSE', 'SPIN']:
            await publish_message(w, client, "hw", "get", "STATUS", w.MACHINE_STATUS)
            await w.Running_Task(client, invert=True)

        if w.MACHINE_STATUS == 'FAULT':
            print(f"{time.ctime()} - [{w.SERIAL} - {w.MACHINE_STATUS} - {w.FAULT}] Waiting to clear fault...")
            await event.wait()
            event.clear()


            # door close

            # fill water untill full level detected within 10 seconds if not full then timeout 

            # heat water until temperature reach 30 celcius within 10 seconds if not reach 30 celcius then timeout

            # wash 10 seconds, if out of balance detected then fault

            # rinse 10 seconds, if motor failure detect then fault

            # spin 10 seconds, if motor failure detect then fault

            # ready state set 

            # When washing is in FAULT state, wait until get FAULTCLEARED

            w.MACHINE_STATUS = 'OFF'
            await publish_message(w, client, "app", "get", "STATUS", w.MACHINE_STATUS)
            continue
            

async def listen(w, client, event):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        await client.subscribe(f"v1cdti/app/set/{student_id}/model-01/")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT - [{m_decode['serial']}]:{m_decode['name']} => {m_decode['value']}")
                
                match m_decode['name']:
                    case "STATUS":
                        w.MACHINE_STATUS = m_decode['value']
                        if m_decode['value'] == "READY":
                            if not event.is_set():
                                event.set()
                    case "FAULT":
                        if m_decode['value'] == "FAULTCLEARED":
                            w.MACHINE_STATUS = 'OFF'
                            if not event.is_set():
                                event.set()
                        elif m_decode['value'] == "OUTOFBALANCE" and w.MACHINE_STATUS == "WASH":
                            w.MACHINE_STATUS = "FAULT"
                            w.FAULT = "OUTOFBALANCE"
                        elif m_decode['value'] == "OUTOFBALANCE" and w.MACHINE_STATUS in ['RINSE', 'SPIN']:
                            w.MACHINE_STATUS = "FAULT"
                            w.FAULT = "OUTOFBALANCE"
                    case "WATERFULLLEVEL":
                        if w.MACHINE_STATUS == "FILLWATER" and m_decode['value'] == "FULL":
                            await w.Cancel_Task()
                            w.MACHINE_STATUS = "HEATWATER"
                    case "TEMPERATUREREACHED":
                        if w.MACHINE_STATUS == "HEATWATER" and m_decode['value'] == "REACHED":
                            await w.Cancel_Task()
                            w.MACHINE_STATUS = "WASH"
                    case "FUNCTIONCOMPLETED":
                        match m_decode['value']:
                            case "WASH":
                                await w.Cancel_Task()
                                w.MACHINE_STATUS = "RINSE"
                            case "RINSE":
                                await w.Cancel_Task()
                                w.MACHINE_STATUS = "SPIN"
                            case "SPIN":
                                await w.Cancel_Task()
                                w.MACHINE_STATUS = "READY"
            elif message.topic.matches(f"v1cdti/app/set/{student_id}/model-01/"):
                await publish_message(w, client, "app", "monitor", "STATUS", w.MACHINE_STATUS)

                                
'''                
async def cancel_me():
    print('cancel_me(): before sleep')

    try:
        # Wait for 1 hour
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print('cancel_me(): cancel sleep')
        raise
    finally:
        print('cancel_me(): after sleep')]

async def make_request_with_timeout():
    try:
        async with asyncio.timeout(1):
            # Structured block affected by the timeout:
            await make_request()
            await make_another_request()
    except TimeoutError:
        log("There was a timeout")
    # Outer code not affected by the timeout:
    await unrelated_code()
'''
async def main():
    n = 10
    W = [WashingMachine(serial=f'SN-00{i+1}') for i in range(n)]
    Events = [asyncio.Event() for i in range(n)]
    async with aiomqtt.Client("broker.hivemq.com") as client:
        listentask = []
        CoroWashingMachineTask = []
        for w, event in zip(W, Events):
            listentask.append(listen(w, client, event))
            CoroWashingMachineTask.append(CoroWashingMachine(w, client, event))
        await asyncio.gather(*listentask , *CoroWashingMachineTask)

import sys
import os
# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

asyncio.run(main())