# projects/C21_functions.py

def connect_normal_usb(state):
    if state:
        print("C2.1: Normal USB connected with special settings")
    else:
        print("C2.1: Normal USB disconnected")

def connect_usb_eth(state):
    print("C2.1: USB to ETH operation executed")

def flash_main_sw():
    print("C2.1: Flashing Main SW with extra verification")

def flash_cdt_ufs():
    print("B1: Flashing CDT - UFS...")

def flash_autosar():
    print("C2.1: Flashing AutoSar with timeout check")
