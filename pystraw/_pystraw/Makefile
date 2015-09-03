
.PHONY: default

default: pystraw.so

CPPFLAGS :=

CFLAGS := -fPIC -ggdb -O0

SRC := $(wildcard *.c)
OBJ := $(SRC:%.c=%.o)

%.o: %.c
	gcc -c $(CPPFLAGS) $(CFLAGS) $<

pystraw.so: $(OBJ)
	gcc -shared -o $@ $< 

