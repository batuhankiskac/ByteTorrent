
import random

#Constants
P = 907
G = 7

def generate_private_key():
    return random.randint(2, P - 2)

def generate_public_key(private_key):
    return pow(G, private_key, P)

def generate_shared_secret(received_public_key, my_private_key):
    return pow(received_public_key, my_private_key, P)