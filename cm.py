class Coin () :
    def __init__(self,crc=8,code="000000") :
        print "LANDED"
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
            self._poll_mech()
            return True
        
          elif ord(faults):
	        print "Fault Found - : "+self._check_fault(ord(faults))+"\n"
	        return False

   
        elif not response:
          ser.close()
          return False
     
    def _poll_mech (self) :
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
            
                if coin==0 and route>0:
	                print "Error : "+self._check_error(route)+"\n"
                if coin>0:
                    self.credit+=self.credit_values[coin-1]
                
            self.event_number=newevent
            threading.Timer(0.1, self._poll_mech).start () # set recall interval here

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
