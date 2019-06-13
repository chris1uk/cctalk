class Hoppper () :
    def __init__(self) :
        self.hopper_address = 3
        self.event_number = 0
        self.cmd_reset = 1
        self.cmd_enable_hopper = 164
        self.cmd_get_cipher = 160
        self.cmd_dispense_coins = 167
        self.cmd_get_status = 166
        self.cmd_get_encryption = 111 #requires trusted mode to read keys
        self.cmd_111_sig = "\xAA\x55\x00\x00\x55\xAA" #sent as data with cmd 111 seems pointless for implementation 
        self.cmd_change_key = 110 #this can be used to check key aswell as change 
        self.des_key="12345678"
        if not os.path.exists("des.key") :
            f = open("des.key", 'wb')
            pickle.dump(self.des_key, f)
            f.close()
        else :
            f = open('des.key', 'rb')
            self.des_key = pickle.load(f)
            f.close()
        self.des = DES.new(self.des_key, DES.MODE_ECB)
        
    def connect_hopper (self) :
        try:
            ser
        except NameError:
            return False
        if self.reset_hopper () :
            send_cmd(self.hopper_address,self.cmd_get_encryption,self.cmd_111_sig) # check if hopper supports des 
            r = fetchresponse()
            if r :
                if ord(r[5]) == 255 :#this would indicate trusted mode 
                    print "Truted mode key has been saved, reboot and may the force be with you"
                    self.des_key=r[-8:]
                    f = open("des.key", 'wb')
                    pickle.dump(self.des_key, f)
                    f.close()
                if ord(r[1])==101 : #checking second byte for command level
                    if not self.change_key(self.des_key,self.des_key) :#trusted mode required 
                        return False
                    return True
            elif not r :
                return False
            
    def change_key (self,old,new) :  
        c=""
        for i in range(0,8) :
            c+=old[i]
            c+=new[i]
        send_cmd(self.hopper_address,self.cmd_change_key,self.des.encrypt(c))
        return fetchresponse()
    
    def get_hopper_status (self) :
        send_cmd(self.hopper_address,self.cmd_get_status,"")#for security it would be better to use header 109 
        return fetchresponse()
    
    def reset_hopper(self) :
        send_cmd(self.hopper_address,self.cmd_reset,"")
        time.sleep(0.1)#give hopper a chance to reboot
        return fetchresponse()
    
    def get_cipher (self) :
        send_cmd(self.hopper_address,self.cmd_get_cipher,"")
        return fetchresponse()
    
    def enable_hopper (self) :
        send_cmd(self.hopper_address,self.cmd_enable_hopper,chr(165))
        return fetchresponse()

    def pay_coin(self,no_coins) :
        c=""
        coins_paid=0
        unpaid=0
        self.reset_hopper()
        self.enable_hopper()
        cipher = self.des.decrypt(self.get_cipher())
        cipher = bytearray(cipher)
        for i in range(0,8) :
            cipher[i]=cipher[i]^no_coins
        cipher = self.des.encrypt(str(cipher))
        cipher+=chr(no_coins)
        
        send_cmd(self.hopper_address,self.cmd_dispense_coins,cipher)
        fetchresponse()
        
        while coins_paid<no_coins :
            r = self.get_hopper_status()
            coins_paid=ord(r[2])
            if ord(r[3]) :
                unpaid=ord(r[3]) 
                unpaid = unpaid-(unpaid*2)
                return unpaid
        return coins_paid
        
        
#mech=Coin()
#hopper=Hoppper()
#if not hopper.connect_hopper() :
#    print "Hopper not found/compatible or trusted mode required this code could easily handle the errors seperately"
#    exit()
#paid=hopper.pay_coin(1)
#if paid <0 :
#    print"Hopper Empty/Jammed IOU",abs(paid)
#else :
#    print "Payout succes ",paid,"coins paid"
#if not mech.connect_mech():
#    print "Mech not found"
