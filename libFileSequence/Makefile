CC = g++
CPPFLAGS     = -std=c++0x -fPIC
LDFLAGS      = -shared
LIBS         = -lpcre
MKDIR_P      = mkdir -p

DESTDIR = ./out/
TARGET  = libFileSequence.so

OBJECTS := $(patsubst %.cpp,%.o,$(wildcard *.cpp))

all: mkdirs $(DESTDIR)$(TARGET)

mkdirs: $(DESTDIR)

$(DESTDIR):
	$(MKDIR_P) $(DESTDIR)

$(DESTDIR)$(TARGET): $(OBJECTS)
	$(CC) -Wall $(LDFLAGS) -o $(DESTDIR)$(TARGET) $(addprefix $(DESTDIR), $(OBJECTS)) $(LIBS)

$(OBJECTS): %.o: %.cpp
	$(CC) -Wall $(CPPFLAGS) -c $(CFLAGS) $< -o $(addprefix $(DESTDIR), $@)

.PHONY: clean

clean:
	-rm -r $(DESTDIR)
