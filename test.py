import time
from cctalk import *
##mech=Note(16,"123456")   # crc,bnv   crc can be 8 or 16 set bnv to 000000 for no encryption
#print mech.connect_mech()

#print "waiting 30 seconds then paying note"
#time.sleep(30)
#paid =  mech.pay_note()
#if paid:
#    print "Notes Paid",paid
#else:
#    print "Failed to pay Note"
#print "waiting 30 seconds then paying note"

#paid =  mech.pay_note()
#if paid:
#    print "Notes Paid"
#else:
#    print "Failed to pay Note"

#print "waiting 30 seconds then paying note"

#paid =  mech.pay_note()
#if paid:
#    print "Notes Paid",paid
#else:
#    print "Failed to pay Note"
#mech.pause_1()

#print "waiting 30 seconds then stopping mech poll"
#time.sleep(30)
#mech.stop_polling() #can be restarted with connect_mech()
#print "POLLING STOPPED"

mech=Coin(16,"201448")   # crc,bnv   crc can be 8 or 16 set bnv to 000000 for no encryption
print mech.connect_mech()
