CC = g++
SWIG = swig
SWIGFLAGS    = -I../
CPPFLAGS     = -std=c++0x -I../ -fPIC
LDFLAGS      = -shared -L../out
LIBS         = -lFileSequence
MKDIR_P      = mkdir -p

DESTDIR = ./out/
TARGET  = libJFileSequence.so

OBJECTS := FileSequence_wrap.o

WRAP = FileSequence_wrap.cpp
INTERFACE = FileSequence.i

all: mkdirs $(DESTDIR)$(TARGET)

mkdirs: $(DESTDIR)

$(DESTDIR):
	$(MKDIR_P) $(DESTDIR)

$(DESTDIR)$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $(DESTDIR)$(TARGET) $(addprefix $(DESTDIR), $(OBJECTS)) $(LIBS)

$(OBJECTS): $(WRAP)
	$(CC) $(CPPFLAGS) -c $(CFLAGS) $(DESTDIR)$(WRAP) -o $(addprefix $(DESTDIR), $@)

$(WRAP): $(INTERFACE)
	$(SWIG) -c++ -java $(SWIGFLAGS) -outdir $(DESTDIR) -o $(DESTDIR)$@ $(INTERFACE) 

.PHONY: clean

clean:
	-rm -r $(DESTDIR)
