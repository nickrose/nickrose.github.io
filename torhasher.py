#!/usr/bin/env python2.7
import os
import binascii
import hashlib
import sys

# supply password

secret = '12password34'
args = sys.argv
if len(args) == 1 or (args[1] in ['--help', '-h']):
    print 'tor password hasher'
    print 'usage: ' + __file__ + ' <password to hash>'
    sys.exit()
else:
    secret = args[1]

# static 'count' value later referenced as "c"
indicator = chr(96)

# used to generate salt
rng = os.urandom

# generate salt and append indicator value so that it
salt = "%s%s" % (rng(8), indicator)

# That's just the way it is. It's always prefixed with 16
prefix = '16:'

# swap variables just so I can make it look exactly like the RFC example
c = ord(salt[8])

# generate an even number that can be divided in subsequent sections. (Thanks Roman)
EXPBIAS = 6
count = (16 + (c & 15)) << ((c >> 4) + EXPBIAS)  #

d = hashlib.sha1()

# take the salt and append the password
tmp = salt[:8] + secret

# hash the salty password as many times as the length of
# the password divides into the count value
slen = len(tmp)
while count:
    if count > slen:
        d.update(tmp)
        count -= slen
    else:
        d.update(tmp[:count])
        count = 0
hashed = d.digest()
# Convert to hex
salt = binascii.b2a_hex(salt[:8]).upper()
indicator = binascii.b2a_hex(indicator)
torhash = binascii.b2a_hex(hashed).upper()

# Put it all together into the proprietary Tor format.
print prefix + salt + indicator + torhash
