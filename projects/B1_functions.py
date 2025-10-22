# projects/B1_functions.py

def connect_normal_usb(state):
    if state:
        print("B1: Normal USB connected")
        connect_usb_eth(not state)
    else:
        print("B1: Normal USB disconnected")

def connect_usb_eth(state):
    if state:
        print("B1: USB to ETH connected")
        connect_normal_usb(not state)
    else:
        print("B1: USB to ETH disconnected")

def flash_main_sw():
    print("B1: Flashing Main SW...")

def flash_cdt_ufs():
    print("B1: Flashing CDT - UFS...")

def flash_autosar():
    print("B1: Flashing AutoSar...")
