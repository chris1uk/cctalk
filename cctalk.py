#!/usr/bin/env python
import serial
import binascii
import sys,os
import threading
import time
import pickle 
from Crypto.Cipher import DES

try:
    ser = serial.Serial("/dev/ttyUSB0",9600, timeout=0.5)
except Exception, e:
    print 'Unable to open serial port. Things should die gracefully :)\n'


BNVCodeLength=6;
rotatePlaces=12;
feedMaster=99;
tapArray = [7,4,5,3,1,2,3,2,6,1];
devices = []
  
def bsr(value, bits):
    """ bsr(value, bits) -> value shifted right by bits

    This function is here because an expression in the original java
    source contained the token '>>>' and/or '>>>=' (bit shift right
    and/or bit shift right assign).  In place of these, the python
    source code below contains calls to this function.

    Copyright 2003 Jeffrey Clement.  See pyrijnadel.py for license and
    original source.
    """
    minint = -2147483648
    if bits == 0:
        return value
    elif bits == 31:
        if value & minint:
            return 1
        else:
            return 0
    elif bits < 0 or bits > 31:
        raise ValueError('bad shift count')
    tmp = (value & 0x7FFFFFFE) // 2**bits
    if (value & minint):
        return (tmp | (0x40000000 // 2**(bits-1)))
    else:
        return tmp
    
def bnv_encrypt(code,data):
    data=list(data)

    initXOR= ~(int(code[0])<<4 | int(code[4]));
    for i in range (0,len(data)):
        d = ord(data[i])
        d ^=initXOR
        data[i]=chr(d%256)

  
    for i in range (0,len(data)):
        if( (int(code[3]) & (1<< (i & 0x03))) != 0) :
            t=ord(data[i]);
            data[i]= chr (((t & 0x01) <<7) | ((t & 0x02) <<5) | ((t & 0x04) <<3) | ((t & 0x08) <<1) | ((t & 0x10) >>1) | ((t & 0x20) >>3) | ((t & 0x40) >>5) | ((t & 0x80) >>7)); 
    for i in range (0,rotatePlaces):
        if (ord(data[len(data)-1]) & 0x01 !=0):
            c1=128
        else:
            c1= 0
        for j in range (0,len(data)):
            if( (ord(data[j]) )& (1 << tapArray[ (int(code[1])+j) % 10 ]  )) != 0 :
                c1 ^=128

        for j in range (0,len(data)):
            if (ord(data[j]) & 0x01 !=0):
                c=128

            else:
                c= 0

            if( ((int(code[5]) ^ feedMaster) & ( 1 << ( (i+j) %8  ))) != 0) :
                c^=128
                
            data[j] = chr(bsr((ord(data[j])&0xFF),1)+c1)

            c1=c;

    finalXOR= (int(code[2])<<4 | int(code[2]));
                
    for i in range (0,len(data)):
        tf = ord(data[i])
        tf ^= finalXOR;
        data[i]=chr(tf)
    return data

def bnv_decrypt(code,data):
    data=list(data)

    initXOR= (int(code[2])<<4 | int(code[2]));# tested correct 
    for i in range (0,len(data)):
        d = ord(data[i])
        d ^=initXOR
        data[i]=chr(d%256)


    for i in range (rotatePlaces-1,-1,-1):
        if (ord(data[0]) & 0x80) !=0:
            c1 = 1
        else:
            c1 = 0
        for j in range(0,len(data)):

            if((ord(data[j]) & (1 << (tapArray[ (int(code[1])+j) % 10 ]-1)  )) != 0):
                c1 ^=1;
                
        for j in range (len(data)-1,-1,-1):

            if (ord(data[j]) & 0x80) !=0:
                c = 1
            else:
                c = 0
            if( ((int(code[5]) ^ feedMaster) & ( 1 << ( (i+j-1) %8  ))) != 0):
                c^=1;
            data[j] = chr(((ord(data[j]) << 1) + c1)%256);
            c1=c;
                
    for i in range (0,len(data)):
        if( (int(code[3]) & (1<< (i & 0x03))) != 0) :
            t=ord(data[i]);
            data[i]= chr (((t & 0x01) <<7) | ((t & 0x02) <<5) | ((t & 0x04) <<3) | ((t & 0x08) <<1) | ((t & 0x10) >>1) | ((t & 0x20) >>3) | ((t & 0x40) >>5) | ((t & 0x80) >>7)); 
    finalXOR= ~(int(code[0])<<4 | int(code[4]));
                
    for i in range (0,len(data)):
        tf = ord(data[i])
        tf ^= finalXOR;
        data[i]=chr(tf%256)
    return data
    
def crc16(data):
    """
    Calculates the CCITT checksum (CRC16) that can be used as a ccTalk
    checksuming algorithm
    """

    crc=0
    poly = 0x1021

    for c in data:
        crc ^= (ord(c) << 8) & 0xffff
        for x in xrange(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xffff
            else:
                crc <<= 1
                crc &= 0xffff
    return crc

    def validateCRC(data):
        """
        Validates the CRC of a full message
        """
        crc = ord(data[2]) + (ord(data[-1]) << 8)
        data = data[0:2]+data[3:-1]
        return crc == calculateCRC(data)

def checksum256 (st) :
    """
    Calculates the checksum for the message
    """

    total = 0
    for byte in st:
        total = total + ord(byte)
    return chr(256-(total%256))

def send_cmd (destination,header,data,crc,code="000000") :
    cmd=""
    cmd=chr(destination)+chr(len(data))+"\x01"+chr(header)+data 
  
    if crc == 8:
        # [dest][length][src][header][data][checksum] 
        cmd+=checksum256(cmd)
        
    if crc == 16:
        #[dest][length][ CRC-16 LSB ][Header][Data][ CRC-16 MSB ]
        cmd = list(cmd)
        test = cmd[0]+cmd[1]+cmd[3]+data
        crc = crc16(test)
        lsb = chr(crc & 0xff)
        msb = chr((crc & 0xff00) >> 8)
        cmd[2] = lsb

        cmd+=msb

        cmd="".join(cmd)

    if code!="000000" :

        cmd = list(cmd)

        cipher = bnv_encrypt(code,cmd[2:])
        cmd = cmd[:2]+cipher
        cmd="".join(cmd)

    ser.write(cmd)
    data = ser.read(len(cmd))

def fetchresponse (code) :
  toid = ser.read(1)
  if toid:
    length = ord(ser.read(1))
    
    if code=="000000":
        fromid = ser.read(1)
        header = ser.read(1)
        data = ser.read(length)
        checksum = ser.read(1)
    else:
      cipher = ser.read(3+length)
      plain = bnv_decrypt(code,cipher)
      plain  = plain [:-1]
      data = "".join(plain[2:])

    if len(data):
      return data
    elif not data:
      return "\x00"
  
def poll_device():
    for routine in devices:
        routine()
    threading.Timer(0.1, poll_device).start () # set recall interval here
    
class Coin () :
    def __init__(self,crc=8,code="000000") :
        self.accept_enable=0
        self.mech_address = 2
        self.event_number =0
        self.divert = 0 # this will be active when coins go to cashbox
        self.cmd_poll=254
        self.cmd_getcoinid=184
        self.cmd_creditpoll=229
        self.cmd_reset=1
        self.cmd_getroute=209
        self.cmd_setroute=210
        self.cmd_setoverides=222
        self.cmd_modifyinhibits=231
        self.cmd_selfcheck=232
        self.routeinhibits=['\x7e','\x7d','\x7b','\x77']#just bitmasks for route inhibits
        self.credit_values = [1.00,0.50,0.20,0.10,0,2.00,0.05,0.00,0.00,1.00,0.50,0.20,0.10,0.00,2.00,0.05,0.00]
        self.credit = 0
        self.bnv_code = code
        self.crc = crc
        self.cmd_get_encryption = 111 #requires trusted mode to read keys
        self.cmd_111_sig = "\xAA\x55\x00\x00\x55\xAA" #sent as data with cmd 111 seems pointless for implementation 
        
    def get_credit (self) :
        cr=self.credit
        self.credit=0
        return cr
    
    def stop_accepting (self) :
        self.accept_enable = 0
      
    def connect_mech (self) :
        try:
            ser
        except NameError:
            return False
        #send_cmd(self.mech_address,self.cmd_reset,"",self.crc,self.bnv_code)
        #fetchresponse(self.bnv_code)
        send_cmd(self.mech_address,self.cmd_get_encryption,self.cmd_111_sig,8,"000000") # des check is done 8 bit checksum no encryption 
        r = fetchresponse("000000")
        print "des check ",binascii.hexlify(r)
        bnv = binascii.hexlify(r[6])+binascii.hexlify(r[7])+binascii.hexlify(r[8])
        print "bnv key is - ",bnv[1]+bnv[0]+bnv[3]+bnv[2]+bnv[5]+bnv[4]
        send_cmd(self.mech_address,self.cmd_poll,"",self.crc,self.bnv_code)
        response=fetchresponse(self.bnv_code)
        if response:
          send_cmd(self.mech_address,self.cmd_reset,"",self.crc,self.bnv_code)
          ser.readline()

          send_cmd(self.mech_address,self.cmd_selfcheck,"",self.crc,self.bnv_code)
          faults=fetchresponse(self.bnv_code)
          print "faults",faults
          if not ord(faults):
            print "Self test completed no faults found\n"
            send_cmd(self.mech_address,self.cmd_modifyinhibits,chr(255)+chr(0),self.crc,self.bnv_code) #bank 1 only enabled
            fetchresponse(self.bnv_code)
      
            print "Coinmech Enabled\n"
            self.accept_enable=1
            devices.append(self.poll_mech)
            return True
        
          elif ord(faults):
	        print "Fault Found - : "+self._check_fault(ord(faults))+"\n"
	        return False

   
        elif not response:
          ser.close()
          return False
     
    def poll_mech (self) :
        if self.accept_enable:
          if(self.divert):#this will check if coins should be diverted     
            send_cmd(self.mech_address,self.cmd_setoverides,self.routeinhibits[0],self.crc,self.bnv_code)#7e 7d 7b 77 i'm just using route 1 for now 
            fetchresponse(self.bnv_code)
          elif not(self.divert):###divert check fix me 
            send_cmd(self.mech_address,self.cmd_setoverides,"\x7f",self.crc,self.bnv_code)#this is default 01111111
            fetchresponse(self.bnv_code)
          send_cmd(self.mech_address,self.cmd_creditpoll,"",self.crc,self.bnv_code)
 
          results=fetchresponse(self.bnv_code)
          if results:
            newevent=ord(results[0])#this fetches event counter
            results = results[1:]
            
            for i in range (0,abs(newevent-self.event_number)) :
                
                coin=ord(results[i*2])
                route=ord(results[i*2+1])
                print "coin ,route",coin,route 
                if coin==0 and route>0:
	                print "Error : "+self._check_error(route)+"\n"
                if coin>0:
                    print "coin accepted"
                    self.credit+=self.credit_values[coin-1]
                
            self.event_number=newevent
            #threading.Timer(0.1, self.poll_mech).start () # set recall interval here

          else:
            print "Coin Mech Vanished"
            self.accept_enable=0    



    def _check_error (self,number) :
  
      errors = [(1,"Reject Coin"),
	            (2,"Coin Inhibited"),
	            (3,"Multiple Window Error"),
	            (5,"Validation Timeout"),
	            (6,"Coin Accept Over Timeout"),	    
                (7,"Sorter Opto Timeout"),
	            (8,"Second Close Coin"),
                (9,"Accept Gate Not Ready"),
	            (10,"Credit Sensor Not Ready"),	    
                (11,"Sorter Not Ready"),
	            (12,"Reject Coin Not Cleared"),
	            (14,"Credit Sensor Blocked"),
                (15,"Sorter Opto Blocked"),	 		    
                (17,"Coin Going Backwards"),
	            (18,"Accept Sensor Under Timeout"),
	            (19,"Accept Sensor Over Timeout"),
	            (21,"Dce Opto Timeout"),	    
                (22,"Dce Opto Error"),
	            (23,"Coin Accept Under Timeout"),
	            (24,"Reject Coin Repeat"),
	            (25,"Reject Slug"),
	            (128,"Coin 1 Inhibited"),
	            (129,"Coin 2 Inhibited"),
	            (130,"Coin 3 Inhibited"),	    
	            (131,"Coin 4 Inhibited"),
	            (132,"Coin 5 Inhibited"),
                (133,"Coin 6 Inhibited"),
	            (134,"Coin 7 Inhibited"),	    
                (135,"Coin 8 Inhibited"),
	            (136,"Coin 9 Inhibited"),
	            (137,"Coin 10 Inhibited"),
	            (138,"Coin 11 Inhibited"),	 		    
	            (139,"Coin 12 Inhibited"),
	            (140,"Coin 13 Inhibited"),
                (141,"Coin 14 Inhibited"),
                (142,"Coin 15 Inhibited"),	    
	            (143,"Coin 16 Inhibited"),
	            (254,"Flight Deck Open")]
  
      for i in range(0,len(errors)):
	    	   if errors[i][0] == number:
		         return errors[i][1]

    def _check_fault (self,number) :
  
      faults = [(0,"No Faults Found"),
	            (1,"Eeprom Checksum Error"),
	            (2,"Inductive Coils Faulty"),
                (3,"Credit Sensor Faulty"),
                (4,"Piezo Sensor Faulty"),	    
                (8,"Sorter Exits Faulty"),
	            (19,"Reject Flap Sensor Fault"),
	            (21,"Rim Sensor Faulty"),
	            (22,"Thermistor Faulty"),	    
	            (35,"Dce Faulty")]
  
      for i in range(0,len(faults)):
	    	   if faults[i][0] == number:
		         return faults[i][1]	

class Note () :
    def __init__(self,crc=8,code="000000") :
        self.request_bill_id=157#Header 157 - Request bill id
        self.cmd_creditpoll=229
        self.cmd_reset=1
        self.cmd_modifyinhibits=231
        self.read_bill_events =159 #Header 159 - Read buffered bill events
        self.accept_enable=0
        self.mech_address = 40
        self.event_number =0
        self.divert = 0 # this will be active when coins go to cashbox
        self.cmd_poll=254
        self.credit_values = [1.00,0.50,0.20,0.10,0,2.00,0.05,0.00,0.00,1.00,0.50,0.20,0.10,0.00,2.00,0.05,0.00]
        self.credit = 0
        self.bnv_code = code
        self.crc = crc
        self.notes_paid = 0 
        
    def connect_mech (self) :
        try:
            ser
        except NameError:
            return False
        send_cmd(self.mech_address,self.cmd_poll,"",self.crc,self.bnv_code)
        response=fetchresponse(self.bnv_code)
 

        if response:
          send_cmd(self.mech_address,self.cmd_reset,"",self.crc,self.bnv_code)
          ser.readline()
          alive = None
          while not alive: # wait for mech to start responding after reset command before we enable
              send_cmd(self.mech_address,self.cmd_poll,"",self.crc,self.bnv_code)
              alive =fetchresponse(self.bnv_code)
          send_cmd(self.mech_address,self.cmd_modifyinhibits,chr(255)+chr(255),self.crc,self.bnv_code) #all enabled
          fetchresponse(self.bnv_code)

          self.accept_enable=1
          for i in range(1,17):
              send_cmd(self.mech_address,157,chr(i),self.crc,self.bnv_code)
  
              data = fetchresponse(self.bnv_code)
              print i,data
              
          send_cmd(self.mech_address,228,chr(255),self.crc,self.bnv_code)
  
          data = fetchresponse(self.bnv_code)
          
          send_cmd(self.mech_address,32,chr(0)+chr(3),self.crc,self.bnv_code)
  
          data = fetchresponse(self.bnv_code)
          

          #self.poll_mech()
          devices.append(self.poll_mech)
          return True
        
         # elif ord(faults):
	     #   print "Fault Found - : "+self._check_fault(ord(faults))+"\n"
	     #   return False

   
        elif not response:
          ser.close()
          return False

    def poll_mech (self) :
        if self.accept_enable:
          send_cmd(self.mech_address,self.read_bill_events,"",self.crc,self.bnv_code)
 
          results=fetchresponse(self.bnv_code)
     
          if results:
            newevent=ord(results[0])#this fetches event counter
            results = results[1:]
            
            for i in range (0,abs(newevent-self.event_number)) :
                note=ord(results[i*2])
                route=ord(results[i*2+1])
                if note>0 and route == 1:#note in escrow
                    print "NOTE IN ESCROW"
                    send_cmd(self.mech_address,154,chr(1),self.crc,self.bnv_code)#Header 154 - Route bill
                    fetchresponse(self.bnv_code)#sent to cashbox
                if note>0 and route == 0: #note credited
                    send_cmd(self.mech_address,157,chr(note),self.crc,self.bnv_code)
                    print "BILL ID",fetchresponse(self.bnv_code)+" Accepted"

                
            self.event_number=newevent
            #threading.Timer(0.1, self.poll_mech).start () # set recall interval here

          else:
            print "Note Mech Vanished"
            self.accept_enable=0
    def pay_note(self):
        self.disable_mech()
        time.sleep(1)
        send_cmd(self.mech_address,27,chr(165),self.crc,self.bnv_code) # enables note payout 
        data = fetchresponse(self.bnv_code)
        send_cmd(self.mech_address,28,chr(0)+chr(48)*8+chr(1),self.crc,self.bnv_code)
        data = fetchresponse(self.bnv_code)
        fetchresponse(self.bnv_code)
        
        self.enable_mech()
        if not data:
            data = "\x00"
        notes_paid = ord(data)

        if notes_paid:

            return True
        else:
            return False
    def pause_1(self):
        print "PAUSED FOR 1 MINUTE"
        self.disable_mech()
        time.sleep(20)
        print "PAUSE IS DONE"
        self.enable_mech()
    
    def disable_mech(self):
        print "mech disabled"
        self.accept_enable = 0
        send_cmd(self.mech_address,228,chr(0),self.crc,self.bnv_code)
        time.sleep(2)
        data = fetchresponse(self.bnv_code)  
        
    def enable_mech(self):
        print "mech enabled"
        self.accept_enable = 1
        send_cmd(self.mech_address,228,chr(255),self.crc,self.bnv_code)
        data = fetchresponse(self.bnv_code)  
    def stop_polling(self):
        print devices.remove(self.poll_mech)
poll_device()
