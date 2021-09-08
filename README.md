# x32tunnel

A TCP tunnel for the Open Sound Control (OSC) protocol, particularly
for the X32 family of mixers.

## Quickstart

```
pip install x32tunnel

# on the mixer side
x32tunnel mixer-side -m mixer-ip-address

# on the client side
x32tunnel client-side -H mixer-side-ip-address
```

