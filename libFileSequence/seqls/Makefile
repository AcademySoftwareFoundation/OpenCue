CC = g++
CPPFLAGS     = -std=c++0x -I../export
LDFLAGS      = -L../out
LIBS         = -lFileSequence

DESTDIR = ./
TARGET  = seqls

OBJECTS := $(patsubst %.cpp,%.o,$(wildcard *.cpp))

all: $(DESTDIR)$(TARGET)

$(DESTDIR)$(TARGET): $(OBJECTS)
	$(CC) -Wall $(LDFLAGS) -o $(DESTDIR)$(TARGET) $(OBJECTS) $(LIBS)

$(OBJECTS): %.o: %.cpp
	$(CC) -Wall $(CPPFLAGS) -c $(CFLAGS) $< -o $@

.PHONY: clean

clean:
	-rm -f $(OBJECTS)
	-rm -f $(TARGET)
