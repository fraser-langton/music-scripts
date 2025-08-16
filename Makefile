# Makefile for keyfinder_cli

CXX = g++
CXXFLAGS = -std=c++11 -O2
LIBS = -lkeyfinder -lsndfile -lfftw3

# Detect OS for library paths
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    # macOS with Homebrew
    CXXFLAGS += -I/opt/homebrew/include
    LDFLAGS += -L/opt/homebrew/lib
endif

TARGET = keyfinder_cli
SOURCE = keyfinder_cli.cpp

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $(TARGET) $(SOURCE) $(LIBS)

clean:
	rm -f $(TARGET)

install-deps:
ifeq ($(UNAME_S),Darwin)
	brew install libkeyfinder libsndfile fftw
else
	@echo "Please install libkeyfinder, libsndfile, and fftw for your system"
endif

.PHONY: clean install-deps
