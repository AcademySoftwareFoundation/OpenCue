CC = g++
SWIG = swig
SWIGFLAGS    = -I../
CPPFLAGS     = -std=c++0x -I../ -fPIC
LDFLAGS      = -shared -L../out -Wl,--version-script=version-script.txt
LIBS         = -lFileSequence
MKDIR_P      = mkdir -p

DESTDIR = ./out/
TARGET  = _FileSequence.so

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
	$(SWIG) -c++ -python $(SWIGFLAGS) -outdir $(DESTDIR) -o $(DESTDIR)$@ $(INTERFACE) 

.PHONY: clean

clean:
	-rm -r $(DESTDIR)
