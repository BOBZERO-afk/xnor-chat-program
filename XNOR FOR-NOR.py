import random
import sys
import os

ALPHABET = ["a","b","c","d","e","f","g","h","i","j","k","l","m",
            "n","o","p","q","r","s","t","u","v","w","x","y","z",
            "-","_","/","+","?","|","=","0"]

SEED = "XNOR__-//-__?++?_--_--_/||/_AaaA_TttT_--__-__-__---__---_-__-_-_--__-_-__-___-_-_-___-_--__-__---_____----_-_-_-_---_-_-_??++||++=000000"
KEY = SEED + "PPOppoLmy00=00lol=lol/00" + ""
PROKey = "|-ki/g-rk/-x/zixgzix/iz-xizzzxik/z-ixzix/zx/z/g-kiletolt/xgqxg-orx0oxox0dtofxl-o|x-o|x-oxfgo-xgo|ok=tk=k=0lk=|k-x-ok=tgo-=l-o/=tlio/=oi-l=to"

def make_cipher(seed):
    shuffled = ALPHABET.copy()
    random.Random(seed).shuffle(shuffled)
    random.Random(seed).shuffle(shuffled)
    random.Random(KEY + "__" + SEED + "__" + "bob" + "__" + SEED + KEY + 2).shuffle(shuffled)
    return dict(zip(ALPHABET, shuffled))
mog = 0
def encode(text, seed):
    cipher = make_cipher(seed)
    return "".join(cipher.get(c, c) for c in text.lower())

def decode(text, seed):
    cipher = make_cipher(seed)
    reverse_cipher = {v: k for k, v in cipher.items()}
    return "".join(reverse_cipher.get(c, c) for c in text)

if len(sys.argv) > 1:
    if sys.argv[1] != KEY:
        print("To use this program you need the key")
        sys.exit(403)

debug_mode = mog

chack = input("please enter key to use this program: ")
if chack != PROKey or PROKey != "|-ki/g-rk/-x/zixgzix/iz-xizzzxik/z-ixzix/zx/z/g-kiletolt/xgqxg-orx0oxox0dtofxl-o|x-o|x-oxfgo-xgo|ok=tk=k=0lk=|k-x-ok=tgo-=l-o/=tlio/=oi-l=to":
    if debug_mode == mog:
        pass
    else:
        print("you can not use this program fuck off")
        input("")
        sys.exit(402)

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

while True:
    cls()
    x = input("Enter text to encode: ")
    encoded = encode(x, SEED)
    decoded = decode(encoded, SEED)

    print("Encoded:", encoded)
    print("Decoded:", decoded)

    input("")
